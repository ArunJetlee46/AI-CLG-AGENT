"""Tests for the in-process curriculum RAG (merged from college-ai).

Covers retrieval, grounded answers with sources, refusal on unknown questions,
LLM-unavailable behaviour and the keyword-only fallback. Uses a deterministic
hash embedder and a fake LLM gateway so no external service is ever contacted.
"""
import hashlib
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.curriculum_rag import (
    SYSTEM_PROMPT,
    UNAVAILABLE_ANSWER,
    CurriculumRAG,
    CurriculumRetriever,
    load_curriculum_chunks,
)
from app.services.llm import LLMResponse
from app.services.vector_store import ChromaStore

settings = get_settings()
DATA_JSONL = Path(settings.curriculum_rag_jsonl)


def hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic offline embedder so tests never hit real Ollama."""
    out = [0.0] * dim
    for token in str(text).lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(min(4, dim)):
            out[(digest[i] + i) % dim] += 1.0
    norm = max(1.0, sum(out))
    return [v / norm for v in out]


class FakeGateway:
    """Deterministic fake so tests do not depend on the real LLM gateway."""

    def __init__(self, fail: bool = False, reply: str = "Grounded reply.") -> None:
        self.fail = fail
        self.reply = reply
        self.calls: list[list[dict]] = []

    def complete(self, messages, tools=None) -> LLMResponse:
        self.calls.append(messages)
        if self.fail:
            return LLMResponse(
                content="[local-fallback] No LLM provider is reachable.",
                provider="local-fallback",
                model="rule-based",
                latency_ms=0,
            )
        question = messages[-1]["content"].split("QUESTION:")[-1].strip().split("\n")[0]
        return LLMResponse(
            content=self.reply.format(question=question), provider="fake", model="test", latency_ms=1
        )


@pytest.fixture(scope="module")
def chunks():
    assert DATA_JSONL.is_file(), f"curriculum corpus missing: {DATA_JSONL}"
    return load_curriculum_chunks()


@pytest.fixture(scope="module")
def vector_store(tmp_path_factory, chunks):
    pytest.importorskip("chromadb", reason="chromadb is an optional dependency (requirements-ml.txt)")
    store = ChromaStore(persist_dir=str(tmp_path_factory.mktemp("chroma")), collection="test_docs")
    for chunk in chunks:
        store.upsert(
            chunk["doc_id"],
            hash_embed(chunk["content"]),
            payload={
                "doc_id": chunk["doc_id"],
                "content": chunk["content"],
                "document": chunk["document"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "course_code": chunk.get("course_code") or "",
                "course_title": chunk.get("course_title") or "",
                "regulation": chunk["regulation"],
                "programme": chunk["programme"],
            },
        )
    return store


def make_ai(store=None, gateway=None, chunks=None, threshold=None) -> CurriculumRAG:
    ai = CurriculumRAG(
        gateway=gateway or FakeGateway(),
        retriever=CurriculumRetriever(chunks=chunks, vector_store=store),
        embedder=hash_embed,
    )
    if threshold is not None:
        settings.curriculum_similarity_threshold = threshold
    return ai


# ---------------------------------------------------------------- retrieval tests

def test_1_course_lookup(chunks, vector_store):
    hits = CurriculumRetriever(chunks=chunks, vector_store=vector_store).retrieve(
        "What is the course AL3451 about?", embedder=hash_embed
    )
    assert hits, "expected retrieval hits"
    assert any("AL3451" in h.get("content", "") for h in hits), "course code chunk should be retrieved"


def test_2_units_retrievable(chunks, vector_store):
    hits = CurriculumRetriever(chunks=chunks, vector_store=vector_store).retrieve(
        "What are the units in Machine Learning?", embedder=hash_embed
    )
    text = " ".join(h.get("content", "") for h in hits).upper().replace("  ", " ")
    assert "UNIT I" in text, "unit headings should be in context"


def test_3_textbook_retrievable(chunks, vector_store):
    hits = CurriculumRetriever(chunks=chunks, vector_store=vector_store).retrieve(
        "What textbook is recommended for Machine Learning?", embedder=hash_embed
    )
    text = " ".join(h.get("content", "") for h in hits).upper()
    assert "TEXT BOOK" in text, "textbook section should be retrieved"


def test_4_source_metadata_preserved(chunks):
    assert all("content" in c and "page_start" in c and "page_end" in c and "document" in c for c in chunks)
    assert any(c.get("course_code") for c in chunks), "some chunks should carry course codes"
    assert any(c.get("course_title") for c in chunks), "some chunks should carry course titles"


# ---------------------------------------------------------------- generation tests

def test_5_grounded_answer_with_sources(chunks, vector_store):
    ai = make_ai(vector_store, FakeGateway(reply="According to the context, {question}"), chunks)
    res = ai.answer("What is the course AL3451 about?")
    assert res["grounded"] is True
    assert res["sources"], "sources must be attached to grounded answers"
    assert res["sources"][0]["document"], "source must include document name"
    assert "page_start" in res["sources"][0] and "page_end" in res["sources"][0]


def test_6_system_prompt_enforces_grounding():
    assert "Do not invent" in SYSTEM_PROMPT
    assert "unavailable" in SYSTEM_PROMPT.lower()


def test_7_unknown_question_no_fabrication(chunks, vector_store, monkeypatch):
    monkeypatch.setattr(settings, "curriculum_similarity_threshold", 0.99)  # nothing can pass 0.99
    ai = make_ai(vector_store, FakeGateway(), chunks)
    res = ai.answer("What is tomorrow's college timetable?")
    assert res["grounded"] is False
    assert "I could not find that information" in res["answer"]


def test_8_llm_unavailable(chunks, vector_store):
    ai = make_ai(vector_store, FakeGateway(fail=True), chunks)
    res = ai.answer("What is the course AL3451 about?")
    # never answer from memory when the LLM is down
    assert "I could not find that information" in res["answer"]
    assert res["grounded"] is False


def test_9_vector_db_unavailable(chunks):
    ai = make_ai(None, FakeGateway(reply="Grounded {question}"), chunks)
    res = ai.answer("What is the course AL3451 about?")
    assert res["answer"]  # keyword-only fallback still answers


def test_10_empty_question():
    ai = make_ai(None, FakeGateway())
    res = ai.answer("   ")
    assert "I could not find that information" in res["answer"]


def test_11_unavailable_answer_constant():
    assert UNAVAILABLE_ANSWER == "I could not find that information in the college knowledge base."
