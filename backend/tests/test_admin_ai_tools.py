"""Tests for the admin LLM batch: AI Admin Copilot, University Digital Twin,
AI Timetable Optimization, and the AI Evaluation Center.

All run with an unreachable Ollama so they exercise the deterministic fallbacks.
"""
from datetime import date, time

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    AuditLog,
    Course,
    Enrollment,
    Lecturer,
    Result,
    Room,
    Student,
    TimetableEntry,
    User,
)
from app.services import admin_ai_tools


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


def _make_lecturer(staff_id: str) -> Lecturer:
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


def _course(db, code: str) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=[])
        db.add(course)
        db.flush()
    return course


def _enroll(db, student: Student, code: str, *, grade: str = "A", marks: float = 75.0,
            attendance: float = 0.9) -> None:
    course = _course(db, code)
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    db.add(Result(enrollment_id=enrollment.id, marks=marks, grade=grade, semester="2026-S1"))
    for i in range(20):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 2, 2 + i),
                                status="present" if i < round(20 * attendance) else "absent"))
    db.commit()


def _room(db, room_no: str, *, capacity: int = 60) -> Room:
    room = Room(room_no=room_no, capacity=capacity, kind="classroom")
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


# ---------------------------------------------------------------------------
# AI Admin Copilot
# ---------------------------------------------------------------------------

def test_copilot_returns_structured_answer():
    stu = _make_student("AISTU01", gpa=3.5)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS101", marks=80.0)
        result = admin_ai_tools.admin_copilot(db, question="How is placement looking this year?", actor="admin")
        assert result["question"]
        assert result["intent"] == "placement"
        assert result["summary"]
        assert isinstance(result["key_numbers"], list)
        assert isinstance(result["suggested_actions"], list)
        assert isinstance(result["citations"], list)
        assert result["provider"] == "local-fallback"
    finally:
        db.close()


def test_copilot_records_audit_event():
    db = SessionLocal()
    try:
        admin_ai_tools.admin_copilot(db, question="what is our health score?", actor="admin")
        event = db.execute(
            select(AuditLog).where(AuditLog.action == "copilot_query").order_by(AuditLog.created_at.desc())
        ).scalars().first()
        assert event is not None
        assert event.actor == "admin"
        assert event.payload["intent"] == "health"
    finally:
        db.close()


def test_copilot_detects_dropout_intent():
    db = SessionLocal()
    try:
        result = admin_ai_tools.admin_copilot(db, question="how many students are at risk of dropout?", actor="admin")
        assert result["intent"] == "dropout"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# University Digital Twin + scenarios
# ---------------------------------------------------------------------------

def test_digital_twin_shape():
    db = SessionLocal()
    try:
        twin = admin_ai_tools.university_digital_twin(db)
        assert "state" in twin
        assert "health" in twin
        assert twin["health"]["university_health_score"] is not None
        assert isinstance(twin["subsystems"], list)
        assert len(twin["subsystems"]) == 5
        assert any(s["key"] == "academic" for s in twin["subsystems"])
        assert isinstance(twin["entities"], dict)
        assert "students" in twin["entities"]
        assert isinstance(twin["warnings"], list)
        assert twin["trajectory"] in ("improving", "stable", "declining")
    finally:
        db.close()


def test_scenario_improves_score_with_positive_deltas():
    stu = _make_student("AISTU02", gpa=2.5)
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS102", marks=50.0, attendance=0.6)
        result = admin_ai_tools.run_scenario(
            db, attendance_delta=15.0, pass_rate_delta=10.0, placement_delta=5.0, interventions=1,
        )
        assert result["projected"]["university_health_score"] >= result["baseline"]["university_health_score"]
        assert result["impact"]["score_delta"] == (
            result["projected"]["university_health_score"] - result["baseline"]["university_health_score"]
        )
        assert len(result["assumptions"]) == 5
    finally:
        db.close()


def test_scenario_clamps_deltas():
    db = SessionLocal()
    try:
        result = admin_ai_tools.run_scenario(db, attendance_delta=200.0)
        assert result["projected"]["kpis"]["attendance"] <= 100.0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# AI Timetable Optimization
# ---------------------------------------------------------------------------

def test_timetable_conflicts_detected():
    db = SessionLocal()
    try:
        lecturer = _make_lecturer("AIFAC01")
        course_a = _course(db, "CS200")
        course_b = _course(db, "CS201")
        room = _room(db, "ADM-101")
        db.add(TimetableEntry(course_id=course_a.id, room_id=room.id, lecturer_id=lecturer.id,
                              day="Monday", start_time=time(9, 0), end_time=time(11, 0), term="2026-S1"))
        db.add(TimetableEntry(course_id=course_b.id, room_id=room.id, lecturer_id=lecturer.id,
                              day="Monday", start_time=time(10, 0), end_time=time(12, 0), term="2026-S1"))
        db.commit()
        result = admin_ai_tools.timetable_conflicts(db)
        assert result["count"] >= 2
        assert any(c["type"] == "room" for c in result["conflicts"])
        assert any(c["type"] == "lecturer" for c in result["conflicts"])
    finally:
        db.close()


def test_optimize_timetable_no_conflicts_without_commit():
    db = SessionLocal()
    try:
        _make_lecturer("AIFAC02")
        _room(db, "ADM-102")
        _course(db, "CS300")
        result = admin_ai_tools.optimize_timetable(db, commit=False)
        assert result["commit"] is False
        assert result["stats"]["courses_scheduled"] >= 1
        assert result["proposed"], "expected a proposed schedule"
        rows = db.execute(select(TimetableEntry).where(TimetableEntry.term == "optimized")).scalars().all()
        assert rows == [], "no entries should persist without commit"
    finally:
        db.close()


def test_optimize_timetable_commit_persists_and_audits():
    db = SessionLocal()
    try:
        _make_lecturer("AIFAC03")
        _room(db, "ADM-103")
        _course(db, "CS301")
        result = admin_ai_tools.optimize_timetable(db, commit=True)
        assert result["commit"] is True
        rows = db.execute(select(TimetableEntry).where(TimetableEntry.term == "optimized")).scalars().all()
        assert len(rows) >= 1
        event = db.execute(
            select(AuditLog).where(AuditLog.action == "timetable_optimized").order_by(AuditLog.created_at.desc())
        ).scalars().first()
        assert event is not None
        assert event.payload["scheduled"] >= 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# AI Evaluation Center
# ---------------------------------------------------------------------------

def test_evaluation_deterministic_fallback():
    db = SessionLocal()
    try:
        result = admin_ai_tools.evaluate_answer(
            db, course_code="CS101", question="Explain binary trees",
            rubric="Clarity: clear expression of ideas\nDepth: thorough analysis of the topic",
            answer=("A binary tree is a hierarchical data structure where each node has at most two children. "
                    "It supports efficient search, insertion, and deletion operations. Balanced trees such as "
                    "AVL and red-black trees guarantee logarithmic time complexity. Trees are used in databases, "
                    "routers, and compilers for expression parsing and indexing."),
            max_marks=100,
        )
        assert result["total_marks"] <= result["max_marks"]
        assert result["grade"] in ("A+", "A", "B", "C", "D", "F")
        assert isinstance(result["criteria"], list)
        assert result["criteria"]
        assert result["feedback"]
        assert isinstance(result["strengths"], list)
        assert isinstance(result["improvements"], list)
        assert result["provider"] == "local-fallback"
    finally:
        db.close()


def test_evaluation_short_answer_scores_lower():
    db = SessionLocal()
    try:
        result = admin_ai_tools.evaluate_answer(
            db, course_code="CS102", question="Explain OOP",
            rubric="Clarity: clear expression\nCompleteness: covers encapsulation, inheritance, polymorphism",
            answer="OOP is a programming paradigm.",
            max_marks=50,
        )
        assert result["total_marks"] < 50
        assert result["total_marks"] > 0
    finally:
        db.close()
