"""Tests for the student timetable service."""
from datetime import date, time

from sqlalchemy import select

from sqlalchemy import text

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    Course,
    Enrollment,
    Lecturer,
    Room,
    Student,
    TimetableEntry,
    User,
)
from app.services.students import growth


def _make_student(student_id: str) -> Student:
    db = SessionLocal()
    try:
        user = User(
            username=student_id,
            password_hash=hash_password("x"),
            role="student",
            email=f"{student_id.lower()}@test.edu",
        )
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=2, program="CS", gpa=3.0)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _enroll(db, student: Student, code: str) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="CS")
        db.add(course)
        db.flush()
    db.add(Enrollment(student_id=student.id, course_id=course.id, status="approved"))
    db.commit()
    return course


def _make_room(db, room_no: str) -> Room:
    room = Room(room_no=room_no, capacity=60, kind="classroom")
    db.add(room)
    db.flush()
    return room


def _make_lecturer(db, staff_id: str) -> Lecturer:
    user = User(
        username=staff_id,
        password_hash=hash_password("x"),
        role="lecturer",
        email=f"{staff_id.lower()}@test.edu",
    )
    db.add(user)
    db.flush()
    lec = Lecturer(user_id=user.id, staff_id=staff_id, department="CS")
    db.add(lec)
    db.flush()
    return lec


def test_timetable_empty_when_no_enrollments():
    stu = _make_student("TT01")
    db = SessionLocal()
    try:
        result = growth.get_timetable(db, db.get(Student, stu.id))
        assert result["entries"] == []
        assert result["days"] == []
        assert result["by_day"] == {}
    finally:
        db.close()


def test_timetable_groups_entries_by_day():
    stu = _make_student("TT02")
    db = SessionLocal()
    try:
        course = _enroll(db, stu, "CS101")
        room = _make_room(db, "R101")
        lec = _make_lecturer(db, "LEC01")
        db.add_all([
            TimetableEntry(course_id=course.id, room_id=room.id, lecturer_id=lec.id,
                           day="Monday", start_time=time(9, 0), end_time=time(10, 0), term="2026-S1"),
            TimetableEntry(course_id=course.id, room_id=room.id, lecturer_id=lec.id,
                           day="Wednesday", start_time=time(11, 0), end_time=time(12, 0), term="2026-S1"),
        ])
        db.commit()

        result = growth.get_timetable(db, db.get(Student, stu.id))
        assert "Monday" in result["days"]
        assert "Wednesday" in result["days"]
        assert len(result["entries"]) == 2
        assert result["by_day"]["Monday"][0]["start_time"] == "09:00"
        assert result["by_day"]["Monday"][0]["room"] == "R101"
        assert result["by_day"]["Monday"][0]["lecturer"] == "LEC01"
        assert result["by_day"]["Monday"][0]["course_code"] == "CS101"
    finally:
        db.close()


def test_timetable_excludes_unapproved_enrollments():
    stu = _make_student("TT03")
    db = SessionLocal()
    try:
        course = _enroll(db, stu, "CS202")
        room = _make_room(db, "R202")
        lec = _make_lecturer(db, "LEC02")
        # unenroll by deleting the approved enrollment and adding a pending one
        db.execute(
            text("DELETE FROM enrollments WHERE student_id = :sid AND course_id = :cid"),
            {"sid": stu.id, "cid": course.id},
        )
        db.flush()
        db.add(Enrollment(student_id=stu.id, course_id=course.id, status="pending"))
        db.add(TimetableEntry(course_id=course.id, room_id=room.id, lecturer_id=lec.id,
                              day="Friday", start_time=time(14, 0), end_time=time(15, 0)))
        db.commit()

        result = growth.get_timetable(db, db.get(Student, stu.id))
        assert result["entries"] == []
    finally:
        db.close()


def test_timetable_sorted_within_day():
    stu = _make_student("TT04")
    db = SessionLocal()
    try:
        c1 = _enroll(db, stu, "CS301")
        c2 = _enroll(db, stu, "CS302")
        room = _make_room(db, "R301")
        lec = _make_lecturer(db, "LEC03")
        db.add_all([
            TimetableEntry(course_id=c1.id, room_id=room.id, lecturer_id=lec.id,
                           day="Tuesday", start_time=time(14, 0), end_time=time(15, 0), term="T2"),
            TimetableEntry(course_id=c2.id, room_id=room.id, lecturer_id=lec.id,
                           day="Tuesday", start_time=time(10, 0), end_time=time(11, 0), term="T2"),
        ])
        db.commit()

        result = growth.get_timetable(db, db.get(Student, stu.id))
        tue = result["by_day"]["Tuesday"]
        assert tue[0]["start_time"] == "10:00"
        assert tue[1]["start_time"] == "14:00"
    finally:
        db.close()
