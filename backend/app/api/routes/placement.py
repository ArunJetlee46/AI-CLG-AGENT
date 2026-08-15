"""Placement Copilot API."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import JobDescription, User
from app.schemas.common import (
    CompanyCreate,
    DriveCreate,
    JDAnalyzeRequest,
    JobDescriptionCreate,
    NotifyRequest,
    RoundCreate,
    SelectionCreate,
    ShortlistRequest,
)
from app.services import placement, placement_intelligence

router = APIRouter(prefix="/placement", tags=["placement"])


def _officer(user: User) -> User:
    if user.role not in ("placement", "lecturer", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Placement module requires placement-officer access")
    return user


@router.get("/overview")
def overview(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement.get_overview(db)


@router.get("/readiness")
def readiness(
    limit: int = Query(default=100, ge=1, le=1000),
    user: User = Depends(require_role("placement", "lecturer", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    _officer(user)
    return placement.get_readiness(db, limit=limit)


@router.get("/readiness/{student_id}")
def readiness_one(
    student_id: str,
    user: User = Depends(require_role("placement", "lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    _officer(user)
    rows = placement.get_readiness(db, student_id=student_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return rows[0]


@router.get("/at-risk")
def at_risk(
    limit: int = Query(default=50, ge=1, le=1000),
    user: User = Depends(require_role("placement", "lecturer", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    _officer(user)
    return placement.get_at_risk(db, limit=limit)


@router.post("/shortlist")
def shortlist(
    body: ShortlistRequest,
    user: User = Depends(require_role("placement", "lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    _officer(user)
    return placement.shortlist(
        db,
        role=body.role,
        min_gpa=body.min_gpa,
        max_backlogs=body.max_backlogs,
        required_skills=body.required_skills,
        limit=body.limit,
    )


@router.get("/report")
def report(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement.get_report(db)


# ---------------------------------------------------------------------------
# Placement flow + intelligence (analytical batch)
# ---------------------------------------------------------------------------
@router.get("/flow-status")
def flow_status(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_flow_status(db)


@router.post("/jd/analyze")
def jd_analyze(body: JDAnalyzeRequest, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.analyze_jd_text(db, body.text)


@router.post("/companies")
def company_create(body: CompanyCreate, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.create_company(
        db, name=body.name, sector=body.sector, location=body.location,
        contact_email=body.contact_email, contact_phone=body.contact_phone, notes=body.notes, actor=user.username,
    )


@router.get("/companies")
def companies(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    _officer(user)
    return placement_intelligence.get_companies(db)


@router.post("/jd")
def jd_create(body: JobDescriptionCreate, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.create_jd(
        db, company_id=body.company_id, title=body.title, raw_text=body.raw_text,
        min_gpa=body.min_gpa, max_backlogs=body.max_backlogs, ctc_min=body.ctc_min,
        ctc_max=body.ctc_max, openings=body.openings, actor=user.username,
    )


@router.get("/jd")
def jds(company_id: str | None = None, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    _officer(user)
    return placement_intelligence.get_jds(db, company_id=company_id)


@router.get("/matching/{jd_id}")
def matching(jd_id: str, limit: int = Query(default=100, ge=1, le=1000),
             user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    jd = db.execute(select(JobDescription).where(JobDescription.id == jd_id)).scalar_one_or_none()
    if jd is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    return placement_intelligence.match_for_jd(db, jd, limit=limit)


@router.post("/drives")
def drive_create(body: DriveCreate, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.create_drive(
        db, title=body.title, company_id=body.company_id, jd_id=body.jd_id,
        drive_date=body.drive_date, mode=body.mode, location=body.location, actor=user.username,
    )


@router.get("/drives")
def drives(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    _officer(user)
    return placement_intelligence.get_drives(db)


@router.post("/drives/{drive_id}/rounds")
def round_create(drive_id: str, body: RoundCreate, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    if body.drive_id != drive_id:
        raise HTTPException(status_code=400, detail="drive id mismatch")
    return placement_intelligence.add_round(
        db, drive_id=drive_id, name=body.name, round_order=body.round_order,
        round_date=body.round_date, actor=user.username,
    )


@router.post("/drives/{drive_id}/notify")
def notify(drive_id: str, body: NotifyRequest, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    if body.drive_id != drive_id:
        raise HTTPException(status_code=400, detail="drive id mismatch")
    return placement_intelligence.notify_students(
        db, drive_id=drive_id, student_ids=body.student_ids, actor=user.username,
    )


@router.get("/drives/{drive_id}/pipeline")
def pipeline(drive_id: str, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_pipeline(db, drive_id)


@router.post("/selections")
def selection_create(body: SelectionCreate, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.record_selection(
        db, drive_id=body.drive_id, student_id=body.student_id, round_reached=body.round_reached,
        offered_ctc=body.offered_ctc, offer_status=body.offer_status, actor=user.username,
    )


@router.get("/funnel")
def funnel(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_funnel(db)


@router.get("/salary")
def salary(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_salary_analytics(db)


@router.get("/skill-demand")
def skill_demand(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_skill_demand(db)


@router.get("/gaps")
def gaps(student_id: str | None = None, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_gap_analysis(db, student_id=student_id)


@router.get("/training")
def training(limit: int = Query(default=50, ge=1, le=500),
             user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    _officer(user)
    return placement_intelligence.get_training_plans(db, limit=limit)


@router.get("/analytics/coding")
def coding_analytics(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_coding_analytics(db)


@router.get("/analytics/aptitude")
def aptitude_analytics(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_aptitude_analytics(db)


@router.get("/analytics/communication")
def communication_analytics(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_communication_analytics(db)


@router.get("/departments")
def departments(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_department_comparison(db)


@router.get("/prediction")
def prediction(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_placement_prediction(db)


@router.get("/notifications")
def notifications(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_notifications(db)


@router.post("/notifications/{notification_id}/read")
def notification_read(notification_id: str, user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    try:
        return placement_intelligence.mark_notification_read(db, notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/report/full")
def full_report(user: User = Depends(require_role("placement", "lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    _officer(user)
    return placement_intelligence.get_reports(db)
