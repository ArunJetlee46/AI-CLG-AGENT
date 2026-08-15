"""Tests for the admin analytics + management batch (admin_intelligence)."""
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
from app.services import admin_intelligence


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
    course = _course(db, code)
    db.add(TimetableEntry(course_id=course.id, room_id="", lecturer_id=lecturer.id, day="MON",
                          start_time=time(9, 0), end_time=time(11, 0), term="2026-S1"))
    db.commit()


def test_user_management_audit_logged():
    db = SessionLocal()
    try:
        row = admin_intelligence.create_user(db, actor="admin", username="admintest01",
                                             password="secret123", role="lecturer", email="t@beru.edu")
        assert row["role"] == "lecturer"
        assert row["is_active"] is True
        users = admin_intelligence.list_users(db)
        assert any(u["id"] == row["id"] for u in users)

        updated = admin_intelligence.update_user(db, actor="admin", user_id=row["id"],
                                                 is_active=False, role="admin")
        assert updated["is_active"] is False
        assert updated["role"] == "admin"

        from app.models.entities import AuditLog
        created = db.execute(select(AuditLog).where(AuditLog.action == "user_created",
                                                    AuditLog.entity_id == row["id"])).scalar_one_or_none()
        assert created is not None
        assert created.actor == "admin"
        try:
            admin_intelligence.create_user(db, actor="admin", username="admintest01",
                                           password="secret123", role="student")
            assert False, "duplicate username should raise"
        except ValueError:
            pass
    finally:
        db.close()


def test_departments_include_all_programs():
    stu = _make_student("ADISTU01", program="Electronics Engineering")
    db = SessionLocal()
    try:
        _enroll(db, stu, "ADIDEPT1", grade="B", marks=65.0)
        result = admin_intelligence.list_departments(db)
        assert "count" in result
        assert "all_programs" in result
        assert any(p == "Electronics Engineering" for p in result["all_programs"])
        assert any(d["program"] == "Electronics Engineering" for d in result["departments"])
    finally:
        db.close()


def test_announcement_crud():
    db = SessionLocal()
    try:
        a = admin_intelligence.create_announcement(db, actor="admin", title="Exam schedule",
                                                   body="Midterms next week.", audience="students", pinned=True)
        assert a["pinned"] is True
        assert any(x["id"] == a["id"] for x in admin_intelligence.list_announcements(db))
        deleted = admin_intelligence.delete_announcement(db, actor="admin", announcement_id=a["id"])
        assert deleted["ok"] is True
        assert not any(x["id"] == a["id"] for x in admin_intelligence.list_announcements(db))
    finally:
        db.close()


def test_resource_management():
    db = SessionLocal()
    try:
        r = admin_intelligence.create_resource(db, actor="admin", name="Lab 2", resource_type="lab",
                                               capacity=40, location="Block B", status="active",
                                               utilization=70.0, notes="")
        assert r["resource_type"] == "lab"
        listing = admin_intelligence.list_resources(db)
        assert listing["count"] >= 1
        updated = admin_intelligence.update_resource(db, actor="admin", resource_id=r["id"],
                                                     status="maintenance")
        assert updated["status"] == "maintenance"
    finally:
        db.close()


def test_backup_snapshot_and_restore():
    db = SessionLocal()
    try:
        b = admin_intelligence.create_backup(db, actor="admin", note="weekly")
        assert b["status"] == "completed"
        assert b["snapshot"]["users"] >= 1
        assert b["snapshot"]["students"] >= 1
        backups = admin_intelligence.list_backups(db)
        assert any(x["id"] == b["id"] for x in backups)
        restored = admin_intelligence.restore_backup(db, actor="admin", backup_id=b["id"])
        assert restored["ok"] is True
    finally:
        db.close()


def test_model_registry_single_active():
    db = SessionLocal()
    try:
        m1 = admin_intelligence.register_model(db, actor="admin", name="pass-predictor",
                                               version="v2", path="artifacts/p2.bin", metrics={"auc": 0.85})
        m2 = admin_intelligence.register_model(db, actor="admin", name="dropout-risk",
                                               version="v1", path="artifacts/d1.bin", metrics={"auc": 0.81})
        admin_intelligence.set_model_active(db, actor="admin", model_id=m1["id"])
        listing = admin_intelligence.list_models(db)
        assert listing["count"] >= 2
        assert listing["active"]["id"] == m1["id"]
        admin_intelligence.set_model_active(db, actor="admin", model_id=m2["id"])
        listing = admin_intelligence.list_models(db)
        assert listing["active"]["id"] == m2["id"]
        assert sum(1 for m in listing["models"] if m["is_active"]) == 1
    finally:
        db.close()


def test_student_analytics_bands_and_rankings():
    strong = _make_student("ADISTU02", gpa=3.8)
    weak = _make_student("ADISTU03", gpa=1.0)
    db = SessionLocal()
    try:
        _enroll(db, strong, "ADIA101", grade="A", marks=95.0, attendance=0.99)
        _enroll(db, weak, "ADIA102", grade="F", marks=12.0, attendance=0.15)
        result = admin_intelligence.student_analytics(db)
        assert result["total"] >= 2
        assert sum(result["risk_bands"].values()) == result["total"]
        assert result["risk_bands"]["high"] >= 1
        assert result["top_students"][0]["student_id"] == "ADISTU02"
        assert result["bottom_students"][0]["student_id"] == "ADISTU03"
        assert any(p["program"] == "Computer Science" for p in result["by_program"])
    finally:
        db.close()


def test_faculty_analytics_attaches_pass_rate():
    lecturer = _make_lecturer("ADILEC1")
    student = _make_student("ADISTU04")
    db = SessionLocal()
    try:
        _link_course(db, lecturer, "ADIA201")
        _enroll(db, student, "ADIA201", grade="A", marks=88.0)
        result = admin_intelligence.faculty_analytics(db)
        row = next(w for w in result["rows"] if w["staff_id"] == "ADILEC1")
        assert row["avg_pass_rate"] == 100.0
        assert result["summary"]["total_faculty"] >= 1
    finally:
        db.close()


def test_placement_overview_reuses_intelligence():
    db = SessionLocal()
    try:
        result = admin_intelligence.placement_overview(db)
        assert "funnel" in result
        assert "salary" in result
        assert "skill_demand" in result
        assert "prediction" in result
        assert result["companies"] >= 0
    finally:
        db.close()


def test_dropout_analytics_ranking():
    weak = _make_student("ADISTU05", gpa=0.9)
    db = SessionLocal()
    try:
        _enroll(db, weak, "ADIA301", grade="F", marks=10.0, attendance=0.1)
        result = admin_intelligence.dropout_analytics(db)
        assert result["total"] >= 1
        assert result["bands"]["high"] >= 1
        assert result["top_risk"][0]["student_id"] == "ADISTU05"
        assert result["drivers"]["avg_gpa"] <= 4.0
        assert any(p["program"] for p in result["by_program"])
    finally:
        db.close()


def test_curriculum_intelligence_flags_difficult_and_prereq_gap():
    strong = _make_student("ADISTU06", gpa=3.6)
    weak = _make_student("ADISTU07", gpa=1.2)
    db = SessionLocal()
    try:
        pre = _course(db, "ADIA401")
        pre.prerequisites = []
        db.commit()
        _enroll(db, strong, "ADIA401", grade="A", marks=90.0)
        hard = _course(db, "ADIA402")
        hard.prerequisites = ["ADIA401"]
        db.commit()
        _enroll(db, weak, "ADIA402", grade="F", marks=15.0)
        result = admin_intelligence.curriculum_intelligence(db)
        assert any(c["course_code"] == "ADIA402" and c["difficult"] for c in result["courses"])
        gap = next((g for g in result["prerequisite_health"]
                    if g["course_code"] == "ADIA402" and g["prerequisite"] == "ADIA401"), None)
        assert gap is not None
        assert gap["healthy"] is False
    finally:
        db.close()


def test_enrollment_forecast_series():
    _make_student("ADISTU08")
    db = SessionLocal()
    try:
        result = admin_intelligence.enrollment_forecast(db)
        assert len(result["historical"]) >= 1
        assert len(result["forecast"]) == 3
        assert all(f["forecast"] for f in result["forecast"])
        assert result["total_enrollments"] >= 1
        assert result["by_department"]
    finally:
        db.close()


def test_accreditation_scorecard():
    db = SessionLocal()
    try:
        result = admin_intelligence.accreditation(db)
        assert 0 <= result["overall_score"] <= 100
        assert result["grade"] in ("A++", "A+", "A", "B+", "B", "C")
        assert set(result["criteria"]) >= {"Curricular Aspects", "Student Support & Progression"}
        assert result["total_checks"] == len(result["readiness"]) == 5
    finally:
        db.close()


def test_research_and_industry_intelligence():
    db = SessionLocal()
    try:
        admin_intelligence.create_project(db, actor="admin", title="NLP for exams",
                                          lead_name="Dr. X", department="CS", status="active",
                                          funding_amount=100000.0, publications=2, start_year=2025)
        research = admin_intelligence.research_dashboard(db)
        assert research["total_projects"] >= 1
        assert research["total_funding"] >= 100000.0
        assert research["total_publications"] >= 2

        admin_intelligence.create_partner(db, actor="admin", name="TechCorp", sector="IT",
                                          contact_person="Jane", mous=3, active=True, placement_hires=12)
        industry = admin_intelligence.industry_intelligence(db)
        assert industry["total_partners"] >= 1
        assert industry["total_mous"] >= 3
        assert industry["total_hires"] >= 12
    finally:
        db.close()


def test_system_health_and_audit_chain():
    db = SessionLocal()
    try:
        result = admin_intelligence.system_health(db)
        assert result["overall"] in ("healthy", "degraded")
        assert result["checks"]["database"]["status"] == "ok"
        assert result["checks"]["audit_chain"]["status"] == "ok"
        assert result["counts"]["users"] >= 1
    finally:
        db.close()


def test_governance_center():
    db = SessionLocal()
    try:
        result = admin_intelligence.governance_center(db)
        assert "safety" in result
        assert "approvals" in result
        assert "audit" in result
        assert "models" in result
        assert isinstance(result["recommendations"], list)
    finally:
        db.close()
