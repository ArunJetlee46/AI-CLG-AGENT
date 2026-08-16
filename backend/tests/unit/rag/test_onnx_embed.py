"""ONNX embedder / reranker wiring tests (Phase A).

Tests are hermetic: conftest pins EMBEDDING_BACKEND=local, and the ONNX
download path is stubbed so the suite never touches the network. Real-model
checks run only when the artifacts are fully cached locally.
"""
import glob
import os

import pytest

from app.config import get_settings
from app.services.rag.vector_store import (
    EmbeddingService,
    _embedding_dimension,
    get_embedder,
    get_reranker,
)

settings = get_settings()


def _has_onnx(repo_id: str) -> bool:
    cache_dir = os.path.join(settings.onnx_model_dir, repo_id.replace("/", "_"))
    return bool(glob.glob(os.path.join(cache_dir, "onnx", "*.onnx")))


class _Unavailable:
    def is_available(self) -> bool:
        return False


def test_hash_fallback_when_onnx_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "onnx")
    monkeypatch.setattr("app.services.rag.onnx.get_onnx_embedder", lambda: _Unavailable())

    vectors = get_embedder().embed(["hello world", "hello world", "another thing"])
    assert len(vectors) == 3
    assert all(len(v) == 384 for v in vectors)
    assert vectors[0] == vectors[1]  # deterministic
    assert vectors[0] != vectors[2]


def test_onnx_path_used_when_available(monkeypatch) -> None:
    class _FakeOnnx:
        def is_available(self) -> bool:
            return True

        def embed(self, texts):
            return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(settings, "embedding_backend", "onnx")
    monkeypatch.setattr("app.services.rag.onnx.get_onnx_embedder", lambda: _FakeOnnx())

    assert get_embedder().embed(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]


def test_reranker_falls_back_to_score_order(monkeypatch) -> None:
    monkeypatch.setattr("app.services.rag.onnx.get_onnx_reranker", lambda: _Unavailable())

    docs = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
    ranked = get_reranker().rerank("query", docs, keep=2)
    assert [d["content"] for d in ranked] == ["a", "b"]
    assert ranked[0].get("score") is None  # no rerank -> original order, no score added


def test_reranker_uses_onnx_order_when_available(monkeypatch) -> None:
    class _FakeReranker:
        def is_available(self) -> bool:
            return True

        def rerank(self, query, candidates, keep):
            return [dict(c, score=float(i)) for i, c in reversed(list(enumerate(candidates[:keep])))]

    monkeypatch.setattr("app.services.rag.onnx.get_onnx_reranker", lambda: _FakeReranker())

    docs = [{"content": "a"}, {"content": "b"}, {"content": "c"}]
    ranked = get_reranker().rerank("query", docs, keep=2)
    assert [d["content"] for d in ranked] == ["b", "a"]
    assert ranked[0]["score"] == 1.0


def test_embedding_dimension_derives_from_embedder(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "local")
    assert _embedding_dimension() == 384  # hash fallback is 384-dim


def test_embedding_dimension_falls_back_to_384(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "ollama")

    def _boom(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(EmbeddingService, "_ollama_embed", _boom)
    assert _embedding_dimension() == 384


def test_onnx_embedder_disables_on_load_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.rag.onnx._resolve_model",
        lambda repo: (_ for _ in ()).throw(RuntimeError("no network")),
    )
    from app.services.rag.onnx import OnnxEmbedder

    embedder = OnnxEmbedder()
    assert embedder.is_available() is False
    with pytest.raises(RuntimeError):
        embedder.embed(["hello"])


@pytest.mark.skipif(
    not _has_onnx(settings.onnx_embedding_repo),
    reason="ONNX embedder artifacts not cached (auto-downloads on first app boot)",
)
def test_onnx_embedder_real_model_vectors() -> None:
    import math

    from app.services.rag.onnx import OnnxEmbedder

    embedder = OnnxEmbedder()
    assert embedder.is_available()
    vectors = embedder.embed(["apples", "apple fruit", "jupiter the planet"])
    assert len(vectors) == 3
    assert all(len(v) == 384 for v in vectors)
    assert all(abs(sum(x * x for x in v) - 1.0) < 1e-3 for v in vectors)

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    assert dot(vectors[0], vectors[1]) > dot(vectors[0], vectors[2]) - 1e-9 or math.isclose(
        dot(vectors[0], vectors[1]), dot(vectors[0], vectors[2])
    )


@pytest.mark.skipif(
    not _has_onnx(settings.onnx_reranker_repo),
    reason="ONNX reranker artifacts not cached (prefetch via python -m scripts.download_onnx_models)",
)
def test_onnx_reranker_real_model_order() -> None:
    from app.services.rag.onnx import OnnxReranker

    reranker = OnnxReranker()
    if not reranker.is_available():
        pytest.skip("ONNX reranker artifacts incomplete")
    docs = [
        {"content": "CS301 timetable: room 401 Monday 9-11, room 402 Wednesday 2-4"},
        {"content": "machine learning course curriculum and prerequisites for B.Tech AI&DS"},
        {"content": "library opening hours and book issue policy"},
    ]
    ranked = reranker.rerank("CS301 timetable room allocation", docs, keep=2)
    assert ranked[0]["content"] == docs[0]["content"]
    assert ranked[0]["score"] >= ranked[1]["score"]
