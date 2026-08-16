"""Tests for the Student Copilot endpoints and services.

Uses the real (temp) DB seeded by conftest; the demo student account falls back
to settings.demo_student_id. A dedicated student with known data is created per
test where a specific profile is required.
"""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Result, Student, User
from app.services import students


def _make_student(student_id: str, *, gpa: float = 3.0, year: int = 2) -> Student:
    db = SessionLocal()
    try:
        user = User(
            username=student_id,
            password_hash=hash_password("student123"),
            role="student",
            email=f"{student_id.lower()}@beru.edu",
        )
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=year, program="Computer Science", gpa=gpa)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _enroll(db, student: Student, code: str, *, grade: str = "", marks: float | None = None,
            attendance: float = 0.9) -> Enrollment:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=[])
        db.add(course)
        db.flush()
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    if grade:
        db.add(
            Result(
                enrollment_id=enrollment.id,
                marks=marks if marks is not None else (60.0 if grade != "F" else 20.0),
                grade=grade,
                semester="2026-S1",
            )
        )
    for i in range(10):
        db.add(
            AttendanceRecord(
                enrollment_id=enrollment.id,
                day=date(2026, 3, 2 + i),
                status="present" if i < round(10 * attendance) else "absent",
            )
        )
    db.commit()
    return enrollment


def test_resolve_student_uses_linked_student():
    stu = _make_student("STUDTEST1", gpa=3.4)
    db = SessionLocal()
    try:
        user = db.get(User, stu.user_id)
        assert students.resolve_student(db, user).student_id == "STUDTEST1"
    finally:
        db.close()


def test_profile_aggregates_courses():
    stu = _make_student("STUDTEST2", gpa=3.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS101", grade="A", marks=85.0, attendance=0.9)
        _enroll(db, stu, "CS102", grade="F", marks=25.0, attendance=0.6)
        profile = students.get_profile(db, stu)
        assert profile["student_id"] == "STUDTEST2"
        assert profile["course_load"] == 2
        assert profile["credits_earned"] == 3  # only CS101 (grade A)
        codes = {c["course_code"] for c in profile["courses"]}
        assert codes == {"CS101", "CS102"}
        assert 0.6 < profile["overall_attendance"] <= 0.9
    finally:
        db.close()


def test_success_score_band_and_drivers():
    strong = _make_student("STUDTEST3", gpa=3.8)
    weak = _make_student("STUDTEST4", gpa=1.8)
    db = SessionLocal()
    try:
        _enroll(db, strong, "CS201", grade="A", marks=90.0, attendance=0.95)
        _enroll(db, weak, "CS202", grade="F", marks=20.0, attendance=0.4)
        strong_score = students.get_success_score(db, strong)
        weak_score = students.get_success_score(db, weak)
        assert strong_score["success_score"] > 70
        assert strong_score["risk_level"] == "low"
        assert weak_score["success_score"] < 50
        assert weak_score["risk_level"] == "high"
        assert strong_score["components"][0]["name"] == "attendance"
        assert any("attendance" in d for d in strong_score["drivers"])
    finally:
        db.close()


def test_alerts_flag_attendance_and_failures():
    stu = _make_student("STUDTEST5", gpa=2.5)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS301", grade="F", marks=15.0, attendance=0.5)
        alerts = students.get_alerts(db, stu)
        kinds = {a["kind"] for a in alerts}
        assert "attendance" in kinds
        assert "grade" in kinds
        assert alerts[0]["severity"] == "high"
    finally:
        db.close()


def test_predictions_are_deterministic():
    stu = _make_student("STUDTEST6", gpa=2.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS401", attendance=1.0)
        _enroll(db, stu, "CS402", attendance=0.2)
        result = students.get_predictions(db, stu)
        assert result["method"] == "heuristic-v1"
        by_code = {p["course_code"]: p for p in result["predictions"]}
        assert by_code["CS401"]["pass_probability"] > by_code["CS402"]["pass_probability"]
        assert by_code["CS402"]["risk_level"] in ("high", "medium")
        assert 0.0 <= result["projected_gpa"] <= 4.0
    finally:
        db.close()


def test_advise_missing_prereq_is_ineligible():
    stu = _make_student("STUDTEST7", gpa=3.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "MATH101", grade="A")
        course = db.execute(select(Course).where(Course.code == "ADV501")).scalar_one_or_none()
        if course is None:
            db.add(Course(code="ADV501", title="Advanced", credits=3, department="Computer Science",
                          prerequisites=["MATH201"]))
            db.commit()
        advice = students.advise(db, stu, "ADV501")
        assert advice["exists"] is True
        assert advice["eligible"] is False
        assert "MATH201" in advice["unmet_prerequisites"]
    finally:
        db.close()


def test_advise_unknown_course():
    stu = _make_student("STUDTEST8", gpa=3.0)
    db = SessionLocal()
    try:
        advice = students.advise(db, stu, "ZZZ999")
        assert advice["exists"] is False
        assert advice["eligible"] is False
    finally:
        db.close()


def test_today_plan_prioritizes_high_severity():
    stu = _make_student("STUDTEST9", gpa=2.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS501", grade="F", marks=10.0, attendance=0.4)
        today = students.get_today(db, stu)
        assert today["success_score"] is not None
        assert today["plan"]
        assert today["plan"][0]["severity"] == "high"
        assert any(item["kind"] == "grade" for item in today["plan"])
    finally:
        db.close()
