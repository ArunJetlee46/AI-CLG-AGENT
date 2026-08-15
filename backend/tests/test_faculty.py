"""Tests for the Faculty Copilot services and approval-gated interventions."""
from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    ApprovalRequest,
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


def _make_lecturer(staff_id: str = "LECTEST") -> Lecturer:
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


def _link_course(db, lecturer: Lecturer, code: str, *, hours: float = 2.0) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=[])
        db.add(course)
        db.flush()
    entry = db.execute(select(TimetableEntry).where(TimetableEntry.lecturer_id == lecturer.id,
                                                    TimetableEntry.course_id == course.id)).scalar_one_or_none()
    if entry is None:
        from datetime import time

        db.add(TimetableEntry(course_id=course.id, room_id="", lecturer_id=lecturer.id, day="MON",
                              start_time=time(9, 0), end_time=time(9 + int(hours), 0), term="2026-S1"))
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
    from datetime import date

    for i in range(20):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 2, 2 + i),
                                status="present" if i < round(20 * attendance) else "absent"))
    db.commit()
    return enrollment


def test_resolve_lecturer_uses_linked_record():
    lecturer = _make_lecturer("LECTEST1")
    db = SessionLocal()
    try:
        user = db.get(User, lecturer.user_id)
        assert faculty.resolve_lecturer(db, user).staff_id == "LECTEST1"
    finally:
        db.close()


def test_profile_workload_aggregates():
    lecturer = _make_lecturer("LECTEST2")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC101", hours=2.0)
        stu1 = _make_student("FSTU01")
        stu2 = _make_student("FSTU02")
        _enroll(db, stu1, course, grade="B", attendance=0.9)
        _enroll(db, stu2, course, grade="A", attendance=0.8)
        profile = faculty.get_profile(db, lecturer)
        assert profile["staff_id"] == "LECTEST2"
        assert profile["course_count"] == 1
        assert profile["student_count"] == 2
        assert profile["teaching_hours"] >= 2.0
    finally:
        db.close()


def test_overview_summary_and_bands():
    lecturer = _make_lecturer("LECTEST3")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC102")
        strong = _make_student("FSTU03", gpa=3.8)
        weak = _make_student("FSTU04", gpa=1.2)
        _enroll(db, strong, course, grade="A", marks=92.0, attendance=0.95)
        _enroll(db, weak, course, grade="F", marks=10.0, attendance=0.3)
        overview = faculty.get_overview(db, lecturer)
        assert overview["summary"]["students"] == 2
        assert overview["summary"]["strong"] == 1
        assert overview["summary"]["at_risk"] >= 1
        assert overview["courses"][0]["pass_rate"] == 0.5
    finally:
        db.close()


def test_at_risk_reasons_are_explainable():
    lecturer = _make_lecturer("LECTEST4")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC103")
        weak = _make_student("FSTU05", gpa=1.8)
        _enroll(db, weak, course, grade="F", marks=25.0, attendance=0.5)
        monitor = faculty.get_at_risk(db, lecturer)
        assert monitor
        assert monitor[0]["risk_level"] in ("high", "medium")
        assert any("attendance" in r for r in monitor[0]["reasons"])
        assert any("GPA" in r for r in monitor[0]["reasons"])
    finally:
        db.close()


def test_course_health_bounded_and_bands():
    lecturer = _make_lecturer("LECTEST5")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC104")
        good = _make_student("FSTU06", gpa=3.7)
        _enroll(db, good, course, grade="A", marks=95.0, attendance=0.98)
        health = faculty.get_course_health(db, lecturer, "FAC104")
        assert health["exists"] and health["authorized"]
        assert health["enrolled"] == 1
        assert health["health_score"] > 75
        assert health["band"] == "healthy"
    finally:
        db.close()


def test_course_attendance_below_threshold():
    lecturer = _make_lecturer("LECTEST6")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC105")
        low = _make_student("FSTU07")
        ok = _make_student("FSTU08")
        _enroll(db, low, course, attendance=0.5)
        _enroll(db, ok, course, attendance=0.9)
        report = faculty.get_course_attendance(db, lecturer, "FAC105")
        assert report["below_count"] == 1
        assert report["students"][0]["student_id"] == "FSTU07"
    finally:
        db.close()


def test_intervention_flow_propose_then_apply():
    lecturer = _make_lecturer("LECTEST7")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC106")
        student = _make_student("FSTU09", gpa=1.9)
        _enroll(db, student, course, grade="F", attendance=0.45)

        proposal = faculty.propose_intervention(
            db, lecturer, student_id="FSTU09", course_code="FAC106",
            plan_text="Schedule a meeting, recommend Unit 2 revision, monitor attendance for 2 weeks.",
        )
        assert proposal["status"] == "pending"

        approval = db.get(ApprovalRequest, proposal["approval_id"])
        assert approval.intent == "intervention"
        assert approval.payload["action"] == "intervention"
        assert approval.payload["student_id"] == student.id

        approval.status = "approved"
        db.commit()

        from app.services.execution import apply_intervention

        result = apply_intervention(db, approval_id=approval.id, actor=lecturer.staff_id)
        assert result["ok"] is True
        plan = db.execute(select(InterventionPlan).where(InterventionPlan.id == result["intervention_id"])).scalar_one()
        assert plan.student_id == student.id
        assert plan.course_code == "FAC106"
        assert plan.status == "active"
    finally:
        db.close()


def test_intervention_rejects_unenrolled_student():
    lecturer = _make_lecturer("LECTEST8")
    db = SessionLocal()
    try:
        course = _link_course(db, lecturer, "FAC107")
        _make_student("FSTU10")
        try:
            faculty.propose_intervention(db, lecturer, student_id="FSTU10", course_code="FAC107", plan_text="Test plan")
            assert False, "expected ValueError for unenrolled student"
        except ValueError as exc:
            assert "not enrolled" in str(exc)
    finally:
        db.close()
