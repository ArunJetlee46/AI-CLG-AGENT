"""ONNX local embeddings and cross-encoder reranking (no torch dependency).

Embedder: BAAI/bge-small-en-v1.5 exported to ONNX (384-dim, BERT mean pooling).
Reranker: BAAI/bge-reranker-base cross-encoder exported to ONNX.

Artifacts are downloaded once from the Hugging Face Hub into
`settings.onnx_model_dir` (gitignored). When the artifacts are unavailable
(no network, empty cache, load error) every entry point raises so callers can
fall back to the existing hash embeddings / score-order reranking, preserving
the offline-first guarantee.
"""
from __future__ import annotations

import glob
import logging
import os

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_SEQ = 512


def _cache_dir(repo_id: str) -> str:
    return os.path.join(settings.onnx_model_dir, repo_id.replace("/", "_"))


def _resolve_model(repo_id: str, *, allow_download: bool) -> tuple[str, str]:
    """Return (model, tokenizer) paths for `repo`, downloading only when allowed.

    The embedder is small and required for retrieval, so it auto-downloads.
    The reranker is large (~1GB) and must never block the request path, so it is
    cache-only here; run `python -m scripts.download_onnx_models` to prefetch it.
    """
    local_dir = _cache_dir(repo_id)
    if allow_download:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            allow_patterns=["tokenizer.json", "config.json", "onnx/*.onnx"],
        )
    tokenizer_path = os.path.join(local_dir, "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"no tokenizer.json for {repo_id} in {local_dir}")
    candidates = glob.glob(os.path.join(local_dir, "onnx", "*.onnx"))
    if not candidates:
        hint = (
            f"no ONNX model for {repo_id} in {local_dir}"
            if allow_download
            else f"reranker not cached ({repo_id}); run `python -m scripts.download_onnx_models` to prefetch"
        )
        raise FileNotFoundError(hint)
    quantized = [p for p in candidates if "quantized" in p]
    return (quantized or sorted(candidates))[0], tokenizer_path


class OnnxEmbedder:
    """BERT-style mean-pooled, L2-normalized embeddings from an ONNX model."""

    def __init__(self, repo_id: str | None = None) -> None:
        self.repo_id = repo_id or settings.onnx_embedding_repo
        self._disabled = False
        self._session = None
        self._tokenizer = None
        self._input_names: list[str] = []
        self._load()

    def _load(self) -> None:
        try:
            from tokenizers import Tokenizer

            import onnxruntime as ort

            model_path, tokenizer_path = _resolve_model(self.repo_id, allow_download=True)
            tok = Tokenizer.from_file(tokenizer_path)
            tok.enable_truncation(max_length=_MAX_SEQ)
            if tok.token_to_id("[PAD]") is not None:
                tok.enable_padding(pad_id=tok.token_to_id("[PAD]"), pad_token="[PAD]")
            session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self._input_names = [i.name for i in session.get_inputs()]
            self._session = session
            self._tokenizer = tok
            logger.info("ONNX embedder ready: %s (%s)", self.repo_id, os.path.basename(model_path))
        except Exception as exc:  # noqa: BLE001 - offline-first: caller falls back
            self._disabled = True
            logger.warning("ONNX embedder unavailable (%s); using hash fallback embeddings", exc)

    def is_available(self) -> bool:
        return not self._disabled and self._session is not None and self._tokenizer is not None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.is_available():
            raise RuntimeError(f"ONNX embedder unavailable ({self.repo_id})")
        encodings = self._tokenizer.encode_batch(texts)  # type: ignore[union-attr]
        input_ids = np.asarray([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.asarray([e.attention_mask for e in encodings], dtype=np.int64)
        feeds: dict[str, np.ndarray] = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)
        outputs = self._session.run(None, feeds)  # type: ignore[union-attr]
        token_embeddings = np.asarray(outputs[0], dtype=np.float32)
        mask = attention_mask.astype(np.float32)[..., None]
        summed = np.sum(token_embeddings * mask, axis=1)
        counts = np.maximum(mask.sum(axis=1), 1e-9)
        pooled = summed / counts
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        pooled = pooled / np.maximum(norms, 1e-9)
        return [list(map(float, v)) for v in pooled]


class OnnxReranker:
    """Cross-encoder reranking ([query, doc] pairs) from an ONNX model."""

    def __init__(self, repo_id: str | None = None) -> None:
        self.repo_id = repo_id or settings.onnx_reranker_repo
        self._disabled = False
        self._session = None
        self._tokenizer = None
        self._input_names: list[str] = []
        self._load()

    def _load(self) -> None:
        try:
            from tokenizers import Tokenizer

            import onnxruntime as ort

            model_path, tokenizer_path = _resolve_model(self.repo_id, allow_download=False)
            tok = Tokenizer.from_file(tokenizer_path)
            tok.enable_truncation(max_length=_MAX_SEQ)
            if tok.token_to_id("[PAD]") is not None:
                tok.enable_padding(pad_id=tok.token_to_id("[PAD]"), pad_token="[PAD]")
            session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self._input_names = [i.name for i in session.get_inputs()]
            self._session = session
            self._tokenizer = tok
            logger.info("ONNX reranker ready: %s (%s)", self.repo_id, os.path.basename(model_path))
        except Exception as exc:  # noqa: BLE001 - reranking is best-effort: score order when unavailable
            self._disabled = True
            logger.warning("ONNX reranker unavailable (%s); using score order", exc)

    def is_available(self) -> bool:
        return not self._disabled and self._session is not None and self._tokenizer is not None

    def rerank(self, query: str, candidates: list[dict], keep: int) -> list[dict]:
        if not self.is_available():
            raise RuntimeError(f"ONNX reranker unavailable ({self.repo_id})")
        if not candidates:
            return []
        pairs = [[query, c.get("content", c.get("doc_id", ""))] for c in candidates]
        encodings = [self._tokenizer.encode(q, d) for q, d in pairs]  # type: ignore[union-attr]
        input_ids = np.asarray([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.asarray([e.attention_mask for e in encodings], dtype=np.int64)
        feeds: dict[str, np.ndarray] = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)
        logits = np.asarray(self._session.run(None, feeds)[0], dtype=np.float32).reshape(-1)  # type: ignore[union-attr]
        scores = 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))
        ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
        return [dict(c, score=float(s)) for c, s in ranked[:keep]]


_embedder: OnnxEmbedder | None = None
_reranker: OnnxReranker | None = None


def get_onnx_embedder() -> OnnxEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = OnnxEmbedder()
    return _embedder


def get_onnx_reranker() -> OnnxReranker:
    global _reranker
    if _reranker is None:
        _reranker = OnnxReranker()
    return _reranker
