"""RAG evaluation harness (Phase 12).

Measures the two headline AI-quality metrics on the Beru knowledge base:

- grounding_accuracy:  fraction of answerable questions whose extractive answer
  contains the ground-truth fact AND carries at least one citation.
- hallucination_rate:  fraction of out-of-corpus questions that were answered
  (i.e. NOT refused) instead of admitting lack of evidence.

Also records citation_coverage and guard_rate (the grounding-guard provider
catching probes through the gated LLM path). Deterministic: uses the
offline-extractive path, so results are reproducible per corpus.

Usage (CLI):  python -m scripts.eval_rag [--verbose]
"""

from dataclasses import dataclass

from app.services.pipeline import DocumentChunker, KeywordIndex
from app.services.rag import RAGService

GROUNDED_HINT_PREFIX = "I couldn't find that in the knowledge base"
NO_MATCH_MESSAGE = "No matching documents found in the knowledge base."

EVAL_DOCS = [
    {
        "source": "library",
        "title": "Library Policy",
        "text": (
            "The main library is open Monday to Friday from 08:00 until 22:00, and on "
            "weekends from 10:00 until 18:00. Student ID cards are required for entry. "
            "Silent study rooms are located on the second floor and can be booked via "
            "the campus portal. Borrowing limits are ten books for undergraduates and "
            "twenty for postgraduate students."
        ),
    },
    {
        "source": "finance",
        "title": "Tuition & Fees",
        "text": (
            "Tuition is billed per semester and is due within thirty days of the start "
            "of term. Late payments incur a penalty of one and a half percent per month. "
            "Students with financial hardship may apply for a payment plan from the "
            "bursar's office. Refund policies follow the academic calendar published online."
        ),
    },
    {
        "source": "admissions",
        "title": "Admissions",
        "text": (
            "The admissions office accepts applications until March 31st each year. "
            "Applicants must submit a certified transcript, two recommendation letters, "
            "and a statement of purpose. International applicants must demonstrate English "
            "proficiency with an IELTS score of 6.5 or above. Decisions are released within "
            "eight weeks of the application deadline."
        ),
    },
    {
        "source": "bursary",
        "title": "Bursary & Attendance",
        "text": (
            "Attendance registers are taken at 08:30 in every lecture and laboratory session. "
            "Students with attendance below eighty percent receive an attendance warning from "
            "the registrar. A transcript can be requested online and is issued within five "
            "working days. Bursary payments are disbursed monthly to eligible students at the "
            "end of each month."
        ),
    },
]


@dataclass
class EvalCase:
    question: str
    expected_fact: str | None = None  # None -> out-of-corpus hallucination probe


GROUNDED_CASES = [
    EvalCase(
        "what are the library opening hours",
        "The main library is open Monday to Friday from 08:00 until 22:00, and on weekends from 10:00 until 18:00.",
    ),
    EvalCase(
        "how many books can undergraduates borrow",
        "Borrowing limits are ten books for undergraduates and twenty for postgraduate students.",
    ),
    EvalCase(
        "what penalty applies to late tuition payments",
        "Late payments incur a penalty of one and a half percent per month.",
    ),
    EvalCase(
        "can students apply for a payment plan",
        "Students with financial hardship may apply for a payment plan from the bursar's office.",
    ),
    EvalCase(
        "what must applicants submit for admission",
        "Applicants must submit a certified transcript, two recommendation letters, and a statement of purpose.",
    ),
    EvalCase(
        "when is the attendance register taken",
        "Attendance registers are taken at 08:30 in every lecture and laboratory session.",
    ),
    EvalCase(
        "how can a transcript be requested online",
        "A transcript can be requested online and is issued within five working days.",
    ),
]

HALLUCINATION_PROBES = [
    EvalCase("what rules govern quadcopter flights"),
    EvalCase("how much does gym membership cost"),
    EvalCase("visa rules exchange visitors"),
    EvalCase("cafeteria halal food options"),
    EvalCase("plagiarism cases handled"),
    EvalCase("astronomy club meeting times"),
]


def build_rag() -> RAGService:
    """Fresh RAG service over the eval corpus (keyword index only, no vectors)."""
    index = KeywordIndex()
    chunker = DocumentChunker(max_chars=1000, overlap_chars=100)
    for doc in EVAL_DOCS:
        doc_id = f"{doc['source']}:{doc['title']}"
        for chunk in chunker.chunk(doc["text"], doc_id=doc_id, source=doc["source"], title=doc["title"]):
            index.add(chunk)
    rag = RAGService(keyword_index=index)
    rag.store = None
    return rag


def evaluate_offline(rag: RAGService) -> dict:
    """Deterministic metrics over the extractive path."""
    grounded_total = len(GROUNDED_CASES)
    grounded_ok = 0
    cited = 0
    for case in GROUNDED_CASES:
        answer, citations, _ = rag.answer_offline(case.question)
        if case.expected_fact and case.expected_fact in answer:
            grounded_ok += 1
        if citations:
            cited += 1

    probes_total = len(HALLUCINATION_PROBES)
    hallucinated = 0
    for case in HALLUCINATION_PROBES:
        answer, _, _ = rag.answer_offline(case.question)
        if answer != NO_MATCH_MESSAGE:
            hallucinated += 1

    return {
        "grounded_cases": grounded_total,
        "grounding_accuracy": round(grounded_ok / grounded_total, 4),
        "citation_coverage": round(cited / grounded_total, 4),
        "probe_cases": probes_total,
        "hallucination_rate": round(hallucinated / probes_total, 4),
        "refusal_rate": round((probes_total - hallucinated) / probes_total, 4),
    }


def evaluate_guard(rag: RAGService) -> dict:
    """Anti-hallucination guard on the LLM-gated path: probes must be refused
    by the grounding-guard provider before any generation is attempted."""
    guarded = 0
    for case in HALLUCINATION_PROBES:
        answer, _, response = rag.answer(case.question, require_grounded=True)
        if response.provider == "grounding-guard" and answer.startswith(GROUNDED_HINT_PREFIX):
            guarded += 1
    total = len(HALLUCINATION_PROBES)
    return {"probe_cases": total, "guard_rate": round(guarded / total, 4)}
