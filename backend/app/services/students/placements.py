"""Student-facing placement hub: personal readiness, shortlist notifications,
and upcoming drives the student has been notified for.

Pure reads over existing PlacementNotification / PlacementDrive / Company data.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Company, PlacementDrive, PlacementNotification, Student
from app.services import placement

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _drive_info(drive: PlacementDrive | None, company: Company | None) -> dict:
    if drive is None:
        return {"id": None, "title": None, "company": None, "drive_date": None,
                "mode": None, "location": None, "status": None}
    return {
        "id": drive.id,
        "title": drive.title,
        "company": company.name if company else None,
        "drive_date": drive.drive_date.isoformat() if drive.drive_date else None,
        "mode": drive.mode,
        "location": drive.location,
        "status": drive.status,
    }


def get_placements(db: Session, student: Student) -> dict:
    # Personal placement readiness
    readiness_rows = placement.get_readiness(db, student_id=student.student_id)
    readiness = None
    if readiness_rows:
        r = readiness_rows[0]
        readiness = {
            "student_id": r["student_id"],
            "readiness_score": r["readiness_score"],
            "band": r["band"],
            "components": [
                {"name": "academic", "score": r["components"].get("academic", 0), "weight": 0.40},
                {"name": "attendance", "score": r["components"].get("attendance", 0), "weight": 0.20},
                {"name": "aptitude", "score": r["components"].get("aptitude", 0), "weight": 0.20},
                {"name": "consistency", "score": r["components"].get("consistency", 0), "weight": 0.20},
            ],
            "placement_probability": r.get("placement_probability"),
            "drivers": r.get("drivers", []),
        }

    # Shortlist notifications for this student (with enriched drive info)
    rows = db.execute(
        select(PlacementNotification, PlacementDrive, Company)
        .outerjoin(PlacementDrive, PlacementNotification.drive_id == PlacementDrive.id)
        .outerjoin(Company, PlacementDrive.company_id == Company.id)
        .where(PlacementNotification.student_id == student.id)
        .order_by(PlacementNotification.created_at.desc())
    ).all()

    shortlists: list[dict] = []
    notified_drive_ids: set[str] = set()
    for n, drive, company in rows:
        if drive is not None:
            notified_drive_ids.add(drive.id)
        shortlists.append({
            "id": n.id,
            "drive_id": n.drive_id,
            "title": n.title,
            "body": n.body,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "drive": _drive_info(drive, company),
        })

    # Upcoming drives the student was notified about
    upcoming: list[dict] = []
    if notified_drive_ids:
        today = date.today()
        drive_rows = db.execute(
            select(PlacementDrive, Company)
            .join(Company, PlacementDrive.company_id == Company.id)
            .where(PlacementDrive.id.in_(notified_drive_ids))
            .order_by(PlacementDrive.drive_date)
        ).all()
        for drive, company in drive_rows:
            upcoming.append({
                **_drive_info(drive, company),
                "is_upcoming": (drive.drive_date or today) >= today,
            })

    return {
        "student_id": student.student_id,
        "method": "placement-v1",
        "readiness": readiness,
        "shortlists": shortlists,
        "upcoming_drives": upcoming,
        "note": "Readiness is computed from academic signals plus the ML placement model.",
    }
