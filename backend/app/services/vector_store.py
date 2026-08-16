import hashlib
import logging
import time
import uuid
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Local embeddings.

    Preferred: Ollama (nomic-embed-text) via the local server.
    Fallback 1: sentence-transformers (bge-small-en-v1.5) when installed.
    Fallback 2: deterministic hashing (offline guarantee).
    """

    def __init__(self) -> None:
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if settings.embedding_backend == "ollama":
            try:
                return self._ollama_embed(texts)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ollama embeddings failed (%s); falling back to local", exc)
        self._load()
        if self._model:
            return [list(map(float, v)) for v in self._model.encode(texts)]
        return [self._hash_embed(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @staticmethod
    def _ollama_embed(texts: list[str]) -> list[list[float]]:
        import httpx

        resp = httpx.post(
            f"{settings.ollama_base_url}/api/embed",
            json={"model": settings.ollama_embedding_model, "input": texts},
            timeout=120,
        )
        if resp.status_code == 404:
            out: list[list[float]] = []
            for t in texts:
                single = httpx.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embedding_model, "prompt": t},
                    timeout=120,
                )
                single.raise_for_status()
                out.append(single.json()["embedding"])
            return out
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def _load(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(settings.embedding_model)
                logger.info("Embedding model loaded: %s", settings.embedding_model)
            except Exception as exc:  # noqa: BLE001
                logger.warning("sentence-transformers unavailable (%s); using hash fallback embeddings", exc)
                self._model = False

    @staticmethod
    def _hash_embed(text: str, dim: int = 384) -> list[float]:
        out = [0.0] * dim
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(min(4, dim)):
                out[(digest[i] + i) % dim] += 1.0
        norm = max(1.0, sum(out))
        return [v / norm for v in out]


_embedder: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder


class VectorStore(Protocol):
    backend: str

    def search(self, embedding: list[float], top_k: int) -> list[dict]:
        ...

    def upsert(self, doc_id: str, embedding: list[float], payload: dict) -> None:
        ...

    def has(self, doc_id: str) -> bool:
        ...


class QdrantStore:
    backend = "qdrant"

    @staticmethod
    def _to_point_id(doc_id) -> str | int:
        """Qdrant accepts only unsigned-integer or UUID point ids. Map the
        string chunk ids (e.g. 'about:Beru Campus AI#0') deterministically to a
        UUID so upserts and idempotency probes (has) address the same point."""
        if isinstance(doc_id, int):
            return doc_id
        text = str(doc_id)
        if text.isdigit():
            return int(text)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, text))

    def __init__(self, collection: str | None = None) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._client = QdrantClient(url=settings.qdrant_url)
        self._collection = collection or settings.vector_collection
        self._client.get_collections()  # connectivity probe; raises if Qdrant is down
        try:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        except Exception:  # noqa: BLE001 - collection may already exist
            pass
        self._VectorParams = VectorParams  # noqa: N806

    def search(self, embedding: list[float], top_k: int) -> list[dict]:
        points = None
        if hasattr(self._client, "query_points"):
            response = self._client.query_points(
                collection_name=self._collection, query=embedding, limit=top_k
            )
            points = response.points
        elif hasattr(self._client, "search"):
            points = self._client.search(
                collection_name=self._collection, query_vector=embedding, limit=top_k
            )
        else:
            raise RuntimeError("qdrant client has no search/query_points method")
        return [{"score": p.score, **p.payload} for p in points]

    def upsert(self, doc_id: str, embedding: list[float], payload: dict) -> None:
        from qdrant_client.models import PointStruct

        self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=self._to_point_id(doc_id), vector=embedding, payload=payload)],
        )

    def has(self, doc_id: str) -> bool:
        retrieve = getattr(self._client, "retrieve", None)
        if retrieve is None:
            return False
        return bool(retrieve(collection_name=self._collection, ids=[self._to_point_id(doc_id)]))


class ChromaStore:
    backend = "chroma"

    def __init__(self, persist_dir: str | None = None, collection: str | None = None) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(f"ChromaDB unavailable: {exc}") from exc

        if persist_dir:
            # dedicated client (tests / isolated corpora)
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            # one shared client per persist dir -> multiple collections, one lock
            self._client = _get_chroma_client()
        self._col = self._client.get_or_create_collection(collection or settings.vector_collection)

    def search(self, embedding: list[float], top_k: int) -> list[dict]:
        res = self._col.query(query_embeddings=[embedding], n_results=top_k)
        out = []
        for i, doc_id in enumerate(res["ids"][0]):
            distance = res["distances"][0][i]
            # cosine space: distance = 1 - similarity; expose similarity so a
            # single threshold works across backends
            out.append({"score": round(1.0 - distance, 4), "doc_id": doc_id, **(res["metadatas"][0][i] or {})})
        return out

    def upsert(self, doc_id: str, embedding: list[float], payload: dict) -> None:
        self._col.upsert(ids=[doc_id], embeddings=[embedding], metadatas=[payload])

    def has(self, doc_id: str) -> bool:
        return bool(self._col.get(ids=[doc_id], limit=1)["ids"])


_chroma_client = None


def _get_chroma_client():
    """Shared PersistentClient so main + curriculum collections share one lock."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=settings.vector_store_dir)
    return _chroma_client


class RerankerService:
    """Optional local reranker (bge-reranker-base). Falls back to score order."""

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(settings.reranker_model)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Reranker unavailable (%s); using base order", exc)
                self._model = False

    def rerank(self, query: str, candidates: list[dict], keep: int) -> list[dict]:
        self._load()
        if not self._model or not candidates:
            return candidates[:keep]
        pairs = [[query, c.get("content", c.get("doc_id", ""))] for c in candidates]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda p: p[1], reverse=True)
        return [dict(c, score=float(s)) for c, s in ranked[:keep]]


_store: VectorStore | None = None
_curriculum_store: VectorStore | None = None
_reranker: RerankerService | None = None


def _make_store(collection: str) -> VectorStore | None:
    preferred = [settings.vector_store_backend] + [b for b in ("qdrant", "chroma") if b != settings.vector_store_backend]
    for name in preferred:
        cls = {"qdrant": QdrantStore, "chroma": ChromaStore}[name]
        try:
            return cls(collection=collection)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector store '%s' unavailable (%s)", name, exc)
    return None


def get_vector_store() -> VectorStore | None:
    global _store
    if _store is None:
        _store = _make_store(settings.vector_collection)
        if _store is not None:
            logger.info("Vector store backend active: %s", _store.backend)
        else:
            logger.warning("No vector store available; retrieval disabled")
    return _store


def get_curriculum_vector_store() -> VectorStore | None:
    """Second collection (curriculum corpus) in the SAME vector DB client."""
    global _curriculum_store
    if _curriculum_store is None:
        _curriculum_store = _make_store(settings.curriculum_collection)
        if _curriculum_store is not None:
            logger.info("Curriculum vector store active: %s ('%s')", _curriculum_store.backend, settings.curriculum_collection)
        else:
            logger.warning("No curriculum vector store available; keyword-only curriculum retrieval")
    return _curriculum_store


def get_reranker() -> RerankerService:
    global _reranker
    if _reranker is None:
        _reranker = RerankerService()
    return _reranker


def bench_embedding() -> None:
    started = time.perf_counter()
    get_embedder().embed_one("warmup")
    logger.debug("embedding warmup took %.2fs", time.perf_counter() - started)
