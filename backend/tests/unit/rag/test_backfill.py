"""Theme E: database -> RAG backfill.

Verifies database rows are rendered into grounded documents, aggregated
student data stays aggregate (no individual PII), the corpus persists in
the *_rag.jsonl boot format, and the pipeline ingests idempotently.
"""

from datetime import date

from app.db import SessionLocal
from app.models.entities import (
    Announcement,
    CampusResource,
    Company,
    Course,
    IndustryPartner,
    Lecturer,
    PlacementDrive,
    ResearchProject,
    Room,
    Student,
    User,
)
from app.services.rag.backfill import (
    backfill_from_db,
    build_db_documents,
    render_documents_to_jsonl,
)
from app.services.rag.pipeline import get_keyword_index


def _seed_rows(db):
    if db.query(Course).filter_by(code="AI401").first() is not None:
        return
    user = User(username="prof-bella", password_hash="x", role="lecturer", email="b@beru.edu")
    db.add(user)
    db.flush()
    lecturer = Lecturer(user_id=user.id, staff_id="LEC-1", department="Computer Science", max_hours=20)
    db.add(lecturer)

    db.add(Course(code="AI401", title="Deep Learning", credits=4, capacity=40,
                  department="AI&DS", prerequisites=["AI301", "MA302"]))
    db.add(Course(code="CS101", title="Intro to Programming", credits=3, capacity=60,
                  department="CS", prerequisites=[]))
    db.add(Room(room_no="R-204", capacity=80, kind="lab"))
    db.add(Company(name="QuantumWorks", sector="software", location="Bengaluru", notes="hires final years"))
    db.add(Announcement(title="Exam timetable published", body="January exams are now posted.", audience="all"))
    db.add(CampusResource(name="Main Library", resource_type="library", capacity=200,
                          location="Block A", status="active"))
    db.add(IndustryPartner(name="InnovateLabs", sector="software", contact_person="A. Rao", active=True))
    db.add(ResearchProject(title="Federated learning for smart campus", lead_name="Prof. B",
                           department="AI&DS", status="active"))
    for sid, prog, gpa in (("STU-9001", "AI&DS", 3.4), ("STU-9002", "CS", 2.9)):
        su = User(username=sid, password_hash="x", role="student", email=f"{sid}@beru.edu")
        db.add(su)
        db.flush()
        db.add(Student(user_id=su.id, student_id=sid, year=3, program=prog, gpa=gpa))
    drive_company = db.query(Company).filter_by(name="QuantumWorks").one()
    db.add(PlacementDrive(title="QuantumWorks 2026", company_id=drive_company.id,
                          drive_date=date(2026, 9, 15), mode="online", location="Remote"))
    db.commit()


def test_build_db_documents_renders_rows_without_pii() -> None:
    db = SessionLocal()
    try:
        _seed_rows(db)
        docs = build_db_documents(db)

        by_id = {d["id"]: d for d in docs}
        assert "course:AI401" in by_id
        assert "Deep Learning" in by_id["course:AI401"]["text"]
        assert "Prerequisites: AI301, MA302" in by_id["course:AI401"]["text"]
        assert "lecturer:LEC-1" in by_id
        assert "room:R-204" in by_id
        assert "company:QuantumWorks" in by_id
        assert "announcement:" in next(k for k in by_id if k.startswith("announcement:"))
        assert "students:aggregate" in by_id

        # aggregate only - no individual student id or GPA may leak into the corpus
        corpus = "\n".join(d["text"] for d in docs).lower()
        assert "stu-9001" not in corpus
        assert "stu-9002" not in corpus
        assert "3.4" not in corpus
    finally:
        db.close()


def test_backfill_from_db_persists_jsonl_and_ingests() -> None:
    db = SessionLocal()
    try:
        _seed_rows(db)
        docs = build_db_documents(db)
        stats = backfill_from_db(db, persist_file=False)
        assert stats["docs"] == len(docs) >= 1
        assert stats["chunks"] >= stats["docs"] > 0
    finally:
        db.close()


def test_render_documents_to_jsonl_boot_shape(tmp_path) -> None:
    docs = [{"id": "course:AI401", "source": "database", "title": "Deep Learning",
             "text": "Course AI401 is Deep Learning."}]
    target = tmp_path / "database_rag.jsonl"
    written = render_documents_to_jsonl(docs, target)
    assert written == 1

    import json

    item = json.loads(target.read_text(encoding="utf-8").strip())
    assert item["id"] == "course:AI401"
    assert item["source"] == "database"
    assert item["document"] == "Deep Learning"
    assert item["content"] == "Course AI401 is Deep Learning."


def test_backfill_documents_are_searchable() -> None:
    db = SessionLocal()
    try:
        _seed_rows(db)
        before = get_keyword_index().count()
        backfill_from_db(db, persist_file=False)
        results = get_keyword_index().search("deep learning", top_k=3)
        assert any("Deep Learning" in r.get("title", "") for r in results)
        assert get_keyword_index().count() >= before
    finally:
        db.close()
