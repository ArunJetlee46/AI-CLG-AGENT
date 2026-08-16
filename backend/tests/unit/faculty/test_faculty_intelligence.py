"""Tests for the Faculty Copilot intelligence batch (learning outcomes, remedial
plans, high performers, research recommendations, schedule, reports, digital
twin, similarity, intervention recommendations).
"""
from datetime import date, time

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    Course,
    Enrollment,
    Lecturer,
    Result,
    Student,
    TimetableEntry,
    User,
)
from app.services import faculty_intelligence


def _make_lecturer(staff_id: str = "LECTINTEL") -> Lecturer:
    db = SessionLocal()
    try:
        user = User(username=staff_id, password_hash=hash_password("lecturer123"), role="lecturer",
                    email=f"{staff_id.lower()}@beru.edu")
        db.add(user)
        db.flush()
        lecturer = Lecturer(user_id=user.id, staff_id=staff_id, department="Computer Science", max_hours=20)
        db.add(lecturer)
        db.commit()
        db.refresh(lecturer)
        return lecturer
    finally:
        db.close()


def _link_course(db, lecturer: Lecturer, code: str) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=[])
        db.add(course)
        db.flush()
    entry = db.execute(select(TimetableEntry).where(TimetableEntry.lecturer_id == lecturer.id,
                                                    TimetableEntry.course_id == course.id)).scalar_one_or_none()
    if entry is None:
        db.add(TimetableEntry(course_id=course.id, room_id="", lecturer_id=lecturer.id, day="MON",
                              start_time=time(9, 0), end_time=time(11, 0), term="2026-S1"))
    db.commit()
    return course


def _make_student(student_id: str, *, gpa: float = 3.0) -> Student:
    db = SessionLocal()
    try:
        user = User(username=student_id, password_hash=hash_password("student123"), role="student",
                    email=f"{student_id.lower()}@beru.edu")
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=2, program="Computer Science", gpa=gpa)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _enroll(db, student: Student, course: Course, *, grade: str = "", marks: float | None = None,
            attendance: float = 0.9) -> Enrollment:
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    if grade:
        db.add(Result(enrollment_id=enrollment.id,
                      marks=marks if marks is not None else (60.0 if grade != "F" else 20.0),
                      grade=grade, semester="2026-S1"))
    for i in range(20):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 2, 2 + i),
                                status="present" if i < round(20 * attendance) else "absent"))
    db.commit()
    return enrollment


def test_learning_outcomes_per_course():
    lecturer = _make_lecturer("LINTEL01")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT101")
        _enroll(db, _make_student("FINT01"), course, grade="A", marks=90.0, attendance=0.95)
        result = faculty_intelligence.get_learning_outcomes(db, lecturer)
        assert result["courses"]
        entry = result["courses"][0]
        assert entry["course_code"] == "FINT101"
        assert {o["area"] for o in entry["outcomes"]} == {"core concepts", "application", "engagement"}
        assert entry["weakest_area"]
        assert entry["distribution"]["high"] >= 1
    finally:
        db.close()


def test_remedial_plan_steps_match_weaknesses():
    lecturer = _make_lecturer("LINTEL02")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT102")
        weak = _make_student("FINT02", gpa=1.8)
        _enroll(db, weak, course, grade="F", marks=20.0, attendance=0.4)
        plan = faculty_intelligence.get_remedial_plan(db, lecturer, "FINT102", "FINT02")
        assert plan["exists"]
        assert plan["risk_level"] in ("high", "medium")
        kinds = {s["kind"] for s in plan["steps"]}
        assert "attendance" in kinds
        assert "academic" in kinds
        assert plan["steps"][0]["priority"] == "high"
    finally:
        db.close()


def test_high_performers_rank_strong_first():
    lecturer = _make_lecturer("LINTEL03")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT103")
        strong = _make_student("FINT03", gpa=3.9)
        weak = _make_student("FINT04", gpa=1.5)
        _enroll(db, strong, course, grade="A", marks=95.0, attendance=1.0)
        _enroll(db, weak, course, grade="F", marks=15.0, attendance=0.3)
        high = faculty_intelligence.get_high_performers(db, lecturer)
        assert high and high[0]["student_id"] == "FINT03"
        assert high[0]["band"] == "high"
    finally:
        db.close()


def test_research_recommendations_filter_by_gpa():
    lecturer = _make_lecturer("LINTEL04")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT104")
        _enroll(db, _make_student("FINT05", gpa=3.8), course, grade="A", marks=92.0, attendance=0.95)
        _enroll(db, _make_student("FINT06", gpa=2.0), course, grade="C", marks=55.0, attendance=0.6)
        result = faculty_intelligence.get_research_recommendations(db, lecturer)
        ids = {c["student_id"] for c in result["candidates"]}
        assert "FINT05" in ids
        assert "FINT06" not in ids
        assert all(c["suggested_area"] for c in result["candidates"])
    finally:
        db.close()


def test_schedule_aggregates_hours_and_days():
    lecturer = _make_lecturer("LINTEL05")
    db = SessionLocal()
    try:
        _link_course(db, lecturer, "FINT105")
        schedule = faculty_intelligence.get_schedule(db, lecturer)
        assert schedule["sessions"] >= 1
        assert schedule["total_hours"] >= 2.0
        assert schedule["days"]
        assert schedule["days"][0]["slots"]
        assert schedule["utilization"] >= 0
        assert isinstance(schedule["overloaded"], bool)
    finally:
        db.close()


def test_course_report_has_narrative_and_distribution():
    lecturer = _make_lecturer("LINTEL06")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT106")
        _enroll(db, _make_student("FINT07"), course, grade="A", marks=88.0, attendance=0.9)
        report = faculty_intelligence.get_course_report(db, lecturer, "FINT106")
        assert report["course_code"] == "FINT106"
        assert report["narrative"]
        assert report["generated_on"]
        assert set(report["distribution"]) == {"outstanding", "good", "average", "below"}
        assert report["top_students"]
    finally:
        db.close()


def test_faculty_digital_twin_snapshot():
    lecturer = _make_lecturer("LINTEL07")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT107")
        _enroll(db, _make_student("FINT08", gpa=3.7), course, grade="A", marks=90.0, attendance=0.95)
        twin = faculty_intelligence.get_faculty_digital_twin(db, lecturer)
        assert twin["identity"]["department"] == "Computer Science"
        assert twin["identity"]["courses"] >= 1
        assert twin["trajectory"]["trend"] in ("improving", "stable", "declining")
        assert twin["next_best_actions"]
        assert 0 <= twin["health"]["avg_course_health"] <= 100
    finally:
        db.close()


def test_similarity_flags_identical_texts():
    lecturer = _make_lecturer("LINTEL08")
    db = SessionLocal()
    try:
        result = faculty_intelligence.get_similarity(
            db, lecturer,
            [
                {"student_id": "A", "text": "Machine learning models learn from data."},
                {"student_id": "B", "text": "Machine learning models learn from data."},
                {"student_id": "C", "text": "The history of ancient Rome is fascinating."},
            ],
            threshold=0.35,
        )
        assert result["submissions"] == 3
        assert len(result["pairs"]) == 1
        assert result["pairs"][0]["flag"] == "high"
        assert {result["pairs"][0]["student_a"], result["pairs"][0]["student_b"]} == {"A", "B"}
    finally:
        db.close()


def test_intervention_recommendations_target_at_risk():
    lecturer = _make_lecturer("LINTEL09")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FINT108")
        _enroll(db, _make_student("FINT09", gpa=1.2), course, grade="F", marks=15.0, attendance=0.2)
        recs = faculty_intelligence.get_intervention_recommendations(db, lecturer)
        assert any(r["student_id"] == "FINT09" for r in recs)
        flagged = next(r for r in recs if r["student_id"] == "FINT09")
        assert flagged["risk_level"] == "high"
        assert flagged["recommendation"]
    finally:
        db.close()
