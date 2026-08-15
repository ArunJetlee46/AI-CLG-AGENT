from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import AttendanceRecord, Enrollment, Result, Student


def build_feature_rows(db: Session) -> list[dict]:
    """Feature engineering from PostgreSQL. Returns one row per enrollment."""
    rows: list[dict] = []
    enrollments = db.execute(
        select(Enrollment, Student)
        .join(Student, Enrollment.student_id == Student.id)
        .where(Enrollment.status == "approved")
    ).all()
    for enrollment, student in enrollments:
        present = db.execute(
            select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.enrollment_id == enrollment.id, AttendanceRecord.status == "present"
            )
        ).scalar_one()
        total = db.execute(
            select(func.count(AttendanceRecord.id)).where(AttendanceRecord.enrollment_id == enrollment.id)
        ).scalar_one()
        attendance_rate = present / total if total else 0.5
        result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        rows.append(
            {
                "student_id": student.id,
                "course_id": enrollment.course_id,
                "year": student.year,
                "gpa": student.gpa or 0.0,
                "attendance_rate": attendance_rate,
                "prior_grade": _grade_to_score(result.grade) if result else 0.5,
            }
        )
    return rows


def _grade_to_score(grade: str) -> float:
    mapping = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.25, "F": 0.1}
    return mapping.get(grade.upper(), 0.5)
