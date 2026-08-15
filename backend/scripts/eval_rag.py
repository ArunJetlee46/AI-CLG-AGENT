"""AI evaluation CLI (Phase 12): prints the RAG quality report.

Usage:
    .\\.venv\\Scripts\\python -m scripts.eval_rag [--verbose]

Runs the deterministic offline harness plus the grounding-guard check and
exits non-zero if the product thresholds are breached:
    grounding_accuracy == 1.0   (per corpus guarantee)
    hallucination_rate  == 0.0
    guard_rate          == 1.0
"""

import argparse

from app.services import evaluation
from app.services.evaluation import build_rag, evaluate_guard, evaluate_offline


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG quality evaluation (Phase 12)")
    parser.add_argument("--verbose", action="store_true", help="print per-case results")
    args = parser.parse_args()

    rag = build_rag()
    offline = evaluate_offline(rag)
    guard = evaluate_guard(rag)

    print("=" * 56)
    print("RAG evaluation report — Beru knowledge base (deterministic)")
    print("=" * 56)
    print(f"corpus documents      : {len(evaluation.EVAL_DOCS)}")
    print(f"grounded cases        : {offline['grounded_cases']}")
    print(f"  grounding_accuracy  : {offline['grounding_accuracy']:.2%}")
    print(f"  citation_coverage   : {offline['citation_coverage']:.2%}")
    print(f"hallucination probes  : {offline['probe_cases']}")
    print(f"  hallucination_rate  : {offline['hallucination_rate']:.2%}")
    print(f"  refusal_rate        : {offline['refusal_rate']:.2%}")
    print(f"guard (LLM path)      : {guard['guard_rate']:.2%} probes refused")
    print("=" * 56)

    if args.verbose:
        print("\n-- grounded answers (extractive) --")
        for case in evaluation.GROUNDED_CASES:
            answer, citations, _ = rag.answer_offline(case.question)
            ok = case.expected_fact in answer and bool(citations)
            print(f"[{'OK ' if ok else 'FAIL'}] {case.question}")
            print(f"      {answer[:110]}...")
        print("\n-- hallucination probes --")
        for case in evaluation.HALLUCINATION_PROBES:
            answer, _, response = rag.answer(case.question)
            print(f"[{'REFUSED' if response.provider == 'grounding-guard' else 'ANSWERED'}] {case.question}")

    ok = offline["grounding_accuracy"] == 1.0 and offline["hallucination_rate"] == 0.0 and guard["guard_rate"] == 1.0
    print(f"\nTHRESHOLDS: {'PASS' if ok else 'FAIL'} (accuracy==1.0, hallucination==0.0, guard==1.0)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
