"""Intervention Effectiveness Tracking Service.

Tracks the effectiveness of interventions over time by comparing
baseline metrics with follow-up measurements.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.entities import (
    InterventionPlan,
    InterventionEffectiveness,
    Student,
    Enrollment,
    Course,
    Result,
    AttendanceRecord,
)


def calculate_success_score(db: Session, student_id: str, course_code: str | None = None) -> float:
    """Calculate a composite success score for a student (0-100)."""
    student = db.execute(select(Student).where(Student.id == student_id)).scalar_one_or_none()
    if not student:
        return 0.0

    enrollments_query = select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.status == "approved")
    if course_code:
        course = db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()
        if course:
            enrollments_query = enrollments_query.where(Enrollment.course_id == course.id)
    enrollments = db.execute(enrollments_query).scalars().all()

    if not enrollments:
        return 50.0

    total_score = 0.0
    count = 0

    for enrollment in enrollments:
        course = enrollment.course
        result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        attendance_records = db.execute(
            select(AttendanceRecord).where(AttendanceRecord.enrollment_id == enrollment.id)
        ).scalars().all()

        attendance_rate = (
            sum(1 for r in attendance_records if r.status == "present") / len(attendance_records)
            if attendance_records
            else 0.5
        )

        grade_score = 0.5
        if result and result.grade:
            grade_map = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "F": 0.0}
            grade_score = grade_map.get(result.grade, 0.5)

        course_score = 0.4 * attendance_rate + 0.6 * grade_score
        total_score += course_score
        count += 1

    avg_score = (total_score / count) * 100 if count > 0 else 50.0
    return max(0.0, min(100.0, avg_score))


def create_intervention_effectiveness(
    db: Session,
    intervention_id: str,
    student_id: str,
    course_code: str,
    intervention_type: str,
) -> InterventionEffectiveness:
    """Create an effectiveness tracking record for an intervention."""
    baseline = calculate_success_score(db, student_id, course_code)

    effectiveness = InterventionEffectiveness(
        intervention_id=intervention_id,
        student_id=student_id,
        course_code=course_code,
        intervention_type=intervention_type,
        baseline_score=baseline,
        status="active",
        started_at=datetime.utcnow(),
    )
    db.add(effectiveness)
    db.commit()
    db.refresh(effectiveness)
    return effectiveness


def update_intervention_effectiveness(
    db: Session,
    intervention_id: str,
    followup_score: float,
    notes: str = "",
) -> Optional[InterventionEffectiveness]:
    """Update an effectiveness record with follow-up measurement."""
    effectiveness = db.execute(
        select(InterventionEffectiveness).where(InterventionEffectiveness.intervention_id == intervention_id)
    ).scalar_one_or_none()

    if not effectiveness:
        return None

    effectiveness.followup_score = followup_score
    effectiveness.improvement = followup_score - effectiveness.baseline_score
    effectiveness.notes = notes
    effectiveness.completed_at = datetime.utcnow()
    effectiveness.status = "completed" if followup_score >= effectiveness.baseline_score else "needs_review"

    db.commit()
    db.refresh(effectiveness)
    return effectiveness


def get_intervention_effectiveness(
    db: Session,
    intervention_id: str,
) -> Optional[InterventionEffectiveness]:
    """Get effectiveness record for an intervention."""
    return db.execute(
        select(InterventionEffectiveness).where(InterventionEffectiveness.intervention_id == intervention_id)
    ).scalar_one_or_none()


def list_intervention_effectiveness(
    db: Session,
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[InterventionEffectiveness]:
    """List intervention effectiveness records with filters."""
    query = select(InterventionEffectiveness)

    if student_id:
        query = query.where(InterventionEffectiveness.student_id == student_id)
    if course_code:
        query = query.where(InterventionEffectiveness.course_code == course_code)
    if status:
        query = query.where(InterventionEffectiveness.status == status)

    query = query.order_by(InterventionEffectiveness.started_at.desc()).limit(limit)
    return db.execute(query).scalars().all()


def get_effectiveness_summary(db: Session) -> dict:
    """Get overall effectiveness statistics."""
    all_records = db.execute(select(InterventionEffectiveness)).scalars().all()

    total = len(all_records)
    completed = [r for r in all_records if r.status == "completed"]
    active = [r for r in all_records if r.status == "active"]
    needs_review = [r for r in all_records if r.status == "needs_review"]

    improvements = [r.improvement for r in completed if r.improvement is not None]
    avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0

    positive = sum(1 for i in improvements if i > 0)
    negative = sum(1 for i in improvements if i < 0)
    neutral = sum(1 for i in improvements if i == 0)

    by_type = {}
    for record in all_records:
        if record.intervention_type not in by_type:
            by_type[record.intervention_type] = {"total": 0, "completed": 0, "avg_improvement": 0.0}
        by_type[record.intervention_type]["total"] += 1
        if record.status == "completed" and record.improvement is not None:
            by_type[record.intervention_type]["completed"] += 1

    for itype, stats in by_type.items():
        type_improvements = [
            r.improvement for r in all_records
            if r.intervention_type == itype and r.improvement is not None
        ]
        stats["avg_improvement"] = sum(type_improvements) / len(type_improvements) if type_improvements else 0.0

    return {
        "total_interventions": total,
        "completed": len(completed),
        "active": len(active),
        "needs_review": len(needs_review),
        "avg_improvement": round(avg_improvement, 2),
        "positive_outcomes": positive,
        "negative_outcomes": negative,
        "neutral_outcomes": neutral,
        "success_rate": round(positive / len(completed) * 100, 1) if completed else 0.0,
        "by_type": by_type,
    }