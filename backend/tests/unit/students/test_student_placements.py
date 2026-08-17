"""Tests for the student placements hub (readiness, shortlists, drives)."""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    Company,
    Course,
    Enrollment,
    PlacementDrive,
    PlacementNotification,
    Result,
    Student,
    User,
)
from app.services.students import placements


def _make_student(student_id: str) -> Student:
    db = SessionLocal()
    try:
        user = User(username=student_id, password_hash=hash_password("x"), role="student",
                     email=f"{student_id.lower()}@test.edu")
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=2, program="CS", gpa=3.0)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _seed_enrollment(db, student: Student):
    course = db.execute(select(Course).where(Course.code == "PL101")).scalar_one_or_none()
    if course is None:
        course = Course(code="PL101", title="Placement Course", credits=3, department="CS")
        db.add(course)
        db.flush()
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    db.add(Result(enrollment_id=enrollment.id, marks=70.0, grade="B", semester="2026-S1"))
    for i in range(10):
        db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 3, 2 + i), status="present"))
    db.commit()


def _make_company(db, name: str) -> Company:
    company = Company(name=name, sector="IT", location="Bangalore")
    db.add(company)
    db.flush()
    return company


def _make_drive(db, company: Company, title: str = "Campus Drive", drive_date: date = date(2026, 6, 1)):
    drive = PlacementDrive(title=title, company_id=company.id, drive_date=drive_date,
                           mode="online", location="Main Auditorium", status="scheduled")
    db.add(drive)
    db.flush()
    return drive


def test_placements_empty_when_no_data():
    stu = _make_student("PL01")
    db = SessionLocal()
    try:
        result = placements.get_placements(db, db.get(Student, stu.id))
        assert result["student_id"] == "PL01"
        assert result["shortlists"] == []
        assert result["upcoming_drives"] == []
    finally:
        db.close()


def test_placements_with_shortlist_and_drive():
    stu = _make_student("PL02")
    db = SessionLocal()
    try:
        _seed_enrollment(db, stu)
        company = _make_company(db, "Acme Corp")
        drive = _make_drive(db, company, "Acme Drive", date(2026, 7, 1))
        db.add(PlacementNotification(
            drive_id=drive.id, student_id=stu.id,
            title="You are shortlisted!", body="Congratulations!", status="sent",
        ))
        db.commit()

        result = placements.get_placements(db, db.get(Student, stu.id))
        assert len(result["shortlists"]) == 1
        assert result["shortlists"][0]["title"] == "You are shortlisted!"
        assert result["shortlists"][0]["drive"]["company"] == "Acme Corp"
        assert result["shortlists"][0]["drive"]["title"] == "Acme Drive"
        assert len(result["upcoming_drives"]) >= 1
        assert result["upcoming_drives"][0]["company"] == "Acme Corp"
    finally:
        db.close()


def test_placements_readiness_populated_for_enrolled_student():
    stu = _make_student("PL03")
    db = SessionLocal()
    try:
        _seed_enrollment(db, stu)
        result = placements.get_placements(db, db.get(Student, stu.id))
        r = result["readiness"]
        assert r is not None
        assert 0 <= r["readiness_score"] <= 100
        assert r["band"] in ("ready", "needs_improvement", "not_ready")
        assert len(r["drivers"]) > 0
        assert len(r["components"]) == 4
    finally:
        db.close()
