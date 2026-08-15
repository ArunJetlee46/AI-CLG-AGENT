import logging

from app.config import get_settings
from app.db import SessionLocal
from app.models.entities import Enrollment, Prediction, Student

logger = logging.getLogger(__name__)
settings = get_settings()

DEBATE_MAX_ROUNDS = 3
DEBATE_AGREE_DELTA = 0.15
DEBATE_MIN_AGREE = 0.60


def fuse_confidences(pairs: list[tuple[float, float]]) -> float:
    """Weighted-average fusion capped at 0.90 (see Phase 7 §5.2)."""
    weighted = sum(p * w for p, w in pairs)
    return min(0.90, weighted)


class RiskSanityValidator:
    """Independent, rule-based cross-check for risk claims.

    Stands in for the Analytics Agent in the debate (Phase 7 §5): verifies the
    claim against *independent* evidence - data coverage, GPA, failure history -
    rather than the model that produced it. Pure SQL, no LLM, deterministic.
    """

    name = "analytics-sanity"

    def validate(self, claim: dict) -> dict:
        checks: dict[str, bool | None] = {}
        student_id = claim.get("student_id")
        db = SessionLocal()
        try:
            student = (
                db.query(Student).filter(Student.student_id == student_id).first()
                if student_id
                else None
            )
            checks["profile_exists"] = student is not None
            checks["gpa_recorded"] = bool(student and student.gpa is not None)

            failures = 0
            if student:
                failures = db.query(Prediction).filter(Prediction.student_id == student.id).count()
            checks["model_evidence"] = failures > 0

            claim_risk = claim.get("risk_level", "low")
            gpa = student.gpa if student else None
            checks["gpa_supports_claim"] = (gpa is not None) and (
                (gpa < 2.0) if claim_risk == "high" else True
            )
        finally:
            db.close()

        known = [c for c in checks.values() if c is not None]
        supported = sum(1 for c in known if c)
        agreement = supported / len(known) if known else 0.0

        missing = [k for k, v in checks.items() if not v and k in ("profile_exists", "gpa_recorded")]
        if agreement >= DEBATE_MIN_AGREE:
            verdict = "agree"
            confidence = 0.5 + 0.5 * agreement
        elif missing:
            verdict = "evidence_gap"
            confidence = 0.45
        else:
            verdict = "disagree"
            confidence = 0.4
        return {"validator": self.name, "verdict": verdict, "agreement": round(agreement, 2),
                "checks": checks, "confidence": round(confidence, 2)}


def debate_node(state: dict) -> dict:
    """Agent-to-agent validation round (proposer = specialist node output).

    Coordinator rules (Phase 7 §5.2):
    - one critique round per graph run (multi-round budget applies when the
      full Placement/Analytics pair lands with Phase 7 agents);
    - fusion: fused = min(0.9, 0.5*proposer + 0.5*validator);
    - stalemate (delta > 0.15 or evidence gap) -> escalate: human review gate.
    """
    proposer_conf = float(state.get("confidence") or 0.5)
    claim = state.get("data", {}).get("top_risk") or state.get("data", {})

    validator = RiskSanityValidator()
    validation = validator.validate(claim)

    fused = fuse_confidences([(proposer_conf, 0.5), (validation["confidence"], 0.5)])
    delta = abs(proposer_conf - validation["confidence"])

    escalated = validation["verdict"] in ("disagree", "evidence_gap") or delta > DEBATE_AGREE_DELTA
    debate = {
        "rounds": 1,
        "proposer": state.get("agent", "specialist"),
        "proposer_confidence": proposer_conf,
        "validator": validation["validator"],
        "validator_verdict": validation["verdict"],
        "validator_confidence": validation["confidence"],
        "agreement_delta": round(delta, 3),
        "fused_confidence": round(fused, 3),
        "escalated": escalated,
        "checks": validation["checks"],
    }
    state["debate"] = debate
    state["confidence"] = fused

    if escalated:
        state["requires_approval"] = True
        state["answer"] += (
            f"\n[debate] {validation['validator']} could not fully corroborate "
            f"this flag (verdict: {validation['verdict']}, agreement {validation['agreement']}). "
            "Escalated for human review."
        )

    state.setdefault("audit_events", []).append(
        {
            "action": "debate_validation",
            "entity_type": "prediction",
            "payload": {"verdict": validation["verdict"], "fused_confidence": round(fused, 3),
                        "escalated": escalated},
        }
    )
    return state
