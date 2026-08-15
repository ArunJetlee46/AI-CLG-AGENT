import logging
import re

from app.config import get_settings
from app.services.rag.curriculum import get_curriculum_rag
from app.services.rag.llm import LLMResponse, get_llm_gateway
from app.services.rag.pipeline import KeywordIndex, get_keyword_index, split_sentences, tokenize
from app.services.rag.vector_store import get_embedder, get_reranker, get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

_OFFLINE_PROVIDER = "offline-extractive"
_COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,4}\s?\d{3}\b")
_GROUNDED_HINT = (
    "I couldn't find that in the knowledge base. I only answer from "
    "evidence, so I won't guess. I cover the Anna University AI&DS (Reg 2021) "
    "curriculum: regulations, program outcomes, semester-wise courses, and "
    "course syllabi (codes like MA3151 or CS3491). If your question is about "
    "something else, the document may not be ingested yet."
)


class RAGService:
    """Hybrid retrieval pipeline.

    retrieve:
      keyword index (always available)  +  embedding search (Qdrant/Chroma when up)
      -> merge/dedupe -> rerank (bge-reranker-base when installed) -> top_k

    answer:
      grounded generation over retrieved chunks with per-chunk citations; refuses
      to free-generate when no context is available (hallucination guard).

    answer_offline:
      retrieval-only extractive answer - no LLM call (offline-first guarantee).
    """

    def __init__(self, keyword_index: KeywordIndex | None = None) -> None:
        self.store = get_vector_store()
        self.embedder = get_embedder()
        self.reranker = get_reranker()
        self.llm = get_llm_gateway()
        self.keyword: KeywordIndex = keyword_index or get_keyword_index()

    # ---- retrieval ------------------------------------------------------

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or settings.rag_top_k
        candidates: list[dict] = []

        if self.store is not None:
            try:
                embedding = self.embedder.embed_one(query)
                candidates.extend(self.store.search(embedding, settings.rag_candidates))
            except Exception as exc:  # noqa: BLE001 - vector retrieval is best-effort
                logger.warning("vector retrieval failed (%s); keyword-only fallback", exc)

        # Keyword retrieval always runs - offline-first guarantee.
        try:
            candidates.extend(self.keyword.search(query, settings.rag_candidates))
        except Exception as exc:  # noqa: BLE001
            logger.warning("keyword retrieval failed: %s", exc)

        merged = self._dedupe(candidates)
        merged = self._boost_course_codes(query, merged)
        return self.reranker.rerank(query, merged, keep=top_k)

    @staticmethod
    def _boost_course_codes(query: str, candidates: list[dict]) -> list[dict]:
        """When the query names exact course codes (e.g. MA3151), promote chunks
        that contain those codes ahead of purely semantic neighbors."""
        codes = _COURSE_CODE_RE.findall(query.upper())
        if not codes or not candidates:
            return candidates
        codes = {c.replace(" ", "") for c in codes}

        def contains_code(chunk: dict) -> bool:
            text = f"{chunk.get('content', '')} {chunk.get('title', '')}".upper()
            return any(f"\n{code}" in f"\n{text}" or f"{code} " in f" {text} " for code in codes)

        exact = [c for c in candidates if contains_code(c)]
        rest = [c for c in candidates if not contains_code(c)]
        return exact + rest if exact else candidates

    @staticmethod
    def _dedupe(candidates: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for c in candidates:
            key = c.get("content") or c.get("doc_id") or c.get("chunk_id")
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    # ---- ingestion -------------------------------------------------------

    def index_documents(self, docs: list[dict]) -> int:
        """Pre-chunked docs for back-compat; prefer pipeline.ingest_documents."""
        count = 0
        for doc in docs:
            chunk_id = str(doc["id"])
            if self.store is not None:
                self.store.upsert(chunk_id, self.embedder.embed_one(doc["content"]), payload=doc)
            count += 1
        return count

    # ---- generation ------------------------------------------------------

    def answer(self, query: str, require_grounded: bool = True) -> tuple[str, list[str], LLMResponse]:
        """Grounded RAG answer with citations.

        Hallucination guard: when no context was retrieved and require_grounded is
        True, we never let the LLM free-generate on an empty context - we return a
        safe extractive/refusal response instead.
        """
        chunks = self.retrieve(query)
        citations = [self._cite(i, c) for i, c in enumerate(chunks)]

        if not chunks:
            if require_grounded:
                external = self._ask_curriculum_rag(query)
                if external is not None:
                    answer, citations = external
                    return answer, citations, LLMResponse(
                        content=answer, provider="college-ai", model="curriculum-rag", latency_ms=0
                    )
                msg = _GROUNDED_HINT
                return msg, [], LLMResponse(
                    content=msg, provider="grounding-guard", model="refusal-heuristic", latency_ms=0
                )
            response = self.llm.complete(
                [
                    {"role": "system", "content": "You are Beru Campus AI, a university assistant. Answer helpfully and briefly."},
                    {"role": "user", "content": query},
                ]
            )
            return response.content, [], response

        context = "\n\n".join(f"[{i}] {c.get('content', '')}" for i, c in enumerate(chunks))
        system = (
            "You are Beru Campus AI. Answer using ONLY the provided context. "
            "Cite sources as [0], [1], ... where each bracket number maps to the "
            "context list above. If the context does not contain the answer, say "
            "you don't know. Do not invent facts, figures, or procedures."
        )
        response = self.llm.complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"},
            ]
        )

        if response.provider == "local-fallback":
            # LLM down but we have evidence: fall back to extraction, not generation.
            return self.answer_offline(query)

        # The main KB had evidence but the model refused / could not answer:
        # consult the curriculum RAG before settling on a weak reply.
        if self._is_refusal(response.content):
            external = self._ask_curriculum_rag(query)
            if external is not None:
                answer, ext_citations = external
                return answer, ext_citations, LLMResponse(
                    content=answer, provider="college-ai", model="curriculum-rag", latency_ms=0
                )
        return response.content, citations, response

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        lowered = answer.lower()
        markers = (
            "don't know", "do not know", "cannot answer", "can't answer",
            "could not find", "not in the context", "does not contain",
            "not mentioned", "unavailable", "no information",
            "couldn't find", "couldn't find any",
        )
        return any(m in lowered for m in markers)

    def answer_offline(self, query: str) -> tuple[str, list[str], LLMResponse]:
        """Retrieval-only answer. Never calls an LLM - the offline-first guarantee."""
        chunks = self.retrieve(query)
        if not chunks:
            msg = "No matching documents found in the knowledge base."
            return msg, [], LLMResponse(content=msg, provider=_OFFLINE_PROVIDER, model="extractive", latency_ms=0)

        excerpts = [self._best_sentence(c.get("content", ""), query) for c in chunks[:3]]
        answer = "From the Beru knowledge base:\n\n" + "\n\n".join(f"- {ex}" for ex in excerpts)
        citations = [self._cite(i, c) for i, c in enumerate(chunks[:3])]
        return answer, citations, LLMResponse(
            content=answer, provider=_OFFLINE_PROVIDER, model="extractive", latency_ms=0
        )

    # ---- helpers ---------------------------------------------------------

    def _ask_curriculum_rag(self, query: str) -> tuple[str, list[str]] | None:
        """In-process fallback to the curriculum RAG when the local knowledge
        base has no evidence for the question (or the main LLM refuses)."""
        if not settings.curriculum_rag_enabled:
            return None
        try:
            result = get_curriculum_rag().answer(query)
        except Exception as exc:  # noqa: BLE001 - the fallback must never break the answer path
            logger.warning("curriculum RAG fallback unavailable: %s", exc)
            return None
        if not result.get("grounded"):
            return None
        citations = []
        for i, s in enumerate(result.get("sources", [])):
            title = s.get("course_title") or s.get("document") or f"college-ai-{i}"
            page = s.get("page_start")
            citations.append(f"[{i}] {title} (p.{page})" if page else f"[{i}] {title}")
        return result["answer"], citations

    @staticmethod
    def _best_sentence(text: str, query: str) -> str:
        q = set(tokenize(query))
        sentences = split_sentences(text)
        if not sentences:
            return text[:500]
        return max(sentences, key=lambda s: sum(1 for _ in set(tokenize(s)) & q), default=sentences[0])[:500]

    @staticmethod
    def _cite(i: int, chunk: dict) -> str:
        title = chunk.get("title") or chunk.get("doc_id") or f"doc-{i}"
        source = chunk.get("source")
        if source and source != title:
            return f"[{i}] {title} ({source})"
        return f"[{i}] {title}"


_rag: RAGService | None = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
