"""Deterministic, privacy-safe synthetic university data generator.

Generates students, lecturers, courses, enrollments, results, attendance,
rooms and timetable entries with embedded failure patterns so ML models can
be validated. Fully seeded -> reproducible. No real PII.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import random
import string

from app.db import SessionLocal
from app.models.entities import (
    Admin,
    AttendanceRecord,
    Course,
    Enrollment,
    Lecturer,
    Result,
    Room,
    Student,
    TimetableEntry,
    User,
)
from app.core.security import hash_password

FIRST_NAMES = [
    "Amina", "Chidi", "Kwame", "Lindiwe", "Obi", "Zainab", "Tunde", "Ngozi",
    "Kofi", "Yaa", "Emeka", "Sade", "Bello", "Adaeze", "Musa", "Funke",
]
LAST_NAMES = [
    "Okonkwo", "Mensah", "Okafor", "Banda", "Adeyemi", "Nwosu", "Osei",
    "Chukwu", "Akinola", "Dlamini", "Eze", "Balogun", "Kone", "Diop",
]
DEPARTMENTS = ["Computer Science", "Engineering", "Business", "Law", "Medicine", "Arts"]
GRADES = ["A", "B", "C", "D", "E", "F"]


@dataclass
class DatasetBundle:
    students: list[dict] = field(default_factory=list)
    lecturers: list[dict] = field(default_factory=list)
    courses: list[dict] = field(default_factory=list)
    enrollments: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    attendance: list[dict] = field(default_factory=list)
    rooms: list[dict] = field(default_factory=list)
    timetable: list[dict] = field(default_factory=list)


class SyntheticDataGenerator:
    def __init__(self, students: int = 500, courses: int = 40, seed: int = 42) -> None:
        self.students_n = students
        self.courses_n = courses
        self.rng = random.Random(seed)

    def generate(self) -> DatasetBundle:
        bundle = DatasetBundle()

        for idx in range(self.courses_n):
            dept = self.rng.choice(DEPARTMENTS)
            code = f"{dept[:2].upper()}{self.rng.randint(100, 499)}"
            bundle.courses.append(
                {
                    "id": f"c{idx:04d}",
                    "code": code,
                    "title": f"{dept} Course {code}",
                    "credits": self.rng.choice([2, 3, 3, 4]),
                    "capacity": self.rng.choice([30, 40, 60, 80, 120]),
                    "department": dept,
                    "prerequisites": [],
                }
            )
        for idx in range(self.courses_n - 1):
            if self.rng.random() < 0.35:
                bundle.courses[idx]["prerequisites"] = [bundle.courses[self.rng.randint(idx + 1, self.courses_n - 1)]["code"]]

        for idx in range(self.students_n):
            bundle.students.append(
                {
                    "id": f"s{idx:05d}",
                    "student_id": f"STU{idx:05d}",
                    "name": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                    "year": self.rng.choice([1, 1, 2, 2, 3, 4]),
                    "program": self.rng.choice(DEPARTMENTS),
                    "gpa": round(self.rng.gauss(2.9, 0.6), 2),
                }
            )

        for idx in range(max(1, self.students_n // 25)):
            bundle.lecturers.append(
                {
                    "id": f"l{idx:04d}",
                    "staff_id": f"LEC{idx:04d}",
                    "name": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                    "department": self.rng.choice(DEPARTMENTS),
                    "max_hours": self.rng.choice([16, 20, 24]),
                }
            )

        for idx in range(40):
            bundle.rooms.append(
                {
                    "id": f"r{idx:03d}",
                    "room_no": f"{self.rng.choice(['A', 'B', 'C', 'D'])}{idx:03d}",
                    "capacity": self.rng.choice([30, 50, 80, 120]),
                    "kind": self.rng.choice(["classroom", "lab", "lecture hall"]),
                }
            )

        enrollment_idx = 0
        seen: set[tuple[str, str]] = set()
        for student in bundle.students:
            for _ in range(self.rng.randint(3, 6)):
                course = self.rng.choice(bundle.courses)
                if (student["id"], course["id"]) in seen:
                    continue
                seen.add((student["id"], course["id"]))
                attendance_rate = self.rng.random()
                if attendance_rate < 0.55 and student["gpa"] < 2.4:
                    pass_fail = self.rng.random() < 0.8
                elif attendance_rate > 0.85 and student["gpa"] > 3.0:
                    pass_fail = self.rng.random() < 0.1
                else:
                    pass_fail = self.rng.random() < 0.3

                grade = self.rng.choices(GRADES, weights=[30, 28, 20, 10, 6, 6])[0] if not pass_fail else "F"
                marks = _grade_to_marks(grade, self.rng)
                bundle.enrollments.append(
                    {
                        "id": f"e{enrollment_idx:06d}",
                        "student_id": student["id"],
                        "course_id": course["id"],
                        "status": "approved",
                    }
                )
                bundle.results.append(
                    {
                        "enrollment_id": f"e{enrollment_idx:06d}",
                        "marks": marks,
                        "grade": grade,
                        "semester": f"20{24 + student['year'] // 4}-S{student['year'] % 2 + 1}",
                    }
                )
                days_attended = int(round(attendance_rate * 63))
                for day_offset in range(63):
                    if day_offset < days_attended:
                        bundle.attendance.append(
                            {
                                "enrollment_id": f"e{enrollment_idx:06d}",
                                "day": date(2026, 3, 2) + timedelta(days=day_offset),
                                "status": "present",
                            }
                        )
                enrollment_idx += 1

        for idx in range(min(200, len(bundle.courses) * 5)):
            course = self.rng.choice(bundle.courses)
            bundle.timetable.append(
                {
                    "course_id": course["id"],
                    "room_id": self.rng.choice(bundle.rooms)["id"],
                    "lecturer_id": self.rng.choice(bundle.lecturers)["id"],
                    "day": self.rng.choice(["MON", "TUE", "WED", "THU", "FRI"]),
                    "start_time": time(8 + self.rng.choice([0, 2, 5, 7]), 0),
                    "end_time": time(10 + self.rng.choice([0, 2, 5, 7]), 0),
                    "term": "2026-S1",
                }
            )

        return bundle

    def insert_to_db(self, db, bundle: DatasetBundle) -> dict[str, int]:
        stats: dict[str, int] = {}

        existing_rooms = {r.room_no for r in db.query(Room).all()}
        for room in bundle.rooms:
            if room["room_no"] in existing_rooms:
                continue
            db.add(Room(room_no=room["room_no"], capacity=room["capacity"], kind=room["kind"]))
        db.flush()
        stats["rooms"] = len(bundle.rooms) - len(existing_rooms)

        existing_courses = {c.code for c in db.query(Course).all()}
        for course in bundle.courses:
            if course["code"] in existing_courses:
                continue
            db.add(
                Course(
                    code=course["code"],
                    title=course["title"],
                    credits=course["credits"],
                    capacity=course["capacity"],
                    department=course["department"],
                    prerequisites=course["prerequisites"],
                )
            )
        db.flush()
        stats["courses"] = len(bundle.courses) - len(existing_courses)

        existing_lecturers = {l.staff_id for l in db.query(Lecturer).all()}
        for lecturer in bundle.lecturers:
            if lecturer["staff_id"] in existing_lecturers:
                continue
            user = User(username=lecturer["staff_id"], password_hash=hash_password("lecturer123"), role="lecturer", email=f"{lecturer['staff_id'].lower()}@beru.edu")
            db.add(user)
            db.flush()
            db.add(Lecturer(user_id=user.id, staff_id=lecturer["staff_id"], department=lecturer["department"], max_hours=lecturer["max_hours"]))
        stats["lecturers"] = len(bundle.lecturers) - len(existing_lecturers)

        existing_students = {s.student_id: s.id for s in db.query(Student).all()}
        student_ids: dict[str, str] = {}
        for student in bundle.students:
            if student["student_id"] in existing_students:
                student_ids[student["id"]] = existing_students[student["student_id"]]
                continue
            user = User(username=student["student_id"], password_hash=hash_password("student123"), role="student", email=f"{student['student_id'].lower()}@beru.edu")
            db.add(user)
            db.flush()
            stu = Student(user_id=user.id, student_id=student["student_id"], year=student["year"], program=student["program"], gpa=student["gpa"])
            db.add(stu)
            db.flush()
            student_ids[student["id"]] = stu.id
        stats["students"] = len(bundle.students) - len(existing_students)

        enrollment_ids: dict[str, str] = {}
        new_enrollment_ids: set[str] = set()
        new_enrollments = 0
        for enrollment in bundle.enrollments:
            course = db.query(Course).filter(Course.code == _course_code_by_id(bundle, enrollment["course_id"])).one()
            student_db_id = student_ids[enrollment["student_id"]]
            existing = db.query(Enrollment).filter(
                Enrollment.student_id == student_db_id, Enrollment.course_id == course.id
            ).first()
            if existing is not None:
                enrollment_ids[enrollment["id"]] = existing.id
                continue
            enr = Enrollment(
                student_id=student_db_id,
                course_id=course.id,
                status=enrollment["status"],
            )
            db.add(enr)
            db.flush()
            enrollment_ids[enrollment["id"]] = enr.id
            new_enrollment_ids.add(enrollment["id"])
            new_enrollments += 1
        stats["enrollments"] = new_enrollments

        added_results = 0
        for result in bundle.results:
            if result["enrollment_id"] not in new_enrollment_ids:
                continue
            db.add(
                Result(
                    enrollment_id=enrollment_ids[result["enrollment_id"]],
                    marks=result["marks"],
                    grade=result["grade"],
                    semester=result["semester"],
                )
            )
            added_results += 1
        added_attendance = 0
        for record in bundle.attendance:
            if record["enrollment_id"] not in new_enrollment_ids:
                continue
            db.add(
                AttendanceRecord(
                    enrollment_id=enrollment_ids[record["enrollment_id"]],
                    day=record["day"],
                    status=record["status"],
                )
            )
            added_attendance += 1
        stats["results"] = added_results
        stats["attendance"] = added_attendance

        lecturer_map = {l.staff_id: l.id for l in db.query(Lecturer).all()}
        room_map = {r.room_no: r.id for r in db.query(Room).all()}
        added_timetable = 0
        for entry in bundle.timetable:
            course = db.query(Course).filter(Course.code == _course_code_by_id(bundle, entry["course_id"])).one()
            room_db_id = room_map[_room_no_by_id(bundle, entry["room_id"])]
            lecturer_db_id = lecturer_map[_staff_id_by_id(bundle, entry["lecturer_id"])]
            duplicate = db.query(TimetableEntry).filter(
                TimetableEntry.course_id == course.id,
                TimetableEntry.room_id == room_db_id,
                TimetableEntry.lecturer_id == lecturer_db_id,
                TimetableEntry.day == entry["day"],
                TimetableEntry.start_time == entry["start_time"],
            ).first()
            if duplicate is not None:
                continue
            db.add(
                TimetableEntry(
                    course_id=course.id,
                    room_id=room_db_id,
                    lecturer_id=lecturer_db_id,
                    day=entry["day"],
                    start_time=entry["start_time"],
                    end_time=entry["end_time"],
                    term=entry["term"],
                )
            )
            added_timetable += 1
        stats["timetable"] = added_timetable

        db.commit()
        return stats


def _course_code_by_id(bundle: DatasetBundle, course_id: str) -> str:
    return next(c["code"] for c in bundle.courses if c["id"] == course_id)


def _room_no_by_id(bundle: DatasetBundle, room_id: str) -> str:
    return next(r["room_no"] for r in bundle.rooms if r["id"] == room_id)


def _staff_id_by_id(bundle: DatasetBundle, lecturer_id: str) -> str:
    return next(l["staff_id"] for l in bundle.lecturers if l["id"] == lecturer_id)


def _grade_to_marks(grade: str, rng: random.Random) -> float:
    ranges = {"A": (70, 100), "B": (60, 69), "C": (50, 59), "D": (45, 49), "E": (40, 44), "F": (0, 39)}
    lo, hi = ranges[grade]
    return round(rng.uniform(lo, hi), 1)
