"""RAG backfill: render the institution's actual database rows into grounded
documents and push them through the ingest pipeline (chunk -> embed -> vector
store + keyword index). This is what lets the assistant answer questions about
*real* courses, lecturers, rooms, placements and announcements instead of only
the static KB corpus.

Works over any SQLAlchemy dialect (SQLite in development, Postgres in
production). Student rows are only ever summarized in aggregate - never
individually - to keep personal data out of the retrieval corpus.
"""
import json
import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
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
    TimetableEntry,
    User,
)
from app.services.rag.pipeline import ingest_documents

logger = logging.getLogger(__name__)
settings = get_settings()

SOURCE = "database"


def build_db_documents(db: Session) -> list[dict]:
    """Render database rows into ingestable documents (no personal data)."""
    docs: list[dict] = []

    for course in db.execute(select(Course).order_by(Course.code)).scalars():
        prereqs = ", ".join(course.prerequisites) if course.prerequisites else "none"
        docs.append(
            {
                "id": f"course:{course.code}",
                "source": SOURCE,
                "title": f"Course {course.code} - {course.title}",
                "text": (
                    f"Course {course.code}: {course.title}. Department: {course.department}. "
                    f"Credits: {course.credits}. Capacity: {course.capacity} students. "
                    f"Prerequisites: {prereqs}."
                ),
            }
        )

    rows = db.execute(select(Lecturer, User).join(User, Lecturer.user_id == User.id)).all()
    for lecturer, user in rows:
        name = (user.username or "").strip() or lecturer.staff_id
        docs.append(
            {
                "id": f"lecturer:{lecturer.staff_id}",
                "source": SOURCE,
                "title": f"Lecturer {name}",
                "text": (
                    f"Lecturer {name} (staff id {lecturer.staff_id}) is in the "
                    f"{lecturer.department} department. Max weekly teaching hours: {lecturer.max_hours}."
                ),
            }
        )

    for room in db.execute(select(Room).order_by(Room.room_no)).scalars():
        docs.append(
            {
                "id": f"room:{room.room_no}",
                "source": SOURCE,
                "title": f"Room {room.room_no}",
                "text": (
                    f"Room {room.room_no} is a {room.kind} with capacity for {room.capacity} people."
                ),
            }
        )

    for company in db.execute(select(Company).order_by(Company.name)).scalars():
        docs.append(
            {
                "id": f"company:{company.name}",
                "source": SOURCE,
                "title": f"Company {company.name}",
                "text": (
                    f"Company {company.name} operates in the {company.sector} sector, "
                    f"located in {company.location}. Notes: {company.notes or 'n/a'}."
                ),
            }
        )

    for drive in db.execute(select(PlacementDrive).order_by(PlacementDrive.drive_date)).scalars():
        company_name = drive.company.name if drive.company is not None else "a partner company"
        docs.append(
            {
                "id": f"placement-drive:{drive.id}",
                "source": SOURCE,
                "title": f"Placement drive {drive.title}",
                "text": (
                    f"Placement drive {drive.title} with {company_name} on {drive.drive_date} "
                    f"({drive.mode}) in {drive.location or 'on campus'}. Status: {drive.status}."
                ),
            }
        )

    for resource in db.execute(select(CampusResource).order_by(CampusResource.name)).scalars():
        docs.append(
            {
                "id": f"resource:{resource.id}",
                "source": SOURCE,
                "title": f"Campus resource {resource.name}",
                "text": (
                    f"Campus resource: {resource.name} ({resource.resource_type}), capacity "
                    f"{resource.capacity}, located at {resource.location}. Status: {resource.status}. "
                    f"Notes: {resource.notes or 'n/a'}."
                ),
            }
        )

    for announcement in db.execute(
        select(Announcement).order_by(Announcement.created_at.desc()).limit(50)
    ).scalars():
        docs.append(
            {
                "id": f"announcement:{announcement.id}",
                "source": SOURCE,
                "title": f"Announcement: {announcement.title}",
                "text": f"Announcement: {announcement.title}. {announcement.body}",
            }
        )

    for project in db.execute(select(ResearchProject).order_by(ResearchProject.title)).scalars():
        docs.append(
            {
                "id": f"research:{project.id}",
                "source": SOURCE,
                "title": f"Research project: {project.title}",
                "text": (
                    f"Research project: {project.title}, led by {project.lead_name} in the "
                    f"{project.department} department. Status: {project.status}. Funding: "
                    f"{project.funding_amount} FCFA. Publications: {project.publications}."
                ),
            }
        )

    for partner in db.execute(select(IndustryPartner).order_by(IndustryPartner.name)).scalars():
        docs.append(
            {
                "id": f"industry:{partner.name}",
                "source": SOURCE,
                "title": f"Industry partner {partner.name}",
                "text": (
                    f"Industry partner: {partner.name} in the {partner.sector} sector. "
                    f"Contact person: {partner.contact_person}. Active: {partner.active}. "
                    f"Placement hires to date: {partner.placement_hires}."
                ),
            }
        )

    docs.append(_student_aggregate_doc(db))
    return docs


def _student_aggregate_doc(db: Session) -> dict:
    """Aggregate-only student summary; individual student rows never enter RAG."""
    total = db.execute(select(func.count(Student.id))).scalar_one()
    programs = db.execute(
        select(Student.program, func.count(Student.id)).group_by(Student.program).order_by(Student.program)
    ).all()
    avg_gpa = db.execute(select(func.avg(Student.gpa))).scalar_one()
    program_lines = "; ".join(f"{p}: {c}" for p, c in programs) if programs else "n/a"
    return {
        "id": "students:aggregate",
        "source": SOURCE,
        "title": "Student population summary",
        "text": (
            f"The institution has {total} enrolled students across {len(programs)} programme(s). "
            f"Programme counts: {program_lines}. Average GPA: {avg_gpa:.2f}."
        ),
    }


def render_documents_to_jsonl(docs: list[dict], path: Path) -> int:
    """Persist the corpus in the same *_rag.jsonl shape the boot loader reads
    ({id, source, document, content}), so a restart rebuilds the keyword index
    without re-reading the database."""
    written = 0
    with path.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(
                json.dumps(
                    {
                        "id": doc["id"],
                        "source": doc.get("source", SOURCE),
                        "document": doc["title"],
                        "content": doc["text"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


def backfill_from_db(db: Session | None = None, *, persist_file: bool = True) -> dict:
    """Backfill the RAG corpus from the database. Idempotent (chunks already
    embedded are skipped by the ingest pipeline). Returns stats."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        docs = build_db_documents(db)
    finally:
        if own_session:
            db.close()
    stats = ingest_documents(docs)
    stats["docs"] = len(docs)

    if persist_file:
        data_dir = Path(settings.knowledge_data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        target = data_dir / "database_rag.jsonl"
        written = render_documents_to_jsonl(docs, target)
        stats["jsonl_written"] = written
        logger.info("database RAG backfill: %d docs, %d chunks, %d vector upserts, wrote %s",
                    stats["docs"], stats["chunks"], stats["vector_upserts"], target)
    return stats
