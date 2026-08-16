"""Theme A: new specialist agents (placement, attendance, exam, advising).

Personalized paths require a real Student row; generic paths must degrade
gracefully on an empty database. Tests seed and remove their own student.
"""

from datetime import date, timedelta

from app.agents.specialists import (
    AdvisingAgent,
    AttendanceAgent,
    ExamAgent,
    PlacementAgent,
)
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Result, Student, User

COURSE_CODE = "TA101"


def _seed_student(student_id: str = "STU-TA01") -> tuple[str, str]:
    db = SessionLocal()
    try:
        user = User(
            username=student_id,
            password_hash=hash_password("test123"),
            role="student",
            email="ta@beru.edu",
        )
        db.add(user)
        db.flush()
        student = Student(user_id=user.id, student_id=student_id, year=3, program="BSc CS", gpa=3.1)
        db.add(student)
        db.flush()
        course = db.query(Course).filter_by(code=COURSE_CODE).first()
        if course is None:
            course = Course(code=COURSE_CODE, title="Test Course", credits=3)
            db.add(course)
            db.flush()
        enrollment = Enrollment(
            student_id=student.id,
            course_id=course.id,
            status="approved",
        )
        db.add(enrollment)
        db.flush()
        db.add_all(
            [
                AttendanceRecord(enrollment_id=enrollment.id, day=date.today() - timedelta(days=2), status="present"),
                AttendanceRecord(enrollment_id=enrollment.id, day=date.today() - timedelta(days=1), status="present"),
                AttendanceRecord(enrollment_id=enrollment.id, day=date.today(), status="absent"),
            ]
        )
        db.commit()
        return user.id, student.id
    finally:
        db.close()


def _remove_student(student_id: str) -> None:
    db = SessionLocal()
    try:
        student = db.query(Student).filter_by(student_id=student_id).first()
        if student is not None:
            for enrollment in list(student.enrollments):
                for row in db.query(AttendanceRecord).filter_by(enrollment_id=enrollment.id):
                    db.delete(row)
                db.query(Result).filter_by(enrollment_id=enrollment.id).delete()
                db.delete(enrollment)
            db.delete(student)
            db.commit()
        user = db.query(User).filter_by(username=student_id).first()
        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _state(student_id: str = "", message: str = "help") -> dict:
    return {
        "student_id": student_id,
        "messages": [{"role": "user", "content": message}],
        "audit_events": [],
    }


def test_placement_agent_personalizes_for_student() -> None:
    _, student_pk = _seed_student()
    try:
        state = _state(student_id="STU-TA01", message="what is my placement readiness?")
        PlacementAgent().run(state)
        assert "STU-TA01" in state["answer"]
        assert "readiness" in state["answer"].lower()
        assert state["data"]["readiness"]["student_id"] == "STU-TA01"
        assert any(e["action"] == "placement_readiness" for e in state["audit_events"])
    finally:
        _remove_student("STU-TA01")


def test_placement_agent_overview_on_empty_db() -> None:
    state = _state(message="placement overview")
    PlacementAgent().run(state)
    assert "Placement overview" in state["answer"]
    assert state["data"]["overview"]["total_students"] >= 0


def test_attendance_agent_personalizes_for_student() -> None:
    _seed_student()
    try:
        state = _state(student_id="STU-TA01", message="is my attendance below 75%?")
        AttendanceAgent().run(state)
        assert "STU-TA01" in state["answer"]
        assert "Attendance for" in state["answer"]
        assert any(e["action"] == "attendance_summary" for e in state["audit_events"])
    finally:
        _remove_student("STU-TA01")


def test_attendance_agent_generic_on_empty_db() -> None:
    state = _state(message="attendance snapshot")
    AttendanceAgent().run(state)
    assert state["answer"]
    assert state["data"]["courses"] is not None


def test_exam_agent_requires_student() -> None:
    state = _state(message="generate practice questions for CS301")
    ExamAgent().run(state)
    assert "student account" in state["answer"].lower()


def test_advising_agent_answers_without_student() -> None:
    state = _state(message="what are the prerequisites for CS302")
    AdvisingAgent().run(state)
    assert state["answer"]
    assert any(e["action"] == "course_advising" for e in state["audit_events"])


def test_advising_agent_asks_for_course_without_code() -> None:
    state = _state(message="am I eligible for the course")
    AdvisingAgent().run(state)
    assert "course code" in state["answer"].lower()


def test_advising_agent_adds_personalized_verdict() -> None:
    _seed_student()
    try:
        state = _state(student_id="STU-TA01", message="can I take TA101?")
        AdvisingAgent().run(state)
        assert "TA101" in state["answer"]
        assert "eligible" in state["answer"].lower()
        assert state["data"]["courses"]["TA101"]["exists"] is True
        assert any(e["action"] == "course_advising" for e in state["audit_events"])
    finally:
        _remove_student("STU-TA01")
