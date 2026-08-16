"""AI evaluation tests (Phase 12): grounding accuracy + hallucination rate.

The harness in app/services/evaluation.py produces deterministic metrics on a
fixed corpus. Thresholds below encode the product guarantee: every answerable
question must be answered with evidence, and every out-of-corpus question must
be refused rather than hallucinated.
"""

from app.services import evaluation
from app.services.evaluation import build_rag, evaluate_guard, evaluate_offline


def test_eval_corpus_answers_all_grounded_cases() -> None:
    rag = build_rag()
    metrics = evaluate_offline(rag)

    assert metrics["grounded_cases"] == len(evaluation.GROUNDED_CASES)
    assert metrics["grounding_accuracy"] == 1.0
    assert metrics["citation_coverage"] == 1.0


def test_eval_corpus_refuses_all_out_of_corpus_probes() -> None:
    rag = build_rag()
    metrics = evaluate_offline(rag)

    assert metrics["probe_cases"] == len(evaluation.HALLUCINATION_PROBES)
    assert metrics["hallucination_rate"] == 0.0
    assert metrics["refusal_rate"] == 1.0


def test_grounding_guard_catches_all_probes_on_llm_path() -> None:
    rag = build_rag()
    metrics = evaluate_guard(rag)

    assert metrics["guard_rate"] == 1.0
    assert metrics["probe_cases"] == len(evaluation.HALLUCINATION_PROBES)


def test_grounded_answer_contains_expected_fact_verbatim() -> None:
    rag = build_rag()
    answer, citations, response = rag.answer_offline(
        "what are the library opening hours"
    )
    assert response.provider == "offline-extractive"
    assert "08:00 until 22:00" in answer
    assert citations and "Library" in citations[0]


def test_metrics_are_deterministic() -> None:
    first = evaluate_offline(build_rag())
    second = evaluate_offline(build_rag())
    assert first == second
