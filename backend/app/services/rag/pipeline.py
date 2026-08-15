import hashlib
import logging
import re
import threading
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_SPLIT = re.compile(r"[\w']+", re.UNICODE)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "to", "of", "in", "on", "at",
    "by", "with", "from", "is", "are", "was", "were", "be", "been", "do", "does",
    "did", "can", "could", "would", "should", "will", "may", "might", "must",
    "what", "which", "when", "where", "who", "whom", "whose", "why", "how",
    "i", "me", "my", "you", "your", "he", "she", "it", "we", "they", "this",
    "that", "these", "those", "there", "here", "s", "t", "about", "than", "not",
    "no", "yes", "so", "as", "if", "into", "up", "out", "over", "under", "again",
    "then", "them", "his", "her", "its", "our", "their", "has", "have", "had",
}


def tokenize(text: str) -> list[str]:
    """Lower-case alphanumeric tokens. Shared with the hash-embedding fallback,
    so keyword retrieval and embedding retrieval stay vocabulary-consistent."""
    return _WORD_SPLIT.findall(text.lower())


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


@dataclass
class Chunk:
    chunk_id: str        # unique id incl. chunk index (used as store/keyword key)
    doc_id: str          # logical source document id (shared across chunks)
    source: str
    title: str
    chunk_idx: int
    content: str

    def to_payload(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "title": self.title,
            "chunk_idx": self.chunk_idx,
            "content": self.content,
        }


class DocumentChunker:
    """Sentence-streaming chunker with configurable max size and tail overlap.

    Splits long text into overlapping chunks (default 1200 chars, 150 overlap)
    so context on chunk boundaries is not lost. Paragraphs and sentences are the
    preferred split points because they are natural semantic units.
    """

    def __init__(self, max_chars: int | None = None, overlap_chars: int | None = None):
        self.max_chars = max_chars or settings.chunk_size_chars
        self.overlap_chars = overlap_chars or settings.chunk_overlap_chars

    def chunk(self, text: str, doc_id: str, source: str = "", title: str = "") -> list[Chunk]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        if len(normalized) <= self.max_chars:
            return [Chunk(f"{doc_id}#0", doc_id, source, title, 0, normalized)]

        sentences = split_sentences(normalized)
        chunks: list[Chunk] = []
        current: list[str] = []
        current_len = 0

        for sent in sentences:
            # push current sentence list into a chunk when adding would overflow
            if current and current_len + len(sent) + 1 > self.max_chars and len(current) > 1:
                text_chunk = " ".join(current)
                chunk_idx = len(chunks)
                chunks.append(Chunk(f"{doc_id}#{chunk_idx}", doc_id, source, title, chunk_idx, text_chunk))
                # keep only the tail words within overlap_chars as the new open chunk
                tail: list[str] = []
                tail_chars = 0
                for word in reversed(text_chunk.split()):
                    if tail and tail_chars + len(word) + 1 > self.overlap_chars:
                        break
                    tail.insert(0, word)
                    tail_chars += len(word) + 1
                current = tail
                current_len = sum(len(w) + 1 for w in current)

            current.append(sent)
            current_len += len(sent) + 1

        if current:
            chunk_idx = len(chunks)
            chunks.append(Chunk(f"{doc_id}#{chunk_idx}", doc_id, source, title, chunk_idx, " ".join(current)))
        return chunks


class KeywordIndex:
    """In-memory, thread-safe inverted index powering retrieval **without** a
    vector DB or embedding model (offline-first guarantee).

    Terms are tokenized exactly like the hash-embedding fallback and ranked by
    length-normalized term-frequency overlap, which is good enough for a campus
    knowledge base while keeping the system fully hermetic.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._docs: dict[str, Chunk] = {}
        self._freq: dict[str, dict[str, int]] = {}
        self._lengths: dict[str, int] = {}

    def add(self, chunk: Chunk) -> None:
        with self._lock:
            self._docs[chunk.chunk_id] = chunk
            freq: dict[str, int] = {}
            for t in tokenize(chunk.content):
                freq[t] = freq.get(t, 0) + 1
            self._freq[chunk.chunk_id] = freq
            self._lengths[chunk.chunk_id] = sum(freq.values())

    def count(self) -> int:
        with self._lock:
            return len(self._docs)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        with self._lock:
            qterms = {t for t in tokenize(query) if t not in _STOPWORDS}
            if not qterms:
                return []
            scores: dict[str, float] = {}
            for chunk_id, freq in self._freq.items():
                overlap = sum(freq.get(t, 0) for t in qterms)
                if overlap:
                    # length-normalized overlap -> favors precise hits
                    scores[chunk_id] = overlap / (max(1, self._lengths[chunk_id]) ** 0.5)
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
            return [
                {"score": round(sc, 4), "chunk_id": chunk_id, **self._docs[chunk_id].to_payload()}
                for chunk_id, sc in ranked
            ]


_keyword_index: KeywordIndex | None = None


def get_keyword_index() -> KeywordIndex:
    global _keyword_index
    if _keyword_index is None:
        _keyword_index = KeywordIndex()
    return _keyword_index


def ingest_documents(docs: list[dict]) -> dict:
    """Pipeline: raw docs -> chunk -> (embed+upsert into vector store) -> keyword index.

    docs: [{"id"?: str, "source": str, "title": str, "text": str}]

    Returns stats. Keyword indexing always runs (offline-first); vector upserts
    happen only when a vector store is available.
    """
    from app.services.rag.engine import get_rag

    rag = get_rag()
    keyword = get_keyword_index()
    stats = {"docs_seen": 0, "chunks": 0, "vector_upserts": 0}

    pending: list[tuple[str, dict]] = []  # (chunk_id, payload) awaiting batch embedding

    def flush_pending() -> None:
        if rag.store is None or not pending:
            pending.clear()
            return
        try:
            vectors = rag.embedder.embed([p[1].get("content", "") for p in pending])
            for (chunk_id, payload), vector in zip(pending, vectors):
                rag.store.upsert(chunk_id, vector, payload=payload)
            stats["vector_upserts"] += len(pending)
        except Exception as exc:  # noqa: BLE001 - vector store must never block ingestion
            logger.warning("vector upsert batch failed (%d chunks): %s", len(pending), exc)
        pending.clear()

    for doc in docs:
        doc_id = str(doc.get("id") or f"{doc.get('source', 'doc')}:{doc.get('title', '')}")
        chunks = DocumentChunker().chunk(
            doc.get("text", ""), doc_id=doc_id, source=doc.get("source", ""), title=doc.get("title", "")
        )
        stats["docs_seen"] += 1
        for chunk in chunks:
            payload = chunk.to_payload()
            if rag.store is not None:
                # idempotent boot: skip chunks already embedded so restarts stay fast
                try:
                    already_embedded = rag.store.has(chunk.chunk_id)
                except Exception:  # noqa: BLE001 - never let a store probe block ingestion
                    already_embedded = False
                if not already_embedded:
                    pending.append((chunk.chunk_id, payload))
                    if len(pending) >= 16:
                        flush_pending()
            keyword.add(chunk)
            stats["chunks"] += 1
    flush_pending()
    if stats["chunks"]:
        logger.info("ingested %s chunks from %s docs (%s vector upserts)",
                    stats["chunks"], stats["docs_seen"], stats["vector_upserts"])
    return stats


def ingest_curriculum() -> dict:
    """Ingest the curriculum corpus (Anna University AIDS Reg 2021 JSONL) into
    the 'curriculum' vector-store collection. Idempotent: chunks already embedded
    are skipped, so restarts stay fast. Returns stats."""
    from app.services.rag.curriculum import load_curriculum_chunks
    from app.services.rag.vector_store import get_curriculum_vector_store, get_embedder

    chunks = load_curriculum_chunks()
    if not chunks:
        logger.info("curriculum ingest skipped: no corpus chunks loaded")
        return {"chunks": 0, "vector_upserts": 0}
    store = get_curriculum_vector_store()
    stats = {"chunks": len(chunks), "vector_upserts": 0}
    if store is None:
        logger.warning("curriculum ingest: no vector store available; skipping embeddings")
        return stats

    embedder = get_embedder()
    pending: list[tuple[str, dict]] = []
    upserts = 0

    def flush_pending() -> None:
        nonlocal upserts
        if not pending:
            return
        try:
            vectors = embedder.embed([p[1]["content"] for p in pending])
            for (doc_id, payload), vector in zip(pending, vectors):
                store.upsert(doc_id, vector, payload=payload)
            upserts += len(pending)
            logger.info("curriculum upserted %d chunks (total %d)", len(pending), upserts)
        except Exception as exc:  # noqa: BLE001 - vector store must never block ingestion
            logger.warning("curriculum vector upsert batch failed (%d chunks): %s", len(pending), exc)
        pending.clear()

    for chunk in chunks:
        payload = {
            "doc_id": chunk["doc_id"],
            "content": chunk["content"],
            "document": chunk["document"],
            "page_start": chunk["page_start"],
            "page_end": chunk["page_end"],
            "course_code": chunk.get("course_code") or "",
            "course_title": chunk.get("course_title") or "",
            "regulation": chunk.get("regulation", settings.curriculum_regulation),
            "programme": chunk.get("programme", settings.curriculum_programme),
        }
        try:
            already = store.has(chunk["doc_id"])
        except Exception:  # noqa: BLE001 - never let a store probe block ingestion
            already = False
        if not already:
            pending.append((chunk["doc_id"], payload))
            if len(pending) >= 16:
                flush_pending()
    flush_pending()
    stats["vector_upserts"] = upserts
    logger.info("curriculum ingest: %d chunks (%d vector upserts)", len(chunks), upserts)
    return stats
