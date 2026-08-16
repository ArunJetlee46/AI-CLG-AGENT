"""Tests for the Admin Copilot services and the emergency kill switch."""
from sqlalchemy import select

from app.core.security import hash_password
from app.core.safety import set_safety
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Lecturer, Result, Student, TimetableEntry, User
from app.services import admin_copilot
from app.services.execution import apply_intervention


def _make_student(student_id: str, *, gpa: float = 3.0, program: str = "Computer Science") -> Student:
    db = SessionLocal()
    try:
        user = User(username=student_id, password_hash=hash_password("student123"), role="student",
                    email=f"{student_id.lower()}@beru.edu")
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=3, program=program, gpa=gpa)
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


def _link_course(db, lecturer: Lecturer, code: str) -> None:
    from datetime import time

    course = _course(db, code)
    db.add(TimetableEntry(course_id=course.id, room_id="", lecturer_id=lecturer.id, day="MON",
                          start_time=time(9, 0), end_time=time(11, 0), term="2026-S1"))
    db.commit()


def _make_approval(db, status: str) -> str:
    from app.models.entities import ApprovalRequest

    approval = ApprovalRequest(user_id="admin", intent="test", payload={}, status=status)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval.id


def test_command_center_counts_and_kpis():
    strong = _make_student("ADSTU01", gpa=3.7)
    weak = _make_student("ADSTU02", gpa=1.1)
    db = SessionLocal()
    try:
        _enroll(db, strong, "ADM101", grade="A", marks=92.0, attendance=0.98)
        _enroll(db, weak, "ADM102", grade="F", marks=15.0, attendance=0.2)
        cc = admin_copilot.command_center(db)
        assert cc["counts"]["students"] >= 2
        assert cc["counts"]["departments"] >= 1
        assert cc["kpis"]["attendance"] <= 100
        assert cc["kpis"]["at_risk"] >= 0
        assert cc["pending_approvals"] == 0
        assert cc["system_health"]["database"] == "ok"
    finally:
        db.close()


def test_health_score_bounded_and_axes():
    strong = _make_student("ADSTU03", gpa=3.8)
    db = SessionLocal()
    try:
        _enroll(db, strong, "ADM103", grade="A", marks=95.0, attendance=0.99)
        score = admin_copilot.health_score(db)
        assert 0 <= score["university_health_score"] <= 100
        assert set(score["axes"]) == {"academic", "student_success", "placement", "faculty", "ai_operations"}
        assert 0 <= score["basis"]["avg_gpa"] <= 4
    finally:
        db.close()


def test_early_warnings_raises_signals():
    weak = _make_student("ADSTU04", gpa=1.0)
    db = SessionLocal()
    try:
        _enroll(db, weak, "ADM104", grade="F", marks=10.0, attendance=0.1)
        warnings = admin_copilot.early_warnings(db)
        assert any(w["id"] == "dropout-risk" for w in warnings)
        assert any(w["severity"] in ("critical", "important", "warning") for w in warnings)
        assert all(w["recommendation"] for w in warnings)
    finally:
        db.close()


def test_departments_grouped_and_flagged():
    weak = _make_student("ADSTU05", gpa=1.2, program="Mechanical Engineering")
    db = SessionLocal()
    try:
        _enroll(db, weak, "ADM105", grade="F", marks=20.0, attendance=0.4)
        result = admin_copilot.departments(db)
        assert result["count"] >= 1
        mech = next(d for d in result["departments"] if d["program"] == "Mechanical Engineering")
        assert mech["students"] == 1
        assert mech["flag"] in ("weak performance", "low attendance")
    finally:
        db.close()


def test_faculty_workload_aggregates():
    lecturer = _make_lecturer("ADLEC1")
    student = _make_student("ADSTU06")
    db = SessionLocal()
    try:
        _link_course(db, lecturer, "ADM106")
        _enroll(db, student, "ADM106")
        workload = admin_copilot.faculty_workload(db)
        row = next(w for w in workload if w["staff_id"] == "ADLEC1")
        assert row["course_count"] == 1
        assert row["student_count"] == 1
        assert row["teaching_hours"] >= 1.9
    finally:
        db.close()


def test_agents_registry_derived():
    db = SessionLocal()
    try:
        registry = admin_copilot.agents(db)
        assert len(registry) == 7
        assert any(a["name"] == "Execute Agent" for a in registry)
        assert all(a["success_rate"] == 100.0 for a in registry)
    finally:
        db.close()


def test_safety_kill_switch_blocks_execution():
    set_safety(execution_enabled=True, read_only=False)
    db = SessionLocal()
    try:
        approval_id = _make_approval(db, "approved")
        assert admin_copilot.get_safety_state()["execution_allowed"] is True

        set_safety(execution_enabled=False, read_only=False)
        assert admin_copilot.get_safety_state()["execution_allowed"] is False
        try:
            apply_intervention(db, approval_id=approval_id, actor="admin")
            assert False, "expected execution to be blocked while paused"
        except ValueError as exc:
            assert "paused" in str(exc)
    finally:
        set_safety(execution_enabled=True, read_only=False)
        db.close()
