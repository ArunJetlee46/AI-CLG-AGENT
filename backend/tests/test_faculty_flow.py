"""Tests for the Faculty pipeline flow: propose -> approve -> execute -> audit.

Ends-to-end: a lecturer proposes an intervention, the request shows up in the
copilot status and audit log, approval executes the InterventionPlan, and both
the execute step and the audit log reflect the executed action.
"""
from datetime import date, time

from sqlalchemy import select

from app.agents.supervisor import approve_request
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    Course,
    Enrollment,
    InterventionPlan,
    Lecturer,
    Result,
    Student,
    TimetableEntry,
    User,
)
from app.services import faculty


def _make_lecturer(db, staff_id: str) -> tuple[User, Lecturer]:
    user = User(username=staff_id, password_hash=hash_password("lecturer123"), role="lecturer",
                email=f"{staff_id.lower()}@beru.edu")
    db.add(user)
    db.flush()
    lecturer = Lecturer(user_id=user.id, staff_id=staff_id, department="Computer Science", max_hours=20)
    db.add(lecturer)
    db.commit()
    db.refresh(user)
    db.refresh(lecturer)
    return user, lecturer


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


def _make_student(db, student_id: str, *, gpa: float = 1.4) -> Student:
    user = User(username=student_id, password_hash=hash_password("student123"), role="student",
                email=f"{student_id.lower()}@beru.edu")
    db.add(user)
    db.flush()
    stu = Student(user_id=user.id, student_id=student_id, year=2, program="Computer Science", gpa=gpa)
    db.add(stu)
    db.commit()
    db.refresh(stu)
    return stu


def _enroll(db, student: Student, course: Course, *, attendance: float = 0.35) -> Enrollment:
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    db.add(Result(enrollment_id=enrollment.id, marks=20.0, grade="F", semester="2026-S1"))
    for i in range(20):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 2, 2 + i),
                                status="present" if i < round(20 * attendance) else "absent"))
    db.commit()
    return enrollment


def test_pipeline_propose_approve_execute_audit():
    db = SessionLocal()
    try:
        user, lecturer = _make_lecturer(db, "LECFLOW1")
        course = _link_course(db, lecturer, "FLW101")
        stu = _make_student(db, "FLWSTU1")
        _enroll(db, stu, course)

        # propose -> pending approval + audit event + status reflects it
        proposal = faculty.propose_intervention(
            db, lecturer, student_id="FLWSTU1", course_code="FLW101",
            plan_text="Weekly mentoring and attendance recovery for this student.",
            actor_user_id=user.id,
        )
        assert proposal["status"] == "pending"

        status = faculty.get_copilot_status(db, lecturer, user)
        stages = {s["key"]: s["value"] for s in status["stages"]}
        assert stages["approval"] == 1
        assert stages["execute"] == 0
        assert stages["recommendation"] >= 1
        assert stages["audit"] >= 1

        pre = faculty.get_my_audit_log(db, lecturer, user, limit=10)
        assert any(e["action"] == "intervention_proposed" for e in pre["entries"])

        # approve -> execute agent persists the InterventionPlan + audit event
        decision = approve_request(proposal["approval_id"], decision="approve", admin_user_id=user.id)
        assert decision.get("ok")

        plan = db.execute(select(InterventionPlan).where(InterventionPlan.course_code == "FLW101")).scalar_one_or_none()
        assert plan is not None
        assert plan.status == "active"

        status2 = faculty.get_copilot_status(db, lecturer, user)
        stages2 = {s["key"]: s["value"] for s in status2["stages"]}
        assert stages2["approval"] == 0
        assert stages2["execute"] == 1

        post = faculty.get_my_audit_log(db, lecturer, user, limit=10)
        actions = {e["action"] for e in post["entries"]}
        assert "intervention_created" in actions
        assert post["total"] >= 2
    finally:
        db.close()


def test_audit_log_pagination_and_shape():
    db = SessionLocal()
    try:
        user, lecturer = _make_lecturer(db, "LECFLOW2")
        log = faculty.get_my_audit_log(db, lecturer, user, limit=5, offset=0)
        assert log["staff_id"] == "LECFLOW2"
        assert log["total"] == 0
        assert log["entries"] == []
    finally:
        db.close()
