"""Tests for the Placement Copilot services."""
from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    Course,
    Enrollment,
    Result,
    Student,
    User,
)
from app.services import placement


def _make_student(student_id: str, *, gpa: float = 3.0) -> Student:
    db = SessionLocal()
    try:
        user = User(username=student_id, password_hash=hash_password("student123"), role="student",
                    email=f"{student_id.lower()}@beru.edu")
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=3, program="Computer Science", gpa=gpa)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _course(db, code: str) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=[])
        db.add(course)
        db.flush()
    return course


def _enroll(db, student: Student, code: str, *, grade: str = "A", marks: float = 75.0,
            attendance: float = 0.9) -> None:
    from datetime import date

    course = _course(db, code)
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    db.add(Result(enrollment_id=enrollment.id, marks=marks, grade=grade, semester="2026-S1"))
    for i in range(20):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 2, 2 + i),
                                status="present" if i < round(20 * attendance) else "absent"))
    db.commit()


def test_overview_aggregates_and_departments():
    strong = _make_student("PLSTU01", gpa=3.7)
    weak = _make_student("PLSTU02", gpa=1.2)
    db = SessionLocal()
    try:
        _enroll(db, strong, "PLC101", grade="A", marks=92.0, attendance=0.98)
        _enroll(db, weak, "PLC102", grade="F", marks=20.0, attendance=0.3)
        overview = placement.get_overview(db)
        assert overview["total_students"] >= 2
        assert 0.0 <= overview["predicted_placement_rate"] <= 1.0
        assert overview["avg_readiness"] is not None
        assert overview["distribution"]["ready"] >= 1
        assert overview["distribution"]["not_ready"] >= 1
        assert any(d["program"] == "Computer Science" for d in overview["departments"])
    finally:
        db.close()


def test_readiness_bands_and_components():
    strong = _make_student("PLSTU03", gpa=3.8)
    weak = _make_student("PLSTU04", gpa=1.0)
    db = SessionLocal()
    try:
        _enroll(db, strong, "PLC103", grade="A", marks=95.0, attendance=0.99)
        _enroll(db, weak, "PLC104", grade="F", marks=15.0, attendance=0.2)
        rows = placement.get_readiness(db, limit=100)
        by_id = {r["student_id"]: r for r in rows}
        assert by_id["PLSTU03"]["band"] == "ready"
        assert by_id["PLSTU03"]["readiness_score"] >= 70
        assert by_id["PLSTU04"]["band"] == "not_ready"
        assert by_id["PLSTU04"]["readiness_score"] < 50
        comps = by_id["PLSTU03"]["components"]
        total = 0.4 * comps["academic"] + 0.2 * comps["attendance"] + 0.2 * comps["aptitude"] + 0.2 * comps["consistency"]
        assert 0 <= by_id["PLSTU03"]["readiness_score"] / 100 - total <= 0.02
        assert sorted((r["readiness_score"] for r in rows), reverse=True) == [r["readiness_score"] for r in rows]
    finally:
        db.close()


def test_at_risk_flags_weak_student_with_reasons():
    strong = _make_student("PLSTU05", gpa=3.6)
    weak = _make_student("PLSTU06", gpa=1.1)
    db = SessionLocal()
    try:
        _enroll(db, strong, "PLC105", grade="A", attendance=0.95)
        _enroll(db, weak, "PLC106", grade="F", marks=10.0, attendance=0.25)
        monitor = placement.get_at_risk(db, limit=100)
        entry = next(r for r in monitor if r["student_id"] == "PLSTU06")
        assert entry["risk_level"] == "high"
        assert entry["placement_probability"] < 0.4
        assert any("GPA" in r for r in entry["reasons"])
        assert any("attendance" in r for r in entry["reasons"])
    finally:
        db.close()


def test_shortlist_gates_and_ranking():
    strong = _make_student("PLSTU07", gpa=3.8)
    weak = _make_student("PLSTU08", gpa=1.4)
    db = SessionLocal()
    try:
        _enroll(db, strong, "PLC107", grade="A", attendance=0.97)
        _enroll(db, weak, "PLC108", grade="F", marks=18.0, attendance=0.3)
        result = placement.shortlist(
            db, role="Data Scientist", min_gpa=3.0, max_backlogs=0,
            required_skills=["python"], limit=50,
        )
        assert result["role"] == "Data Scientist"
        ids = [c["student_id"] for c in result["candidates"]]
        assert "PLSTU07" in ids
        assert "PLSTU08" not in ids
        scores = [c["match_score"] for c in result["candidates"]]
        assert scores == sorted(scores, reverse=True)
        top = result["candidates"][0]
        assert top["gates"]["gpa_ok"] is True
        assert top["backlogs"] == 0
    finally:
        db.close()


def test_report_snapshot_fields():
    _make_student("PLSTU09", gpa=3.2)
    db = SessionLocal()
    try:
        report = placement.get_report(db)
        assert report["total_students"] >= 1
        assert report["method"] == "heuristic-v1"
        assert report["generated_at"]
        assert "ready" in report["distribution"]
        assert isinstance(report["departments"], list)
    finally:
        db.close()
