"""Placement Copilot API."""
import csv
import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import JobDescription, User
from app.schemas.placement import (
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


@router.post("/import/preview")
async def import_preview(
    import_type: str = Query(..., pattern=r"^(companies|jds|drives|selections)$"),
    file: UploadFile = File(...),
    user: User = Depends(require_role("placement", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Preview first 10 rows of a CSV import with validation."""
    _officer(user)
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")

    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    errors = []
    for i, row in enumerate(reader):
        if i >= 500:
            break
        row_errors = _validate_csv_row(import_type, row)
        if row_errors:
            errors.append({"row": i + 2, "errors": row_errors})
        if i < 10:
            rows.append(row)

    return {
        "import_type": import_type,
        "filename": file.filename,
        "total_rows": min(i + 1, 500) if i < 500 else "500+",
        "preview": rows,
        "validation_errors": errors[:20],
        "error_count": len(errors),
        "can_import": len(errors) == 0,
    }


@router.post("/import/confirm")
async def import_confirm(
    import_type: str = Query(..., pattern=r"^(companies|jds|drives|selections)$"),
    file: UploadFile = File(...),
    user: User = Depends(require_role("placement", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Execute a CSV import after preview validation."""
    _officer(user)
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")

    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    skipped = 0
    for i, row in enumerate(reader):
        try:
            _import_csv_row(db, import_type, row, user.username)
            imported += 1
        except (ValueError, KeyError):
            skipped += 1

    db.commit()
    return {
        "import_type": import_type,
        "imported": imported,
        "skipped": skipped,
        "message": f"Imported {imported} rows, skipped {skipped}.",
    }


def _validate_csv_row(import_type: str, row: dict) -> list[str]:
    """Validate a single CSV row. Returns list of error messages."""
    errors = []
    if import_type == "companies":
        if not row.get("name", "").strip():
            errors.append("name is required")
    elif import_type == "jds":
        if not row.get("company_name", "").strip() and not row.get("company_id", "").strip():
            errors.append("company_name or company_id is required")
        if not row.get("title", "").strip():
            errors.append("title is required")
    elif import_type == "drives":
        if not row.get("title", "").strip():
            errors.append("title is required")
        if not row.get("company_name", "").strip() and not row.get("company_id", "").strip():
            errors.append("company_name or company_id is required")
        if not row.get("drive_date", "").strip():
            errors.append("drive_date is required")
    elif import_type == "selections":
        if not row.get("student_id", "").strip():
            errors.append("student_id is required")
        if not row.get("company_name", "").strip() and not row.get("drive_id", "").strip():
            errors.append("company_name or drive_id is required")
    return errors


def _import_csv_row(db: Session, import_type: str, row: dict, actor: str) -> None:
    """Import a single CSV row into the database."""
    from app.models.entities import Company, JobDescription, PlacementDrive, PlacementSelection, Student

    if import_type == "companies":
        name = row["name"].strip()
        existing = db.execute(select(Company).where(Company.name == name)).scalar_one_or_none()
        if existing:
            raise ValueError(f"Company {name} already exists")
        company = Company(
            name=name,
            sector=row.get("sector", "").strip(),
            location=row.get("location", "").strip(),
            contact_email=row.get("contact_email", "").strip(),
            contact_phone=row.get("contact_phone", "").strip(),
            notes=row.get("notes", "").strip(),
        )
        db.add(company)
        db.flush()

    elif import_type == "jds":
        company_name = row.get("company_name", "").strip()
        company = None
        if company_name:
            company = db.execute(select(Company).where(Company.name == company_name)).scalar_one_or_none()
        if company is None:
            company_id = row.get("company_id", "").strip()
            if company_id:
                company = db.execute(select(Company).where(Company.id == company_id)).scalar_one_or_none()
        if company is None:
            raise ValueError(f"Company not found: {company_name or row.get('company_id', '')}")

        def _parse_float(val, default=0.0):
            try:
                return float(str(val).strip().split()[0]) if val and str(val).strip() else default
            except (ValueError, IndexError):
                return default

        jd = JobDescription(
            company_id=company.id,
            title=row["title"].strip(),
            raw_text=row.get("raw_text", ""),
            skills=[s.strip() for s in row.get("skills", "").split(",") if s.strip()],
            role_type=row.get("role_type", "software").strip(),
            min_gpa=_parse_float(row.get("min_gpa"), 2.5),
            max_backlogs=int(_parse_float(row.get("max_backlogs"), 0)),
            ctc_min=_parse_float(row.get("ctc_min")),
            ctc_max=_parse_float(row.get("ctc_max")),
            openings=int(_parse_float(row.get("openings"), 1)),
            location=row.get("location", "").strip(),
            mode=row.get("mode", "onsite").strip(),
        )
        db.add(jd)
        db.flush()

    elif import_type == "drives":
        company_name = row.get("company_name", "").strip()
        company = None
        if company_name:
            company = db.execute(select(Company).where(Company.name == company_name)).scalar_one_or_none()
        if company is None:
            company_id = row.get("company_id", "").strip()
            if company_id:
                company = db.execute(select(Company).where(Company.id == company_id)).scalar_one_or_none()
        if company is None:
            raise ValueError(f"Company not found: {company_name or row.get('company_id', '')}")

        from datetime import date as _date
        try:
            drive_date = _date.fromisoformat(row["drive_date"].strip())
        except (ValueError, KeyError):
            raise ValueError(f"Invalid drive_date: {row.get('drive_date', '')}")

        jd_id = None
        jd_title = row.get("jd_title", "").strip()
        if jd_title:
            jd = db.execute(
                select(JobDescription).where(JobDescription.title == jd_title, JobDescription.company_id == company.id)
            ).scalar_one_or_none()
            if jd:
                jd_id = jd.id

        drive = PlacementDrive(
            title=row["title"].strip(),
            company_id=company.id,
            jd_id=jd_id,
            drive_date=drive_date,
            mode=row.get("mode", "online").strip(),
            location=row.get("location", "").strip(),
            status=row.get("status", "scheduled").strip(),
        )
        db.add(drive)
        db.flush()

    elif import_type == "selections":
        student_id = row["student_id"].strip()
        student = db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()
        if student is None:
            raise ValueError(f"Student not found: {student_id}")

        drive_id = row.get("drive_id", "").strip()
        if not drive_id:
            company_name = row.get("company_name", "").strip()
            if company_name:
                company = db.execute(select(Company).where(Company.name == company_name)).scalar_one_or_none()
                if company:
                    drives = db.execute(
                        select(PlacementDrive).where(PlacementDrive.company_id == company.id).order_by(PlacementDrive.drive_date.desc())
                    ).scalars().all()
                    if drives:
                        drive_id = drives[0].id
        if not drive_id:
            raise ValueError(f"Drive not found for student {student_id}")

        def _parse_float2(val, default=0.0):
            try:
                return float(str(val).strip().split()[0]) if val and str(val).strip() else default
            except (ValueError, IndexError):
                return default

        sel = PlacementSelection(
            drive_id=drive_id,
            student_id=student.id,
            round_reached=row.get("round_reached", "final").strip(),
            offered_ctc=_parse_float2(row.get("offered_ctc")),
            offer_status=row.get("offer_status", "offered").strip(),
        )
        db.add(sel)
        db.flush()
