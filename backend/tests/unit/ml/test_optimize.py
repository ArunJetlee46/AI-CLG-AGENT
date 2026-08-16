import pytest

from app.db import SessionLocal
from app.ml.optimize import build_input, solve_timetable
from app.models.entities import Course, Room, TimetableEntry
from synthetic.generator import SyntheticDataGenerator


@pytest.fixture(scope="module")
def seeded_db():
    generator = SyntheticDataGenerator(students=30, courses=12, seed=11)
    bundle = generator.generate()
    db = SessionLocal()
    try:
        generator.insert_to_db(db, bundle)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        for table in ("timetable_entries", "attendance", "results", "enrollments", "courses",
                      "lecturers", "students", "rooms", "users"):
            db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
        db.commit()
    finally:
        db.close()


def _report(db):
    return solve_timetable(db)


def _assert_hard_constraints_hold(db, entries) -> None:
    by_room_slot: dict[tuple[str, str, str], int] = {}
    by_lecturer_slot: dict[tuple[str, str, str], int] = {}
    course_ids: set[str] = set()
    rooms = {r.id: r for r in db.execute(__import__("sqlalchemy").select(Room)).scalars()}
    courses = {c.id: c for c in db.execute(__import__("sqlalchemy").select(Course)).scalars()}

    for e in entries:
        assert e["course_id"] not in course_ids, f"course scheduled twice: {e['course_id']}"
        course_ids.add(e["course_id"])
        room = rooms[e["room_id"]]
        assert room.capacity >= courses[e["course_id"]].capacity, "H3 room capacity violated"
        assert not (room.kind != "lab" and "lab" in courses[e["course_id"]].title.lower()), "H4 lab constraint violated"

        key_room = (e["room_id"], e["day"], e["start"])
        assert by_room_slot.get(key_room, 0) == 0, "H2 room unary violated"
        by_room_slot[key_room] = 1

        if e.get("lecturer_id"):
            key_lec = (e["lecturer_id"], e["day"], e["start"])
            assert by_lecturer_slot.get(key_lec, 0) == 0, "H5 faculty unary violated"
            by_lecturer_slot[key_lec] = 1


def test_heuristic_schedules_all_without_conflicts(seeded_db) -> None:
    db = SessionLocal()
    try:
        report = solve_timetable(db)
        assert report["status"] in ("OPTIMAL", "FEASIBLE", "heuristic")
        assert report["conflicts"] == 0, f"unscheduled: {report['unscheduled']}"
        assert report["scheduled"] == report["courses"]
        assert report["slots"] == 20
        _assert_hard_constraints_hold(db, report["entries"])
    finally:
        db.close()


def test_commit_persists_entries(seeded_db) -> None:
    db = SessionLocal()
    try:
        from app.models.entities import ApprovalRequest

        approval = ApprovalRequest(
            intent="apply_timetable",
            payload={"action": "apply_timetable", "term": "2026-S2"},
            user_id="",
            status="approved",
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        report = solve_timetable(db, approval_id=approval.id, term="2026-S2")
        assert report["scheduled"] == report["courses"]
        entries = db.execute(__import__("sqlalchemy").select(TimetableEntry)).scalars().all()
        assert len(entries) == len(db.execute(__import__("sqlalchemy").select(Course)).scalars().all())
        assert all(e.term == "2026-S2" for e in entries)
    finally:
        db.close()


def test_commit_without_approval_is_rejected_and_writes_nothing(seeded_db) -> None:
    from app.core.approvals import ApprovalRequiredError

    db = SessionLocal()
    try:
        before = db.execute(__import__("sqlalchemy").select(TimetableEntry)).scalars().all()
        with pytest.raises(ApprovalRequiredError):
            solve_timetable(db, approval_id="missing", term="2026-S3")
        assert len(db.execute(__import__("sqlalchemy").select(TimetableEntry)).scalars().all()) == len(before)
    finally:
        db.close()


def test_build_input_maps_lecturers(seeded_db) -> None:
    db = SessionLocal()
    try:
        inp = build_input(db)
        assert inp.courses
        assert inp.rooms
        assert all(c["id"] in inp.lecturer_of for c in inp.courses)
    finally:
        db.close()


def test_room_capacity_enforced_by_construction(seeded_db) -> None:
    """A course bigger than every room must be reported unscheduled, not forced."""
    db = SessionLocal()
    try:
        course = db.execute(__import__("sqlalchemy").select(Course)).scalars().first()
        course.capacity = 10_000  # bigger than any room
        db.commit()
        report = solve_timetable(db)
        assert report["conflicts"] >= 1
        assert course.id in report["unscheduled"]
    finally:
        db.close()
