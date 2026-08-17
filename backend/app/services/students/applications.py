"""Student-facing placement services: self-apply, withdraw, offer workflow, resume upload."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Company,
    PlacementApplication,
    PlacementDrive,
    PlacementNotification,
    PlacementSelection,
    Student,
    StudentResume,
    User,
)
from app.services import placement
from app.services.email import application_status_email, offer_email

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _drive_info(drive: PlacementDrive | None, company: Company | None) -> dict:
    if drive is None:
        return {"id": None, "title": None, "company": None, "drive_date": None,
                "mode": None, "location": None, "status": None}
    return {
        "id": drive.id,
        "title": drive.title,
        "company": company.name if company else None,
        "company_id": drive.company_id,
        "drive_date": drive.drive_date.isoformat() if drive.drive_date else None,
        "mode": drive.mode,
        "location": drive.location,
        "status": drive.status,
    }


def get_placements(db: Session, student: Student) -> dict:
    """Full student placement hub: readiness, shortlists, drives, applications, offers, resume."""
    # 1. Readiness
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

    # 2. Shortlist notifications
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

    # 3. Applications (student's own applications)
    app_rows = db.execute(
        select(PlacementApplication, PlacementDrive, Company)
        .outerjoin(PlacementDrive, PlacementApplication.drive_id == PlacementDrive.id)
        .outerjoin(Company, PlacementDrive.company_id == Company.id)
        .where(PlacementApplication.student_id == student.id)
        .order_by(PlacementApplication.applied_at.desc())
    ).all()
    applications = []
    for app, drive, company in app_rows:
        applications.append({
            "id": app.id,
            "drive_id": app.drive_id,
            "status": app.status,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "drive": _drive_info(drive, company),
        })

    # 4. Open drives (not yet applied to)
    applied_drive_ids = {a.drive_id for a, _, _ in app_rows}
    all_open_drives = db.execute(
        select(PlacementDrive, Company)
        .join(Company, PlacementDrive.company_id == Company.id)
        .where(PlacementDrive.status == "scheduled")
        .order_by(PlacementDrive.drive_date)
    ).all()
    open_drives = []
    for drive, company in all_open_drives:
        open_drives.append({
            **_drive_info(drive, company),
            "applied": drive.id in applied_drive_ids,
            "notified": drive.id in notified_drive_ids,
        })

    # 5. Offers (accepted/rejected by student)
    offer_rows = db.execute(
        select(PlacementSelection, PlacementDrive, Company)
        .outerjoin(PlacementDrive, PlacementSelection.drive_id == PlacementDrive.id)
        .outerjoin(Company, PlacementDrive.company_id == Company.id)
        .where(PlacementSelection.student_id == student.id)
        .order_by(PlacementSelection.created_at.desc())
    ).all()
    offers = []
    for sel, drive, company in offer_rows:
        offers.append({
            "id": sel.id,
            "drive_id": sel.drive_id,
            "round_reached": sel.round_reached,
            "offered_ctc": sel.offered_ctc,
            "offer_status": sel.offer_status,
            "decided_at": sel.decided_at.isoformat() if sel.decided_at else None,
            "created_at": sel.created_at.isoformat() if sel.created_at else None,
            "drive": _drive_info(drive, company),
        })

    # 6. Resume status
    resume_row = db.execute(
        select(StudentResume).where(StudentResume.student_id == student.id)
    ).scalar_one_or_none()
    resume = None
    if resume_row:
        resume = {
            "id": resume_row.id,
            "filename": resume_row.original_filename,
            "skills": resume_row.skills,
            "uploaded_at": resume_row.uploaded_at.isoformat() if resume_row.uploaded_at else None,
        }

    return {
        "student_id": student.student_id,
        "method": "placement-v2",
        "readiness": readiness,
        "shortlists": shortlists,
        "open_drives": open_drives,
        "applications": applications,
        "offers": offers,
        "resume": resume,
        "note": "Readiness is computed from academic signals plus the ML placement model.",
    }


def apply_to_drive(db: Session, student: Student, drive_id: str) -> dict:
    """Student applies to an open placement drive."""
    # Check drive exists and is scheduled
    drive = db.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id)).scalar_one_or_none()
    if drive is None:
        raise ValueError("Drive not found")
    if drive.status != "scheduled":
        raise ValueError("Drive is not open for applications")

    # Check not already applied
    existing = db.execute(
        select(PlacementApplication)
        .where(PlacementApplication.student_id == student.id, PlacementApplication.drive_id == drive_id)
    ).scalar_one_or_none()
    if existing and existing.status != "withdrawn":
        raise ValueError("Already applied to this drive")

    # Check JD eligibility if available
    if drive.jd:
        jd = drive.jd
        readiness = placement.get_readiness(db, student_id=student.student_id)
        if readiness:
            r = readiness[0]
            if r.get("gpa", 0) < jd.min_gpa and jd.min_gpa > 0:
                raise ValueError(f"GPA {r['gpa']:.2f} below minimum {jd.min_gpa}")
            if r.get("backlogs", 0) > jd.max_backlogs:
                raise ValueError(f"Backlogs exceed maximum {jd.max_backlogs}")

    if existing and existing.status == "withdrawn":
        existing.status = "applied"
        existing.applied_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        db.commit()
        return {"id": existing.id, "drive_id": drive_id, "status": "applied", "message": "Re-applied successfully"}

    app = PlacementApplication(student_id=student.id, drive_id=drive_id, status="applied")
    db.add(app)
    db.commit()
    db.refresh(app)

    # Send email notification
    company = db.execute(select(Company).where(Company.id == drive.company_id)).scalar_one_or_none()
    if student.user and student.user.email:
        application_status_email(
            student.user.email, drive.title,
            company.name if company else "Unknown", "applied",
        )

    return {"id": app.id, "drive_id": drive_id, "status": "applied", "message": "Application submitted"}


def withdraw_application(db: Session, student: Student, drive_id: str) -> dict:
    """Student withdraws an application."""
    app = db.execute(
        select(PlacementApplication)
        .where(PlacementApplication.student_id == student.id, PlacementApplication.drive_id == drive_id)
    ).scalar_one_or_none()
    if app is None:
        raise ValueError("No application found for this drive")
    if app.status == "withdrawn":
        raise ValueError("Application already withdrawn")

    app.status = "withdrawn"
    app.updated_at = datetime.utcnow()
    db.commit()
    return {"id": app.id, "drive_id": drive_id, "status": "withdrawn", "message": "Application withdrawn"}


def decide_offer(db: Session, student: Student, selection_id: str, decision: str) -> dict:
    """Student accepts or rejects a placement offer."""
    sel = db.execute(
        select(PlacementSelection)
        .where(PlacementSelection.id == selection_id, PlacementSelection.student_id == student.id)
    ).scalar_one_or_none()
    if sel is None:
        raise ValueError("Offer not found")
    if sel.offer_status not in ("offered",):
        raise ValueError(f"Cannot {decision} — current status is {sel.offer_status}")

    sel.offer_status = decision
    sel.decided_at = datetime.utcnow()
    db.commit()

    # Send email
    drive = db.execute(select(PlacementDrive).where(PlacementDrive.id == sel.drive_id)).scalar_one_or_none()
    company = None
    if drive:
        company = db.execute(select(Company).where(Company.id == drive.company_id)).scalar_one_or_none()
    if student.user and student.user.email:
        offer_email(
            student.user.email,
            company.name if company else "Unknown",
            drive.title if drive else "Unknown",
            sel.offered_ctc,
            decision,
        )

    return {
        "id": sel.id,
        "offer_status": decision,
        "decided_at": sel.decided_at.isoformat() if sel.decided_at else None,
        "message": f"Offer {decision}",
    }
