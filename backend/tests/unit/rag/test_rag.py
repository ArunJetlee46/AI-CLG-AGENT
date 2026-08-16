from app.config import get_settings
from app.services.llm import LLMResponse
from app.services.pipeline import DocumentChunker, KeywordIndex, ingest_documents
from app.services.rag import RAGService

settings = get_settings()

LIBRARY_TEXT = (
    "The main library is open Monday to Friday from 08:00 until 22:00, and on "
    "weekends from 10:00 until 18:00. Student ID cards are required for entry. "
    "Silent study rooms are located on the second floor and can be booked via "
    "the campus portal. Borrowing limits are ten books for undergraduates and "
    "twenty for postgraduate students."
)

FEES_TEXT = (
    "Tuition is billed per semester and is due within thirty days of the start "
    "of term. Late payments incur a penalty of one and a half percent per month. "
    "Students with financial hardship may apply for a payment plan from the "
    "bursar's office. Refund policies follow the academic calendar published online."
)


class FakeLLM:
    def __init__(self) -> None:
        self.calls = []

    def complete(self, messages, tools=None, on_token=None) -> LLMResponse:
        self.calls.append(messages)
        content = "The library closes at 22:00 according to the library policy [0]."
        if on_token:
            on_token(content)
        return LLMResponse(content=content, provider="fake", model="test", latency_ms=1)


def make_rag(keyword: KeywordIndex | None = None, llm=None, store=None):
    rag = RAGService(keyword_index=keyword or KeywordIndex())
    rag.store = store
    if llm is not None:
        rag.llm = llm
    return rag


def test_chunker_chunks_and_overlaps() -> None:
    chunker = DocumentChunker(max_chars=200, overlap_chars=40)
    chunks = chunker.chunk(FEES_TEXT, doc_id="fees-1", source="finance", title="Tuition")
    assert len(chunks) >= 2
    assert all(len(c.content) <= 200 + 10 for c in chunks)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.source == "finance" and c.title == "Tuition" for c in chunks)
    # boundary context carried over via overlap
    assert FEES_TEXT.split()[0] in chunks[0].content


def test_keyword_index_ranks_relevant_first() -> None:
    idx = KeywordIndex()
    chunker = DocumentChunker(max_chars=1000, overlap_chars=100)
    for c in chunker.chunk(LIBRARY_TEXT, doc_id="lib", source="library", title="Library"):
        idx.add(c)
    for c in chunker.chunk(FEES_TEXT, doc_id="fees", source="finance", title="Tuition"):
        idx.add(c)

    hits = idx.search("library opening hours", top_k=5)
    assert hits and hits[0]["title"] == "Library"
    assert hits[0]["score"] > 0

    absent = idx.search("gymnasium pool schedule", top_k=5)
    assert absent == []


def test_ingest_and_offline_extractive_answer(monkeypatch) -> None:
    # force a fresh global keyword index + RAG singleton and disable vector store
    monkeypatch.setattr("app.services.rag.engine.get_vector_store", lambda: None)
    monkeypatch.setattr("app.services.pipeline._keyword_index", None)
    monkeypatch.setattr("app.services.rag.engine._rag", None)

    stats = ingest_documents(
        [
            {"source": "library", "title": "Library", "text": LIBRARY_TEXT},
            {"source": "finance", "title": "Tuition", "text": FEES_TEXT},
        ]
    )
    # ingestion fed the keyword index even without a vector store
    assert stats["chunks"] >= 2
    assert stats["vector_upserts"] == 0

    from app.services.rag import get_rag

    answer, citations, response = get_rag().answer_offline("what time does the library close")
    assert response.provider == "offline-extractive"
    assert "22:00" in answer
    assert citations and "Library" in citations[0]


def test_grounded_guard_refuses_empty_context() -> None:
    fake = FakeLLM()
    rag = make_rag(llm=fake)  # empty keyword index, store None
    answer, citations, response = rag.answer("tell me about quantum physics phd admissions")
    assert response.provider == "grounding-guard"
    assert "couldn't find that in the knowledge base" in answer
    assert citations == []
    assert fake.calls == [], "no generation is allowed without grounding context"


def test_answer_grounds_on_context_with_citations() -> None:
    fake = FakeLLM()
    idx = KeywordIndex()
    chunker = DocumentChunker(max_chars=1000, overlap_chars=100)
    for c in chunker.chunk(LIBRARY_TEXT, doc_id="lib", source="library", title="Library Hours"):
        idx.add(c)
    rag = make_rag(keyword=idx, llm=fake)

    answer, citations, response = rag.answer("when does the library close")
    assert fake.calls, "LLM should be called when context is present"
    # grounding: the CONTEXT block is present in the user turn
    assert any("CONTEXT:" in (m.get("content") or "") for m in fake.calls[0])
    assert response.content.startswith("The library closes")
    assert citations and citations[0].startswith("[0]") and "Library" in citations[0]
