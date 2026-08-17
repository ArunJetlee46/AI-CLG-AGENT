"""Placement Intelligence + Officer Copilot analytics (analytical batch).

Deterministic, explainable placement analytics and flow operations built on
the existing readiness scoring and the new placement models:

  flow_status   -> 11-stage pipeline snapshot (company..analytics)
  jd_analyzer   -> deterministic JD parser (skills, gates, ctc, role type)
  matching      -> AI job-student matching + candidate ranking (gates + score)
  funnel        -> recruitment funnel analytics
  salary        -> CTC analytics by program and sector
  skill_demand  -> in-demand skills aggregated across job descriptions
  gap_analysis  -> student skills vs required skills -> gaps + training
  training      -> personalized placement training plans for at-risk students
  coding/aptitude/communication -> per-program assessment analytics (proxies)
  companies     -> company relationship management (CRM)
  drives        -> placement drive management + recruitment rounds
  pipeline      -> per-drive recruitment pipeline
  notifications -> student notifications + mark-read
  departments   -> placement comparison across programs
  prediction    -> predicted placement rate + cohort trend
  reports       -> automated placement report

Mutations (create company / JD / drive / round / selection, notify students)
are officer-initiated writes; every one is recorded in the audit chain.
"""
import re
from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.models.entities import (
    Company,
    Course,
    Enrollment,
    JobDescription,
    PlacementDrive,
    PlacementNotification,
    PlacementSelection,
    RecruitmentRound,
    Result,
    Student,
)
from app.services.placement import AT_RISK_CUTOFF, _scored

# ---------------------------------------------------------------------------
# Skill taxonomy (deterministic keyword -> skill category)
# ---------------------------------------------------------------------------
SKILL_CATEGORIES: dict[str, list[str]] = {
    "programming": [
        "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go ",
        "kotlin", "swift", "rust", "ruby", "php", "scala", "r ",
    ],
    "web": ["react", "angular", "vue", "node", "django", "flask", "spring", "html", "css",
            "next.js", "tailwind", "rest", "graphql", "api"],
    "data": ["machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "pandas",
             "numpy", "data science", "data analysis", "excel", "power bi", "tableau",
             "big data", "spark", "hadoop", "sql", "mysql", "postgresql", "mongodb", "etl"],
    "cloud_devops": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "linux",
                     "jenkins", "ci/cd", "devops", "git"],
    "testing": ["selenium", "testing", "test automation", "junit", "pytest", "cypress"],
    "design": ["ui/ux", "figma", "photoshop", "illustrator", "wireframe", "prototype"],
    "marketing": ["seo", "content", "social media", "analytics", "campaign", "google ads"],
    "hr": ["recruitment", "talent", "hr", "onboarding", "employee engagement"],
    "soft": ["communication", "teamwork", "leadership", "problem solving", "presentation",
             "critical thinking", "time management", "adaptability", "collaboration"],
}

ROLE_BY_TYPE = {
    "programming": "software",
    "web": "software",
    "data": "data",
    "cloud_devops": "software",
    "testing": "software",
    "design": "design",
    "marketing": "marketing",
    "hr": "hr",
    "soft": "other",
}

_CTC_RE = re.compile(r"(?:ctc|package|salary|compensation)\D{0,8}?[\$₹rs\.\s]*(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*[\$₹rs\.\s]*(\d+(?:\.\d+)?)?\s*(?:lpa|cpa|inr|lakh|cr)?", re.IGNORECASE)
_CTC_RE2 = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|cpa)", re.IGNORECASE)
_SKILL_RE = re.compile(r"|".join(sorted({re.escape(kw) for kws in SKILL_CATEGORIES.values() for kw in kws}, key=len, reverse=True)), re.IGNORECASE)


def _parse_skills(text: str) -> list[str]:
    found: list[str] = []
    for m in _SKILL_RE.finditer(text):
        tok = m.group(0).strip().lower()
        if tok not in found:
            found.append(tok)
    return found


def _role_type(text: str) -> str:
    cats = [cat for cat, kws in SKILL_CATEGORIES.items() if any(re.search(rf"\b{re.escape(k.strip())}\b", text, re.IGNORECASE) or k.strip() in text.lower() for k in kws)]
    if not cats:
        return "software"
    priority = ("programming", "data", "cloud_devops", "web", "testing", "design", "marketing", "hr")
    for cat in priority:
        if cat in cats:
            return ROLE_BY_TYPE[cat]
    return ROLE_BY_TYPE[cats[0]]


def _parse_ctc(text: str) -> tuple[float, float]:
    m = _CTC_RE2.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|cpa)", text, re.IGNORECASE)
    if m:
        v = float(m.group(1))
        return v, v
    return 0.0, 0.0


def _student_skills(db: Session) -> dict[str, list[str]]:
    """student_uuid -> distinct skills from passed course titles (proxy)."""
    rows = db.execute(
        select(Enrollment.student_id, Course.title, Result.grade)
        .join(Course, Course.id == Enrollment.course_id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.status == "approved")
    ).all()
    out: dict[str, list[str]] = defaultdict(list)
    for student_uuid, title, grade in rows:
        if grade == "F" or not title:
            continue
        for skill in _parse_skills(title):
            if skill not in out[student_uuid]:
                out[student_uuid].append(skill)
    return out


def _skill_fit(student_skills: list[str], required: list[str]) -> list[str]:
    return [s for s in required if s in student_skills]


def _cohort_years(db: Session) -> dict[int, int]:
    rows = db.execute(select(Student.year, func.count()).group_by(Student.year)).all()
    return {year: count for year, count in rows}


def _selection_stats(db: Session) -> dict[str, dict]:
    rows = db.execute(
        select(Student.program, PlacementSelection.offered_ctc, PlacementSelection.offer_status)
        .join(PlacementSelection, PlacementSelection.student_id == Student.id)
    ).all()
    by_program: dict[str, list[tuple[float, str]]] = defaultdict(list)
    by_sector: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for program, ctc, status in rows:
        by_program[program].append((ctc or 0.0, status))
    sec_rows = db.execute(
        select(Company.sector, PlacementSelection.offered_ctc, PlacementSelection.offer_status)
        .select_from(PlacementDrive)
        .join(Company, Company.id == PlacementDrive.company_id)
        .join(PlacementSelection, PlacementSelection.drive_id == PlacementDrive.id)
    ).all()
    for sector, ctc, status in sec_rows:
        by_sector[sector or "unspecified"].append((ctc or 0.0, status))
    return {"by_program": by_program, "by_sector": by_sector}


def _aggregate(rows: list[tuple[float, str]]) -> dict:
    ctcs = [c for c, _ in rows if c > 0]
    if not ctcs:
        return {"count": len(rows), "avg_ctc": None, "median_ctc": None, "max_ctc": None,
                "offered": 0, "joined": 0}
    ordered = sorted(ctcs)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return {
        "count": len(rows),
        "avg_ctc": round(sum(ctcs) / n, 2),
        "median_ctc": round(median, 2),
        "max_ctc": max(ctcs),
        "offered": sum(1 for _, s in rows if s in ("offered", "accepted", "joined")),
        "joined": sum(1 for _, s in rows if s == "joined"),
    }


# ---------------------------------------------------------------------------
# Flow status (11-stage pipeline)
# ---------------------------------------------------------------------------
def get_flow_status(db: Session) -> dict:
    companies = db.execute(select(func.count(Company.id))).scalar_one()
    jds = db.execute(select(func.count(JobDescription.id))).scalar_one()
    all_jds = db.execute(select(JobDescription)).scalars().all()
    analyzed = sum(1 for jd in all_jds if jd.skills)
    scored = _scored(db)
    open_jds = db.execute(select(JobDescription).where(JobDescription.status == "open")).scalars().all()
    eligible = set()
    for jd in open_jds:
        for r in scored:
            if r["gpa"] >= jd.min_gpa and r["backlogs"] <= jd.max_backlogs and (jd.year_required == 0 or r["year"] >= jd.year_required):
                eligible.add(r["student_id"])
    matches = len(eligible) * max(1, len(open_jds)) if open_jds else 0
    reviewed = db.execute(select(func.count(PlacementDrive.id)).where(PlacementDrive.status.in_(["scheduled", "ongoing", "completed"]))).scalar_one()
    notified = db.execute(select(func.count(PlacementNotification.id))).scalar_one()
    rounds = db.execute(select(func.count(RecruitmentRound.id))).scalar_one()
    selections = db.execute(select(func.count(PlacementSelection.id))).scalar_one()

    stages = [
        ("company", "Company", companies),
        ("jd_upload", "Upload Job Description", jds),
        ("jd_analyzer", "JD Analyzer", analyzed),
        ("eligibility", "Eligibility Engine", len(eligible)),
        ("matching", "AI Candidate Matching", matches),
        ("ranking", "Candidate Ranking", matches),
        ("officer_review", "Officer Review", reviewed),
        ("notify", "Notify Students", notified),
        ("rounds", "Recruitment Rounds", rounds),
        ("selection", "Selection", selections),
        ("analytics", "Placement Analytics", 1 if scored else 0),
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_students": len(scored),
        "cohort_years": _cohort_years(db),
        "stages": [{"key": k, "label": l, "value": v} for k, l, v in stages],
    }


# ---------------------------------------------------------------------------
# JD Analyzer
# ---------------------------------------------------------------------------
def analyze_jd_text(db: Session, text: str) -> dict:
    skills = _parse_skills(text)
    role = _role_type(text)
    ctc_min, ctc_max = _parse_ctc(text)
    gpa_m = re.search(r"(?:gpa|cgpa|aggregate)[^0-9]{0,6}([0-3](?:\.\d+)?)", text, re.IGNORECASE)
    min_gpa = float(gpa_m.group(1)) if gpa_m else 2.5
    bl_m = re.search(r"(?:backlog)[^0-9]{0,8}(\d+)", text, re.IGNORECASE)
    max_backlogs = int(bl_m.group(1)) if bl_m else 0
    yr_m = re.search(r"(?:final\s*year|(?:19|2[0-4])\s*(?:batch|pass)?(?:ing)?\s*out)", text, re.IGNORECASE)
    year_required = 4 if yr_m else 0
    loc_m = re.search(r"(?:location|work\s*from)[\s\:\-]*([a-z]+(?:[ ,\-][a-z]+){0,3})", text, re.IGNORECASE)
    location = loc_m.group(1).strip() if loc_m else ""
    mode = "remote" if re.search(r"remote|work from home|wfh", text, re.IGNORECASE) else "onsite"
    return {
        "skills": skills,
        "role_type": role,
        "min_gpa": min_gpa,
        "max_backlogs": max_backlogs,
        "year_required": year_required,
        "ctc_min": ctc_min,
        "ctc_max": ctc_max,
        "location": location,
        "mode": mode,
        "word_count": len(text.split()),
        "method": "deterministic",
    }


def create_company(db: Session, *, name: str, sector: str, location: str, contact_email: str, contact_phone: str, notes: str, actor: str) -> dict:
    company = Company(name=name, sector=sector, location=location, contact_email=contact_email,
                     contact_phone=contact_phone, notes=notes)
    db.add(company)
    db.flush()
    record_event(db, actor=actor, action="company_created", entity_type="company", entity_id=company.id,
                 payload={"name": name, "sector": sector})
    return _company_row(db, company.id)


def create_jd(db: Session, *, company_id: str, title: str, raw_text: str, min_gpa: float | None,
              max_backlogs: int | None, ctc_min: float | None, ctc_max: float | None,
              openings: int | None, actor: str) -> dict:
    parsed = analyze_jd_text(db, raw_text)
    jd = JobDescription(
        company_id=company_id,
        title=title,
        raw_text=raw_text,
        skills=parsed["skills"],
        role_type=parsed["role_type"],
        min_gpa=min_gpa if min_gpa is not None else parsed["min_gpa"],
        max_backlogs=max_backlogs if max_backlogs is not None else parsed["max_backlogs"],
        year_required=parsed["year_required"],
        ctc_min=ctc_min if ctc_min is not None else parsed["ctc_min"],
        ctc_max=ctc_max if ctc_max is not None else parsed["ctc_max"],
        openings=openings if openings is not None else 1,
        location=parsed["location"],
        mode=parsed["mode"],
    )
    db.add(jd)
    db.flush()
    record_event(db, actor=actor, action="jd_created", entity_type="job_description", entity_id=jd.id,
                 payload={"title": title, "company_id": company_id, "skills": parsed["skills"]})
    return _jd_row(db, jd.id)


# ---------------------------------------------------------------------------
# Matching + ranking + shortlist + notify
# ---------------------------------------------------------------------------
def match_for_jd(db: Session, jd: JobDescription, *, limit: int = 100) -> list[dict]:
    skills = [s.lower().strip() for s in (jd.skills or []) if str(s).strip()]
    student_skills = _student_skills(db)
    ranked: list[dict] = []
    eligible = 0
    for r in _scored(db):
        if r["gpa"] < jd.min_gpa:
            continue
        if r["backlogs"] > jd.max_backlogs:
            continue
        if jd.year_required and r["year"] < jd.year_required:
            continue
        eligible += 1
        matched = _skill_fit(student_skills.get(r["student_uuid"], []), skills)
        gpa_fit = min(1.0, r["gpa"] / 4.0)
        backlog_fit = 1.0 / (1.0 + r["backlogs"])
        readiness_fit = r["readiness_score"] / 100.0
        skill_fit = (len(matched) / len(skills)) if skills else 0.5
        score = 100.0 * (0.35 * gpa_fit + 0.15 * backlog_fit + 0.25 * readiness_fit + 0.25 * skill_fit)
        ranked.append({
            "student_id": r["student_id"],
            "program": r["program"],
            "year": r["year"],
            "gpa": r["gpa"],
            "backlogs": r["backlogs"],
            "readiness_score": r["readiness_score"],
            "placement_probability": r["placement_probability"],
            "skills_matched": matched,
            "match_score": round(score, 1),
            "gates": {"gpa_ok": r["gpa"] >= jd.min_gpa, "backlogs_ok": r["backlogs"] <= jd.max_backlogs,
                      "year_ok": jd.year_required == 0 or r["year"] >= jd.year_required},
        })
    ranked.sort(key=lambda c: c["match_score"], reverse=True)
    return {"jd_id": jd.id, "title": jd.title, "required_skills": skills,
            "eligible_count": eligible, "candidates": ranked[:limit]}


def notify_students(db: Session, *, drive_id: str, student_ids: list[str], actor: str) -> dict:
    drive = db.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id)).scalar_one_or_none()
    if drive is None:
        raise ValueError("drive not found")
    company = db.execute(select(Company).where(Company.id == drive.company_id)).scalar_one()
    created = 0
    for sid in student_ids:
        student = db.execute(select(Student).where(Student.student_id == sid)).scalar_one_or_none()
        if student is None:
            continue
        existing = db.execute(
            select(PlacementNotification).where(
                PlacementNotification.drive_id == drive_id, PlacementNotification.student_id == student.id
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(PlacementNotification(
            drive_id=drive_id,
            student_id=student.id,
            title=f"{company.name} recruitment drive",
            body=f"You have been shortlisted for {drive.title} ({drive.drive_date}). Prepare for the upcoming rounds.",
        ))
        created += 1
    db.commit()
    if created:
        record_event(db, actor=actor, action="students_notified", entity_type="placement_drive",
                     entity_id=drive_id, payload={"drive": drive.title, "students": created})
    return {"notified": created, "drive_id": drive_id, "drive_title": drive.title}


# ---------------------------------------------------------------------------
# CRUD rows for the frontend
# ---------------------------------------------------------------------------
def _company_row(db: Session, company_id: str) -> dict:
    company = db.execute(select(Company).where(Company.id == company_id)).scalar_one()
    drives = db.execute(select(func.count(PlacementDrive.id)).where(PlacementDrive.company_id == company_id)).scalar_one()
    selections = db.execute(
        select(func.count(PlacementSelection.id))
        .select_from(PlacementDrive)
        .join(PlacementSelection, PlacementSelection.drive_id == PlacementDrive.id)
        .where(PlacementDrive.company_id == company_id)
    ).scalar_one()
    return {"id": company.id, "name": company.name, "sector": company.sector, "location": company.location,
            "contact_email": company.contact_email, "contact_phone": company.contact_phone, "notes": company.notes,
            "created_at": company.created_at.isoformat(), "drives": drives, "selections": selections}


def _jd_row(db: Session, jd_id: str) -> dict:
    jd = db.execute(select(JobDescription).where(JobDescription.id == jd_id)).scalar_one()
    drives = db.execute(select(func.count(PlacementDrive.id)).where(PlacementDrive.jd_id == jd_id)).scalar_one()
    return {"id": jd.id, "company_id": jd.company_id, "title": jd.title, "skills": jd.skills,
            "role_type": jd.role_type, "min_gpa": jd.min_gpa, "max_backlogs": jd.max_backlogs,
            "year_required": jd.year_required, "ctc_min": jd.ctc_min, "ctc_max": jd.ctc_max,
            "openings": jd.openings, "location": jd.location, "mode": jd.mode, "status": jd.status,
            "created_at": jd.created_at.isoformat(), "drives": drives}


def get_companies(db: Session) -> list[dict]:
    rows = db.execute(select(Company).order_by(Company.name)).scalars().all()
    return [_company_row(db, c.id) for c in rows]


def get_jds(db: Session, *, company_id: str | None = None) -> list[dict]:
    q = select(JobDescription).order_by(JobDescription.created_at.desc())
    if company_id:
        q = q.where(JobDescription.company_id == company_id)
    rows = db.execute(q).scalars().all()
    return [_jd_row(db, jd.id) for jd in rows]


def create_drive(db: Session, *, title: str, company_id: str, jd_id: str | None, drive_date: date,
                 mode: str, location: str, actor: str) -> dict:
    drive = PlacementDrive(title=title, company_id=company_id, jd_id=jd_id, drive_date=drive_date,
                           mode=mode, location=location, status="scheduled")
    db.add(drive)
    db.flush()
    record_event(db, actor=actor, action="drive_created", entity_type="placement_drive", entity_id=drive.id,
                 payload={"title": title, "company_id": company_id, "drive_date": str(drive_date)})
    return _drive_row(db, drive.id)


def add_round(db: Session, *, drive_id: str, name: str, round_order: int, round_date: date, actor: str) -> dict:
    round_ = RecruitmentRound(drive_id=drive_id, name=name, round_order=round_order, round_date=round_date)
    db.add(round_)
    db.flush()
    record_event(db, actor=actor, action="round_created", entity_type="recruitment_round", entity_id=round_.id,
                 payload={"drive_id": drive_id, "name": name})
    return _drive_row(db, drive_id)


def record_selection(db: Session, *, drive_id: str, student_id: str, round_reached: str,
                     offered_ctc: float, offer_status: str, actor: str) -> dict:
    student = db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()
    if student is None:
        raise ValueError(f"student {student_id} not found")
    existing = db.execute(
        select(PlacementSelection).where(PlacementSelection.drive_id == drive_id,
                                         PlacementSelection.student_id == student.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"selection already recorded for {student_id} in this drive")
    sel = PlacementSelection(drive_id=drive_id, student_id=student.id, round_reached=round_reached,
                             offered_ctc=offered_ctc, offer_status=offer_status, decided_at=datetime.now(timezone.utc))
    db.add(sel)
    db.flush()
    record_event(db, actor=actor, action="selection_recorded", entity_type="placement_selection", entity_id=sel.id,
                 payload={"drive_id": drive_id, "student_id": student_id, "offer_status": offer_status,
                          "offered_ctc": offered_ctc})
    return _drive_row(db, drive_id)


def _drive_row(db: Session, drive_id: str) -> dict:
    drive = db.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id)).scalar_one()
    company = db.execute(select(Company).where(Company.id == drive.company_id)).scalar_one()
    rounds = db.execute(select(RecruitmentRound).where(RecruitmentRound.drive_id == drive_id)
                        .order_by(RecruitmentRound.round_order)).scalars().all()
    selections = db.execute(select(PlacementSelection).where(PlacementSelection.drive_id == drive_id)).scalars().all()
    notified = db.execute(select(func.count(PlacementNotification.id)).where(PlacementNotification.drive_id == drive_id)).scalar_one()
    uuid_to_display = {s.id: s.student_id for s in db.execute(select(Student)).scalars().all()}
    return {
        "id": drive.id, "title": drive.title, "company": company.name, "company_id": drive.company_id,
        "jd_id": drive.jd_id, "drive_date": drive.drive_date.isoformat(), "mode": drive.mode,
        "location": drive.location, "status": drive.status,
        "rounds": [{"id": r.id, "name": r.name, "round_order": r.round_order, "round_date": r.round_date.isoformat(),
                    "status": r.status} for r in rounds],
        "selections": [{"id": s.id, "student_id": uuid_to_display.get(s.student_id, s.student_id),
                        "round_reached": s.round_reached,
                        "offered_ctc": s.offered_ctc, "offer_status": s.offer_status} for s in selections],
        "notified": notified,
    }


def get_drives(db: Session) -> list[dict]:
    rows = db.execute(select(PlacementDrive).order_by(PlacementDrive.drive_date.desc())).scalars().all()
    return [_drive_row(db, d.id) for d in rows]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def get_funnel(db: Session) -> dict:
    scored = _scored(db)
    total = len(scored)
    ready = sum(1 for r in scored if r["band"] == "ready")
    at_risk = sum(1 for r in scored if (r["placement_probability"] or 0) < AT_RISK_CUTOFF)
    open_jds = db.execute(select(JobDescription).where(JobDescription.status == "open")).scalars().all()
    eligible = 0
    for jd in open_jds:
        for r in scored:
            if r["gpa"] >= jd.min_gpa and r["backlogs"] <= jd.max_backlogs and (jd.year_required == 0 or r["year"] >= jd.year_required):
                eligible += 1
                break
    shortlisted = db.execute(select(func.count(PlacementNotification.id))).scalar_one()
    offers = db.execute(select(func.count(PlacementSelection.id)).where(PlacementSelection.offer_status.in_(["offered", "accepted", "joined"]))).scalar_one()
    joined = db.execute(select(func.count(PlacementSelection.id)).where(PlacementSelection.offer_status == "joined")).scalar_one()
    return {
        "cohort": total,
        "eligible": eligible,
        "shortlisted": shortlisted,
        "offers": offers,
        "joined": joined,
        "ready": ready,
        "at_risk": at_risk,
        "conversion": {
            "eligible_pct": round(100.0 * eligible / total, 1) if total else 0,
            "offer_rate_pct": round(100.0 * offers / total, 1) if total else 0,
            "join_rate_pct": round(100.0 * joined / total, 1) if total else 0,
        },
        "note": "eligible/shortlist derived from open JDs and drive notifications; offers from recorded selections.",
    }


def get_salary_analytics(db: Session) -> dict:
    stats = _selection_stats(db)
    by_program = {p: _aggregate(rows) for p, rows in stats["by_program"].items()}
    by_sector = {s: _aggregate(rows) for s, rows in stats["by_sector"].items()}
    all_rows = [r for rows in stats["by_program"].values() for r in rows]
    return {"overall": _aggregate(all_rows), "by_program": by_program, "by_sector": by_sector,
            "note": "CTC analytics come from recorded drive selections."}


def get_skill_demand(db: Session) -> dict:
    jds = db.execute(select(JobDescription)).scalars().all()
    counts: dict[str, int] = defaultdict(int)
    for jd in jds:
        for skill in (jd.skills or []):
            counts[str(skill).lower()] += 1
    top = [{"skill": k, "demand": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
    sectors: dict[str, dict] = defaultdict(lambda: {"jds": 0, "skills": defaultdict(int)})
    for jd in jds:
        company = db.execute(select(Company).where(Company.id == jd.company_id)).scalar_one_or_none()
        sector = company.sector if company and company.sector else "unspecified"
        sectors[sector]["jds"] += 1
        for skill in (jd.skills or []):
            sectors[sector]["skills"][str(skill).lower()] += 1
    sector_rows = [
        {"sector": s, "jds": v["jds"],
         "top_skills": [{"skill": k, "demand": c} for k, c in sorted(v["skills"].items(), key=lambda x: x[1], reverse=True)[:5]]}
        for s, v in sorted(sectors.items())
    ]
    return {"total_jds": len(jds), "top_skills": top[:20], "sectors": sector_rows}


def get_gap_analysis(db: Session, student_id: str | None = None) -> dict:
    scored = _scored(db)
    student_skills = _student_skills(db)
    open_jds = db.execute(select(JobDescription).where(JobDescription.status == "open")).scalars().all()
    demand = defaultdict(int)
    for jd in open_jds:
        for s in (jd.skills or []):
            demand[str(s).lower()] += 1
    required = [s for s, _ in sorted(demand.items(), key=lambda x: x[1], reverse=True)][:12]
    rows = []
    targets = [r for r in scored if not student_id or r["student_id"] == student_id]
    for r in targets:
        own = student_skills.get(r["student_uuid"], [])
        gaps = [s for s in required if s not in own]
        rows.append({
            "student_id": r["student_id"],
            "program": r["program"],
            "skills": own,
            "gap_skills": gaps,
            "gap_count": len(gaps),
            "recommendation": ", ".join(f"train on {s}" for s in gaps[:5]) or "align with recruiter expectations",
        })
    if student_id:
        rows = [r for r in rows if r["student_id"] == student_id]
    return {"required_skills": required, "students": rows[:100], "total": len(rows)}


def _training_plan(r: dict, gaps: list[str]) -> str:
    weakest = min(r["components"], key=r["components"].get)
    if r["backlogs"]:
        base = f"Clear {r['backlogs']} backlog(s) first; "
    elif weakest == "attendance":
        base = "Attendance below target; attend 4 consecutive weeks at 100%. "
    elif weakest == "academic":
        base = "Raise GPA via focused re-sits and assignment recovery. "
    else:
        base = "Practice aptitude tests daily for 30 min. "
    skill_part = "; then " + ", ".join(f"build {g}" for g in gaps[:3]) if gaps else ""
    return base + skill_part + "."


def get_training_plans(db: Session, *, limit: int = 50) -> list[dict]:
    scored = _scored(db)
    student_skills = _student_skills(db)
    demand = defaultdict(int)
    for jd in db.execute(select(JobDescription)).scalars().all():
        for s in (jd.skills or []):
            demand[str(s).lower()] += 1
    required = [s for s, _ in sorted(demand.items(), key=lambda x: x[1], reverse=True)][:8]
    targets = [r for r in scored if (r["placement_probability"] or 0) < 0.7]
    targets.sort(key=lambda r: r["placement_probability"] or 1.0)
    out = []
    for r in targets[:limit]:
        own = student_skills.get(r["student_uuid"], [])
        gaps = [s for s in required if s not in own]
        out.append({
            "student_id": r["student_id"],
            "program": r["program"],
            "readiness_score": r["readiness_score"],
            "placement_probability": r["placement_probability"],
            "weakest_component": min(r["components"], key=r["components"].get),
            "gap_skills": gaps,
            "plan": _training_plan(r, gaps),
        })
    return out


def _program_marks(db: Session) -> dict[str, list[float]]:
    rows = db.execute(
        select(Student.program, Result.marks)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.status == "approved")
    ).all()
    by_program: dict[str, list[float]] = defaultdict(list)
    for program, marks in rows:
        by_program[program].append(marks or 0.0)
    return by_program


def _assessment_analytics(db: Session, kind: str) -> dict:
    rows = db.execute(
        select(Student.program, Course.title, Result.marks, Result.grade)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Course, Course.id == Enrollment.course_id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.status == "approved")
    ).all()
    scoring_keywords = {
        "coding": ["programming", "python", "java", "javascript", "c", "web", "data", "ai", "ml", "database", "software", "algorithm", "operating", "network"],
        "aptitude": [],
        "communication": [],
    }
    key = scoring_keywords[kind]
    by_program: dict[str, list[float]] = defaultdict(list)
    pass_by_program: dict[str, list[bool]] = defaultdict(list)
    for program, title, marks, grade in rows:
        if kind == "coding" and not any(k in (title or "").lower() for k in key):
            continue
        if kind in ("aptitude", "communication") and key:
            continue
        by_program[program].append(marks or 0.0)
        pass_by_program[program].append(grade != "F")
    programs = []
    for program, ms in by_program.items():
        passed = pass_by_program[program]
        avg = sum(ms) / len(ms) if ms else 0
        programs.append({
            "program": program,
            "students": len(ms),
            "avg_score": round(avg, 1),
            "pass_rate": round(sum(passed) / len(passed), 4) if passed else 0,
            "max_score": round(max(ms), 1) if ms else 0,
            "min_score": round(min(ms), 1) if ms else 0,
        })
    programs.sort(key=lambda p: p["avg_score"], reverse=True)
    all_scores = [m for ms in by_program.values() for m in ms]
    all_passed = [p for ps in pass_by_program.values() for p in ps]
    return {
        "kind": kind,
        "note": "heuristic proxy computed from course marks"
                + (" in programming/data courses" if kind == "coding" else " (aptitude/communication are course-mark proxies; interview data is roadmap)"),
        "programs": programs,
        "overall_avg": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
        "overall_pass_rate": round(sum(all_passed) / len(all_passed), 4) if all_passed else 0,
    }


def get_coding_analytics(db: Session) -> dict:
    return _assessment_analytics(db, "coding")


def get_aptitude_analytics(db: Session) -> dict:
    return _assessment_analytics(db, "aptitude")


def get_communication_analytics(db: Session) -> dict:
    return _assessment_analytics(db, "communication")


def get_department_comparison(db: Session) -> dict:
    scored = _scored(db)
    by_program: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        by_program[r["program"]].append(r)
    sel = _selection_stats(db)
    programs = []
    for program, rows in by_program.items():
        agg = _aggregate(sel["by_program"].get(program, []))
        programs.append({
            "program": program,
            "students": len(rows),
            "ready": sum(1 for r in rows if r["band"] == "ready"),
            "avg_readiness": round(sum(r["readiness_score"] for r in rows) / len(rows), 1),
            "avg_gpa": round(sum(r["gpa"] for r in rows) / len(rows), 2),
            "avg_ctc": agg["avg_ctc"],
            "offers": agg["count"],
            "joined": agg["joined"],
        })
    programs.sort(key=lambda p: p["avg_readiness"], reverse=True)
    return {"programs": programs}


def get_placement_prediction(db: Session) -> dict:
    scored = _scored(db)
    probas = [r["placement_probability"] for r in scored if r["placement_probability"] is not None]
    predicted_rate = round(sum(probas) / len(probas), 4) if probas else None
    bands = defaultdict(int)
    for r in scored:
        bands[r["band"]] += 1
    years = defaultdict(list)
    for r in scored:
        years[r["year"]].append(r["placement_probability"])
    trend = [{"year": y, "students": len(ps), "predicted_rate": round(sum(ps) / len(ps), 4)} for y, ps in sorted(years.items())]
    return {
        "predicted_placement_rate": predicted_rate,
        "cohort_size": len(scored),
        "ready_count": bands["ready"],
        "at_risk_count": sum(1 for r in scored if (r["placement_probability"] or 0) < AT_RISK_CUTOFF),
        "trend": trend,
        "note": "Predicted rate = mean ML placement probability over the cohort.",
    }


def get_notifications(db: Session) -> dict:
    rows = db.execute(
        select(PlacementNotification, Student.student_id)
        .join(Student, Student.id == PlacementNotification.student_id)
        .order_by(PlacementNotification.created_at.desc())
        .limit(100)
    ).all()
    entries = [
        {"id": n.id, "student_id": sid, "title": n.title, "body": n.body, "status": n.status,
         "created_at": n.created_at.isoformat()}
        for n, sid in rows
    ]
    unread = sum(1 for e in entries if e["status"] == "sent")
    return {"entries": entries, "total": len(entries), "unread": unread}


def mark_notification_read(db: Session, notification_id: str) -> dict:
    n = db.execute(select(PlacementNotification).where(PlacementNotification.id == notification_id)).scalar_one_or_none()
    if n is None:
        raise ValueError("notification not found")
    n.status = "read"
    db.commit()
    return {"id": n.id, "status": n.status}


def get_pipeline(db: Session, drive_id: str) -> dict:
    drive = _drive_row(db, drive_id)
    company = db.execute(select(Company).where(Company.id == drive["company_id"])).scalar_one()
    notified = db.execute(select(PlacementNotification).where(PlacementNotification.drive_id == drive_id)).scalars().all()
    round_names = [r["name"] for r in drive["rounds"]]
    stage_counts: dict[str, int] = defaultdict(int)
    stage_counts["notified"] = len(notified)
    cleared: dict[str, list[str]] = defaultdict(list)
    for sel in drive["selections"]:
        cleared[sel["round_reached"] or "selection"].append(sel["student_id"])
    stages = [{"stage": "Notified", "count": len(notified)}]
    for name in round_names:
        stages.append({"stage": name, "count": len(cleared[name])})
    stages.append({"stage": "Selected", "count": len(drive["selections"])})
    selections = drive["selections"]
    return {
        "drive": drive,
        "company": company.name,
        "rounds": round_names,
        "funnel": stages,
        "selections": selections,
        "offer_rate_pct": round(100.0 * len(selections) / len(notified), 1) if notified else 0,
    }


def get_reports(db: Session) -> dict:
    overview = get_funnel(db)
    prediction = get_placement_prediction(db)
    dept = get_department_comparison(db)
    salary = get_salary_analytics(db)
    demand = get_skill_demand(db)
    risk = _scored(db)
    high_risk = [r for r in risk if (r["placement_probability"] or 0) < AT_RISK_CUTOFF]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "analytical-batch",
        "funnel": overview,
        "prediction": prediction,
        "departments": dept["programs"],
        "salary": salary["overall"],
        "top_skills": demand["top_skills"][:5],
        "high_risk_students": len(high_risk),
        "summary": (
            f"Cohort of {overview['cohort']} students; predicted placement rate "
            f"{prediction['predicted_placement_rate']:.0%}; {overview['ready']} ready, "
            f"{len(high_risk)} at risk. Top in-demand skill: "
            f"{demand['top_skills'][0]['skill'] if demand['top_skills'] else 'n/a'}."
        ),
    }
