"""Placement Copilot services.

Deterministic, explainable placement analytics built on the existing ML
placement prediction task and the shared student aggregates:

  overview   -> batch stats, predicted placement rate, department breakdown
  readiness  -> 0-100 readiness score + band + components + placement prob
  at-risk    -> students likely to remain unplaced, with human-readable reasons
  shortlist  -> score a cohort against a job spec (gpa gate, backlogs, skills)
  report     -> one-click batch report

Skill / project / interview data is not ingested yet, so readiness uses academic
signals (gpa, attendance, marks, pass rate) plus the ML placement probability.
Component weights and band cutoffs are documented heuristic-v1 constants.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.ml.datasets import _student_base
from app.ml.predict import predict_task
from app.models.entities import Enrollment, Result

settings = get_settings()

READY_BAND = 0.70    # readiness >= 70 -> ready
NEEDS_BAND = 0.50    # readiness >= 50 -> needs improvement; else not ready
AT_RISK_CUTOFF = 0.4  # placement_probability < 0.4 -> high unplaced risk

# Readiness component weights (heuristic-v1).
WEIGHTS = {"academic": 0.40, "attendance": 0.20, "aptitude": 0.20, "consistency": 0.20}


def _academic_map(db: Session) -> dict[str, dict]:
    """student_uuid -> {graded, passed, backlogs, pass_rate}."""
    rows = db.execute(
        select(Enrollment.student_id, Result.grade)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.status == "approved")
    ).all()
    counts: dict[str, list[int]] = defaultdict(list)
    for student_uuid, grade in rows:
        if not grade:
            continue
        counts[student_uuid].append(1 if grade == "F" else 0)
    out: dict[str, dict] = {}
    for student_uuid, flags in counts.items():
        graded = len(flags)
        backlogs = sum(flags)
        out[student_uuid] = {
            "graded": graded,
            "backlogs": backlogs,
            "pass_rate": (graded - backlogs) / graded if graded else 0.5,
        }
    return out


def _readiness(student: dict, academic: dict) -> dict:
    consistency = academic.get("pass_rate", 0.5)
    components = {
        "academic": round(min(1.0, student["gpa"] / 4.0), 4),
        "attendance": round(student["attendance_rate"], 4),
        "aptitude": round(min(1.0, student["avg_marks"] / 100.0), 4),
        "consistency": round(consistency, 4),
    }
    score = int(round(100.0 * sum(components[k] * WEIGHTS[k] for k in WEIGHTS)))
    band = "ready" if score >= 100 * READY_BAND else ("needs_improvement" if score >= 100 * NEEDS_BAND else "not_ready")
    return {"score": max(0, min(100, score)), "band": band, "components": components}


def _drivers(student: dict, academic: dict, readiness: dict, proba: float | None) -> list[str]:
    drivers: list[str] = []
    if student["gpa"] >= 3.2:
        drivers.append(f"strong GPA {student['gpa']}")
    elif student["gpa"] < 2.5:
        drivers.append(f"GPA {student['gpa']} below 2.5")
    if student["attendance_rate"] >= 0.85:
        drivers.append(f"attendance {student['attendance_rate']:.0%}")
    elif student["attendance_rate"] < 0.75:
        drivers.append(f"attendance {student['attendance_rate']:.0%} below 75%")
    if student["avg_marks"] >= 70:
        drivers.append(f"marks {student['avg_marks']}")
    elif student["avg_marks"] < 50:
        drivers.append(f"marks {student['avg_marks']} below 50")
    if academic["pass_rate"] >= 0.85:
        drivers.append(f"pass rate {academic['pass_rate']:.0%}")
    elif academic["pass_rate"] < 0.6:
        drivers.append(f"pass rate {academic['pass_rate']:.0%}")
    if proba is not None:
        if proba >= 0.7:
            drivers.append(f"placement model {proba:.0%}")
        elif proba < 0.4:
            drivers.append(f"placement model {proba:.0%} at risk")
    return drivers or ["no strong drivers"]


def _placement_map(db: Session) -> dict[str, dict]:
    rows = predict_task(db, "placement", limit=1000)
    mapping = {r["student_id"]: r for r in rows}
    base_ids = {b["student_id"] for b in _student_base(db)}
    if len(mapping) < len(base_ids):
        return {}
    return mapping


def _heuristic_proba(student: dict) -> float:
    """Placement heuristic matching app.ml.predict (0.6*gpa + 0.4*attendance)."""
    return round(min(1.0, max(0.0, 0.6 * (student["gpa"] / 4.0) + 0.4 * student["attendance_rate"])), 4)


def _scored(db: Session, *, limit: int | None = None, student_id: str | None = None) -> list[dict]:
    academics = _academic_map(db)
    placement = _placement_map(db)
    out: list[dict] = []
    for student in _student_base(db):
        if student_id and student["student_id"] != student_id:
            continue
        academic = academics.get(student["student_uuid"], {"graded": 0, "backlogs": 0, "pass_rate": 0.5})
        readiness = _readiness(student, academic)
        proba = placement.get(student["student_id"], {}).get("placement_probability")
        if proba is None:
            proba = _heuristic_proba(student)
        out.append(
            {
                "student_id": student["student_id"],
                "student_uuid": student["student_uuid"],
                "program": student["program"],
                "year": student["year"],
                "gpa": round(student["gpa"], 2),
                "attendance_rate": student["attendance_rate"],
                "avg_marks": round(student["avg_marks"], 1),
                "backlogs": academic["backlogs"],
                "readiness_score": readiness["score"],
                "band": readiness["band"],
                "components": readiness["components"],
                "placement_probability": round(proba, 4),
                "unplaced_risk": round(1.0 - proba, 4),
                "drivers": _drivers(student, academic, readiness, proba),
            }
        )
    out.sort(key=lambda r: r["readiness_score"], reverse=True)
    return out[:limit] if limit else out


def get_readiness(db: Session, *, limit: int = 100, student_id: str | None = None) -> list[dict]:
    return _scored(db, limit=limit if not student_id else None, student_id=student_id)


def get_overview(db: Session) -> dict:
    scored = _scored(db)
    probas = [r["placement_probability"] for r in scored if r["placement_probability"] is not None]
    bands: dict[str, int] = defaultdict(int)
    for r in scored:
        bands[r["band"]] += 1
    by_program: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        by_program[r["program"]].append(r)
    departments = [
        {
            "program": program,
            "students": len(rows),
            "ready": sum(1 for r in rows if r["band"] == "ready"),
            "avg_readiness": round(sum(r["readiness_score"] for r in rows) / len(rows), 1),
            "avg_gpa": round(sum(r["gpa"] for r in rows) / len(rows), 2),
        }
        for program, rows in sorted(by_program.items())
    ]
    return {
        "total_students": len(scored),
        "predicted_placement_rate": round(sum(probas) / len(probas), 4) if probas else None,
        "avg_readiness": round(sum(r["readiness_score"] for r in scored) / len(scored), 1) if scored else None,
        "distribution": {
            "ready": bands["ready"],
            "needs_improvement": bands["needs_improvement"],
            "not_ready": bands["not_ready"],
        },
        "funnel": {
            "ready": bands["ready"],
            "needs_improvement": bands["needs_improvement"],
            "not_ready": bands["not_ready"],
            "at_risk": sum(1 for r in scored if (r["placement_probability"] or 0) < AT_RISK_CUTOFF),
        },
        "departments": departments,
    }


def get_at_risk(db: Session, *, limit: int = 50) -> list[dict]:
    scored = [r for r in _scored(db) if (r["placement_probability"] or 0) < 0.6]
    scored.sort(key=lambda r: r["placement_probability"] or 1.0)
    out: list[dict] = []
    for r in scored[:limit]:
        risk = "high" if (r["placement_probability"] or 0) < AT_RISK_CUTOFF else "medium"
        out.append(
            {
                "student_id": r["student_id"],
                "program": r["program"],
                "gpa": r["gpa"],
                "attendance_rate": r["attendance_rate"],
                "backlogs": r["backlogs"],
                "readiness_score": r["readiness_score"],
                "placement_probability": r["placement_probability"],
                "risk_level": risk,
                "reasons": [d for d in r["drivers"] if "at risk" in d or "below" in d or "risk" in d]
                or r["drivers"][:2],
            }
        )
    return out


def shortlist(db: Session, *, role: str, min_gpa: float = 0.0, max_backlogs: int = 0,
              required_skills: list[str] | None = None, limit: int = 50) -> dict:
    required_skills = [s.strip().lower() for s in (required_skills or []) if s.strip()]
    scored = _scored(db)
    candidates: list[dict] = []
    eligible_count = 0
    for r in scored:
        if r["gpa"] < min_gpa:
            continue
        if r["backlogs"] > max_backlogs:
            continue
        eligible_count += 1
        matched = [s for s in required_skills if s in f"{r['program']} {r['drivers']}".lower()]
        gpa_fit = min(1.0, r["gpa"] / 4.0)
        backlog_fit = 1.0 / (1.0 + r["backlogs"])
        match_score = round(100.0 * (0.5 * gpa_fit + 0.3 * r["readiness_score"] / 100.0 + 0.2 * backlog_fit), 1)
        candidates.append(
            {
                "student_id": r["student_id"],
                "program": r["program"],
                "gpa": r["gpa"],
                "backlogs": r["backlogs"],
                "readiness_score": r["readiness_score"],
                "match_score": match_score,
                "skills_matched": matched,
                "gates": {"gpa_ok": r["gpa"] >= min_gpa, "backlogs_ok": r["backlogs"] <= max_backlogs},
            }
        )
    candidates.sort(key=lambda c: c["match_score"], reverse=True)
    return {
        "role": role,
        "min_gpa": min_gpa,
        "max_backlogs": max_backlogs,
        "required_skills": required_skills,
        "eligible_count": eligible_count,
        "candidates": candidates[:limit],
    }


def get_report(db: Session) -> dict:
    overview = get_overview(db)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "heuristic-v1",
        "total_students": overview["total_students"],
        "predicted_placement_rate": overview["predicted_placement_rate"],
        "avg_readiness": overview["avg_readiness"],
        "distribution": overview["distribution"],
        "departments": overview["departments"],
        "note": (
            "Readiness is computed from academic signals (gpa, attendance, marks, pass rate) "
            "plus the ML placement probability. Skill/interview/project data is roadmap."
        ),
    }
