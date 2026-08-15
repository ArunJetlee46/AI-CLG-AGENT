"""Tests for the Student Growth analytical batch (weaknesses, recommendations,
career readiness, study groups, notifications, gamification, digital twin, progress).
"""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Result, Student, User
from app.services import student_growth


def _make_student(student_id: str, *, gpa: float = 3.0, year: int = 2, program: str = "Computer Science") -> Student:
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
        stu = Student(user_id=user.id, student_id=student_id, year=year, program=program, gpa=gpa)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _enroll(db, student: Student, code: str, *, grade: str = "", marks: float | None = None,
            attendance: float = 0.9, department: str = "Computer Science") -> Enrollment:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department=department, prerequisites=[])
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


def test_weaknesses_flags_low_attendance_and_failures():
    stu = _make_student("GROW001", gpa=2.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS701", grade="F", marks=15.0, attendance=0.4)
        result = student_growth.get_weaknesses(db, stu)
        areas = {a["area"] for a in result["areas"]}
        assert "attendance" in areas
        assert "academic" in areas
        assert result["overall_weakness_score"] > 40
        assert all(c["course_code"] for a in result["areas"] for c in a["courses"])
    finally:
        db.close()


def test_recommendations_include_electives_and_retakes():
    stu = _make_student("GROW002", gpa=2.5)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS801", grade="F", marks=20.0, attendance=0.8)
        _enroll(db, stu, "CS802", grade="B", marks=70.0, attendance=0.9)
        result = student_growth.get_recommendations(db, stu)
        assert result["method"] == "heuristic-e1"
        assert any(s["course_code"] == "CS801" for s in result["strengthen"])
        assert result["electives"]  # catalog has many courses
        assert all(e["match_score"] >= 0 for e in result["electives"])
        assert result["next_steps"]
    finally:
        db.close()


def test_career_readiness_band_and_components():
    strong = _make_student("GROW003", gpa=3.8)
    weak = _make_student("GROW004", gpa=1.8)
    db = SessionLocal()
    try:
        _enroll(db, strong, "CS901", grade="A", marks=90.0, attendance=0.95)
        _enroll(db, weak, "CS902", grade="F", marks=15.0, attendance=0.4)
        s = student_growth.get_career_readiness(db, strong)
        w = student_growth.get_career_readiness(db, weak)
        assert s["career_readiness_score"] > 70
        assert s["band"] == "career_ready"
        assert w["career_readiness_score"] < 50
        assert w["band"] == "at_risk"
        assert [c["name"] for c in s["components"]] == ["academic", "discipline", "consistency", "engagement"]
    finally:
        db.close()


def test_study_groups_rank_complementary_peers():
    me = _make_student("GROW005", gpa=3.0)
    peer = _make_student("GROW006", gpa=3.2)
    db = SessionLocal()
    try:
        _enroll(db, me, "CS1001", attendance=0.5)
        _enroll(db, peer, "CS1001", attendance=0.95, grade="A", marks=85.0)
        result = student_growth.get_study_groups(db, me)
        assert result["groups"]
        top = result["groups"][0]
        assert top["peer_student_id"] == "GROW006"
        assert top["complementarity_score"] >= 1.0
        assert any("CS1001" in s for s in top["synergy"])
    finally:
        db.close()


def test_gamification_level_xp_and_badges():
    stu = _make_student("GROW007", gpa=3.9)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS1101", grade="A", marks=95.0, attendance=1.0)
        _enroll(db, stu, "CS1102", grade="A", marks=90.0, attendance=0.95)
        result = student_growth.get_gamification(db, stu)
        assert result["level"] >= 1
        assert result["xp"] > 0
        earned = {b["id"] for b in result["badges"] if b["earned"]}
        assert "first-steps" in earned
        assert "perfect-attendance" in earned
        assert "high-achiever" in earned
    finally:
        db.close()


def test_notifications_sort_high_severity_first():
    stu = _make_student("GROW008", gpa=1.9)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS1201", grade="F", marks=10.0, attendance=0.3)
        result = student_growth.get_notifications(db, stu)
        assert result["notifications"]
        assert result["notifications"][0]["severity"] == "high"
        kinds = {n["type"] for n in result["notifications"]}
        assert "alert" in kinds
    finally:
        db.close()


def test_digital_twin_is_a_coherent_snapshot():
    stu = _make_student("GROW009", gpa=3.6)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS1301", grade="A", marks=88.0, attendance=0.9)
        twin = student_growth.get_digital_twin(db, stu)
        assert twin["identity"]["program"] == "Computer Science"
        assert twin["health"]["success_score"] >= 0
        assert twin["trajectory"]["trend"] in ("improving", "stable", "declining")
        assert twin["next_best_actions"]
    finally:
        db.close()


def test_progress_series_and_course_trends():
    stu = _make_student("GROW010", gpa=3.0)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS1401", attendance=0.8)
        result = student_growth.get_progress(db, stu)
        assert len(result["success_trend"]) == 12
        assert len(result["attendance_trend"]) == 12
        assert len(result["gpa_trend"]) == 12
        assert result["success_trend"][-1]["value"] > 0
        assert all(t["trend"] in ("improving", "stable", "declining") for t in result["course_trends"])
    finally:
        db.close()
