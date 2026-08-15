"""Mutating operations, all gated by an approved approval.

These are the ONLY write paths for domain data. Each function takes an
`approval_id`, verifies it inside the method (`require_approved`), performs the
write, and records an audit event carrying the `approval_id` that authorized
the row - so the chain can answer "which approval authorized this write".
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.approvals import require_approved
from app.core.audit import record_event
from app.core.safety import execution_allowed
from app.models.entities import Course, Enrollment, InterventionPlan, Student

logger = logging.getLogger(__name__)


def _check_execution() -> None:
    """Emergency kill switch: block every mutating write when execution is paused."""
    if not execution_allowed():
        raise ValueError("AI execution is paused by the safety control. Re-enable execution to continue.")


def apply_registration(db: Session, *, approval_id: str, actor: str) -> dict:
    """Create enrollments authorized by an approved registration request."""
    _check_execution()
    approval = require_approved(db, approval_id)
    student = db.execute(select(Student).where(Student.user_id == approval.user_id)).scalar_one_or_none()
    if student is None:
        raise ValueError("no student profile for requester")

    created = 0
    codes = approval.payload.get("course_codes", [])
    for code in codes:
        course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
        if course is None:
            continue
        exists = db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student.id, Enrollment.course_id == course.id
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            Enrollment(
                student_id=student.id,
                course_id=course.id,
                status="approved",
                approved_by=actor,
                approval_id=approval.id,
            )
        )
        created += 1
    db.commit()
    record_event(
        db,
        actor=actor,
        action="enrollment_created",
        entity_type="enrollment",
        entity_id=approval.id,
        approval_id=approval.id,
        payload={"course_codes": codes, "created": created, "student_id": student.id},
    )
    return {"ok": True, "message": f"Approved: {created} enrollment(s) created.", "created": created}


def apply_timetable(db: Session, *, approval_id: str, actor: str) -> dict:
    """Persist an OR-Tools timetable authorized by an approved change request."""
    _check_execution()
    approval = require_approved(db, approval_id)
    from app.ml.optimize import solve_timetable

    term = approval.payload.get("term") or "2026-S1"
    report = solve_timetable(db, approval_id=approval_id, term=term)
    record_event(
        db,
        actor=actor,
        action="timetable_applied",
        entity_type="timetable",
        entity_id=approval.id,
        approval_id=approval.id,
        payload={
            "term": term,
            "scheduled": report.get("scheduled", 0),
            "conflicts": report.get("conflicts", 0),
            "algorithm": report.get("algorithm"),
            "status": report.get("status"),
        },
    )
    return {
        "ok": True,
        "message": f"Timetable applied for {term}: {report.get('scheduled', 0)} sessions, "
        f"{report.get('conflicts', 0)} conflicts.",
        "report": report,
    }


def apply_intervention(db: Session, *, approval_id: str, actor: str) -> dict:
    """Persist an intervention plan authorized by an approved risk flag."""
    _check_execution()
    approval = require_approved(db, approval_id)
    payload = approval.payload
    plan = InterventionPlan(
        student_id=payload.get("student_id"),
        course_code=payload.get("course_code", ""),
        plan_text=payload.get("plan_text", ""),
        status="active",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    record_event(
        db,
        actor=actor,
        action="intervention_created",
        entity_type="intervention",
        entity_id=plan.id,
        approval_id=approval.id,
        payload={
            "student_id": plan.student_id,
            "course_code": plan.course_code,
            "plan": plan.plan_text[:200],
        },
    )
    return {"ok": True, "message": f"Intervention applied for {plan.student_id}.", "intervention_id": plan.id}
