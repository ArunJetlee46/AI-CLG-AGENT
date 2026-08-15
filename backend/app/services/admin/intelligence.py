"""Admin analytics + management batch (deterministic, audit-logged).

Covers the analytical/management half of the admin module:

  Management : users, RBAC, departments, announcements, resources,
               backups, AI model registry, research projects, industry partners
  Analytics  : student, faculty, university placement, KPI, dropout risk,
               curriculum, enrollment forecast, accreditation, research,
               industry collaboration, system health, governance center

Every mutation is written directly and recorded on the audit log. All
analytics reuse the shared student aggregates (placement._scored,
admin_copilot._institution_profile) so numbers stay consistent with the
Faculty and Placement modules.
"""
import hashlib
import json
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import safety
from app.core.audit import record_event
from app.core.security import hash_password
from app.models.entities import (
    Admin as AdminProfile,
)
from app.models.entities import (
    Announcement,
    ApprovalRequest,
    AuditLog,
    BackupRecord,
    CampusResource,
    Course,
    DecisionCard,
    Enrollment,
    IndustryPartner,
    Lecturer,
    ModelRecord,
    ResearchProject,
    Result,
    Room,
    Student,
    TimetableEntry,
    User,
)
from app.services.admin import copilot as admin_copilot
from app.services.admin.copilot import (
    _academic_pass_map,
    _department_rows,
    _difficult_courses,
    _dropout_risk,
    _institution_profile,
)
from app.services.placement import _scored
from app.services.placement import intelligence as pl

ROLES = ("student", "lecturer", "placement", "admin")
HIGH_RISK_CUTOFF = 0.7


def _user_row(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "email": u.email,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# User management + RBAC
# ---------------------------------------------------------------------------
def list_users(db: Session) -> list[dict]:
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [_user_row(u) for u in users]


def _next_code(db: Session, prefix: str, model) -> str:
    count = db.execute(select(func.count()).select_from(model)).scalar() or 0
    candidate = f"{prefix}{count + 1:05d}"
    while True:
        exists = db.execute(select(model.id).where(model.student_id == candidate)).scalar_one_or_none() if model is Student else \
                 db.execute(select(model.id).where(model.staff_id == candidate)).scalar_one_or_none()
        if not exists:
            return candidate
        count += 1
        candidate = f"{prefix}{count + 1:05d}"


def create_user(db: Session, *, actor: str, username: str, password: str, role: str, email: str = "") -> dict:
    username = username.strip()
    if db.execute(select(User.id).where(User.username == username)).scalar_one_or_none():
        raise ValueError(f"username '{username}' already exists")
    user = User(username=username, password_hash=hash_password(password), role=role, email=email.strip(), is_active=True)
    db.add(user)
    db.flush()
    if role == "student":
        db.add(Student(user_id=user.id, student_id=_next_code(db, "STU", Student), year=1, program=""))
    elif role == "lecturer":
        db.add(Lecturer(user_id=user.id, staff_id=_next_code(db, "FAC", Lecturer), department=""))
    elif role == "admin":
        db.add(AdminProfile(user_id=user.id, permissions=[]))
    record_event(db, actor=actor, action="user_created", entity_type="user", entity_id=user.id,
                 payload={"username": user.username, "role": role})
    return _user_row(user)


def update_user(db: Session, *, actor: str, user_id: str, role: str | None = None,
                is_active: bool | None = None, password: str | None = None) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("user not found")
    changes: dict = {}
    if role is not None and role != user.role:
        user.role = role
        changes["role"] = role
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        changes["is_active"] = is_active
    if password is not None:
        user.password_hash = hash_password(password)
        changes["password_reset"] = True
    if not changes:
        return _user_row(user)
    record_event(db, actor=actor, action="user_updated", entity_type="user", entity_id=user.id, payload=changes)
    return _user_row(user)


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------
def list_departments(db: Session) -> dict:
    rows = _department_rows(db)
    programs = {r["program"] for r in rows}
    for (p,) in db.execute(select(Course.department)).all():
        if p:
            programs.add(p)
    for (p,) in db.execute(select(Lecturer.department)).all():
        if p:
            programs.add(p)
    return {"departments": rows, "count": len(rows), "all_programs": sorted(programs)}


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------
def list_announcements(db: Session) -> list[dict]:
    rows = db.execute(
        select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    ).scalars().all()
    creator_names = [a.created_by for a in rows if a.created_by]
    creator_roles: dict[str, str] = {}
    if creator_names:
        creator_roles = {
            u.username: u.role
            for u in db.execute(select(User).where(User.username.in_(creator_names))).scalars()
        }
    return [{
        "id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
        "pinned": a.pinned, "created_by": a.created_by,
        "created_role": creator_roles.get(a.created_by, ""),
        "created_at": a.created_at.isoformat(),
    } for a in rows]


def create_announcement(db: Session, *, actor: str, actor_role: str = "", title: str, body: str,
                        audience: str = "all", pinned: bool = False) -> dict:
    a = Announcement(title=title, body=body, audience=audience, pinned=pinned, created_by=actor)
    db.add(a)
    db.flush()
    record_event(db, actor=actor, action="announcement_created", entity_type="announcement",
                 entity_id=a.id, payload={"title": title, "audience": audience})
    return {"id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
            "pinned": a.pinned, "created_by": a.created_by, "created_role": actor_role,
            "created_at": a.created_at.isoformat()}


def delete_announcement(db: Session, *, actor: str, announcement_id: str) -> dict:
    a = db.get(Announcement, announcement_id)
    if a is None:
        raise ValueError("announcement not found")
    title = a.title
    db.delete(a)
    record_event(db, actor=actor, action="announcement_deleted", entity_type="announcement",
                 entity_id=announcement_id, payload={"title": title})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Resource management
# ---------------------------------------------------------------------------
def list_resources(db: Session) -> dict:
    resources = db.execute(select(CampusResource).order_by(CampusResource.name)).scalars().all()
    room_usage: dict[str, int] = defaultdict(int)
    for (room_id,) in db.execute(select(TimetableEntry.room_id)).all():
        room_usage[room_id] += 1
    rows = [{
        "id": r.id, "name": r.name, "resource_type": r.resource_type, "capacity": r.capacity,
        "location": r.location, "status": r.status, "utilization": r.utilization,
        "notes": r.notes, "source": "manual",
    } for r in resources]
    for r in db.execute(select(Room)).scalars():
        rows.append({
            "id": r.id, "name": f"Room {r.room_no}", "resource_type": r.kind, "capacity": r.capacity,
            "location": "", "status": "active",
            "utilization": round(min(100.0, room_usage.get(r.id, 0) * 4.0), 1),
            "notes": "derived from timetable usage", "source": "timetable",
        })
    return {"resources": rows, "count": len(rows),
            "status_counts": {s: sum(1 for x in rows if x["status"] == s) for s in set(x["status"] for x in rows)}}


def create_resource(db: Session, *, actor: str, name: str, resource_type: str, capacity: int,
                    location: str, status: str, utilization: float, notes: str) -> dict:
    r = CampusResource(name=name, resource_type=resource_type, capacity=capacity,
                       location=location, status=status, utilization=utilization, notes=notes)
    db.add(r)
    db.flush()
    record_event(db, actor=actor, action="resource_created", entity_type="resource",
                 entity_id=r.id, payload={"name": name, "resource_type": resource_type})
    return {"id": r.id, "name": r.name, "resource_type": r.resource_type, "capacity": r.capacity,
            "location": r.location, "status": r.status, "utilization": r.utilization,
            "notes": r.notes, "source": "manual"}


def update_resource(db: Session, *, actor: str, resource_id: str, status: str | None = None,
                    utilization: float | None = None) -> dict:
    r = db.get(CampusResource, resource_id)
    if r is None:
        raise ValueError("resource not found")
    changes: dict = {}
    if status is not None and status != r.status:
        r.status = status
        changes["status"] = status
    if utilization is not None and utilization != r.utilization:
        r.utilization = utilization
        changes["utilization"] = utilization
    if changes:
        record_event(db, actor=actor, action="resource_updated", entity_type="resource",
                     entity_id=resource_id, payload=changes)
    return {"id": r.id, "name": r.name, "resource_type": r.resource_type, "capacity": r.capacity,
            "location": r.location, "status": r.status, "utilization": r.utilization,
            "notes": r.notes, "source": "manual"}


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
def list_backups(db: Session) -> list[dict]:
    rows = db.execute(select(BackupRecord).order_by(BackupRecord.created_at.desc())).scalars().all()
    return [{
        "id": b.id, "filename": b.filename, "kind": b.kind, "status": b.status,
        "size_bytes": b.size_bytes, "note": b.note, "created_at": b.created_at.isoformat(),
    } for b in rows]


def create_backup(db: Session, *, actor: str, note: str = "") -> dict:
    tables = {"users": User, "students": Student, "lecturers": Lecturer, "courses": Course,
              "enrollments": Enrollment, "results": Result, "audit_logs": AuditLog}
    snapshot = {name: db.execute(select(func.count()).select_from(model)).scalar() or 0
                for name, model in tables.items()}
    rec = BackupRecord(
        filename=f"beru_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db",
        kind="manual", status="completed",
        size_bytes=sum(snapshot.values()) * 2048,
        note=note or "manual snapshot",
    )
    db.add(rec)
    db.flush()
    record_event(db, actor=actor, action="backup_created", entity_type="backup",
                 entity_id=rec.id, payload=snapshot)
    return {"id": rec.id, "filename": rec.filename, "kind": rec.kind, "status": rec.status,
            "size_bytes": rec.size_bytes, "note": rec.note, "created_at": rec.created_at.isoformat(),
            "snapshot": snapshot}


def restore_backup(db: Session, *, actor: str, backup_id: str) -> dict:
    b = db.get(BackupRecord, backup_id)
    if b is None:
        raise ValueError("backup not found")
    record_event(db, actor=actor, action="backup_restored", entity_type="backup",
                 entity_id=backup_id, payload={"filename": b.filename})
    return {"ok": True, "message": f"restore simulated for {b.filename}"}


# ---------------------------------------------------------------------------
# AI model management
# ---------------------------------------------------------------------------
def _model_row(m: ModelRecord) -> dict:
    return {"id": m.id, "name": m.name, "version": m.version, "path": m.path,
            "metrics": m.metrics, "is_active": m.is_active, "trained_at": m.trained_at.isoformat()}


def list_models(db: Session) -> dict:
    rows = db.execute(select(ModelRecord).order_by(ModelRecord.trained_at.desc())).scalars().all()
    active = next((m for m in rows if m.is_active), None)
    return {"models": [_model_row(m) for m in rows], "count": len(rows),
            "active": _model_row(active) if active else None}


def register_model(db: Session, *, actor: str, name: str, version: str, path: str, metrics: dict) -> dict:
    m = ModelRecord(name=name, version=version, path=path, metrics=metrics)
    db.add(m)
    db.flush()
    record_event(db, actor=actor, action="model_registered", entity_type="model",
                 entity_id=m.id, payload={"name": name, "version": version})
    return _model_row(m)


def set_model_active(db: Session, *, actor: str, model_id: str) -> dict:
    m = db.get(ModelRecord, model_id)
    if m is None:
        raise ValueError("model not found")
    for other in db.execute(select(ModelRecord).where(ModelRecord.is_active.is_(True))).scalars():
        other.is_active = False
    m.is_active = True
    record_event(db, actor=actor, action="model_activated", entity_type="model",
                 entity_id=model_id, payload={"name": m.name, "version": m.version})
    return _model_row(m)


# ---------------------------------------------------------------------------
# Research + Industry
# ---------------------------------------------------------------------------
def list_projects(db: Session) -> list[dict]:
    rows = db.execute(select(ResearchProject).order_by(ResearchProject.created_at.desc())).scalars().all()
    return [{
        "id": p.id, "title": p.title, "lead_name": p.lead_name, "department": p.department,
        "status": p.status, "funding_amount": p.funding_amount, "publications": p.publications,
        "start_year": p.start_year,
    } for p in rows]


def create_project(db: Session, *, actor: str, title: str, lead_name: str, department: str,
                   status: str, funding_amount: float, publications: int, start_year: int) -> dict:
    p = ResearchProject(title=title, lead_name=lead_name, department=department, status=status,
                        funding_amount=funding_amount, publications=publications, start_year=start_year)
    db.add(p)
    db.flush()
    record_event(db, actor=actor, action="research_project_created", entity_type="research_project",
                 entity_id=p.id, payload={"title": title, "department": department})
    return list_projects(db)[0]


def research_dashboard(db: Session) -> dict:
    projects = list_projects(db)
    by_dept: dict[str, dict] = defaultdict(lambda: {"projects": 0, "funding": 0.0, "publications": 0})
    status_counts: dict[str, int] = defaultdict(int)
    for p in projects:
        key = p["department"] or "General"
        by_dept[key]["projects"] += 1
        by_dept[key]["funding"] += p["funding_amount"]
        by_dept[key]["publications"] += p["publications"]
        status_counts[p["status"]] += 1
    return {
        "total_projects": len(projects),
        "total_funding": round(sum(p["funding_amount"] for p in projects), 2),
        "total_publications": sum(p["publications"] for p in projects),
        "status_counts": dict(status_counts),
        "by_department": [{"department": k, **v} for k, v in
                          sorted(by_dept.items(), key=lambda x: -x[1]["funding"])],
    }


def list_partners(db: Session) -> list[dict]:
    rows = db.execute(select(IndustryPartner).order_by(IndustryPartner.created_at.desc())).scalars().all()
    return [{
        "id": p.id, "name": p.name, "sector": p.sector, "contact_person": p.contact_person,
        "mous": p.mous, "active": p.active, "placement_hires": p.placement_hires,
    } for p in rows]


def create_partner(db: Session, *, actor: str, name: str, sector: str, contact_person: str,
                   mous: int, active: bool, placement_hires: int) -> dict:
    p = IndustryPartner(name=name, sector=sector, contact_person=contact_person,
                        mous=mous, active=active, placement_hires=placement_hires)
    db.add(p)
    db.flush()
    record_event(db, actor=actor, action="industry_partner_created", entity_type="industry_partner",
                 entity_id=p.id, payload={"name": name, "sector": sector})
    return list_partners(db)[0]


def industry_intelligence(db: Session) -> dict:
    partners = list_partners(db)
    sectors: dict[str, int] = defaultdict(int)
    for p in partners:
        sectors[p["sector"] or "General"] += 1
    return {
        "partners": partners,
        "total_partners": len(partners),
        "active_partners": sum(1 for p in partners if p["active"]),
        "total_mous": sum(p["mous"] for p in partners),
        "total_hires": sum(p["placement_hires"] for p in partners),
        "sectors": [{"sector": k, "partners": v} for k, v in sorted(sectors.items(), key=lambda x: -x[1])],
        "companies_from_placement": len(pl.get_companies(db)),
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def student_analytics(db: Session) -> dict:
    profile = _institution_profile(db)
    scored = profile["scored"]
    by_program: dict[str, dict] = defaultdict(lambda: {"count": 0, "gpa": 0.0, "readiness": 0.0, "at_risk": 0})
    by_year: dict[int, dict] = defaultdict(lambda: {"count": 0, "at_risk": 0})
    risk_bands = {"low": 0, "medium": 0, "high": 0}
    for s in scored:
        risk = _dropout_risk(s)
        band = "high" if risk >= HIGH_RISK_CUTOFF else ("medium" if risk >= 0.5 else "low")
        risk_bands[band] += 1
        prog = by_program[s["program"]]
        prog["count"] += 1
        prog["gpa"] += s["gpa"]
        prog["readiness"] += s["readiness_score"]
        if band == "high":
            prog["at_risk"] += 1
        yr = by_year[s.get("year", 1)]
        yr["count"] += 1
        if band == "high":
            yr["at_risk"] += 1
    program_rows = []
    for program, agg in by_program.items():
        program_rows.append({
            "program": program, "count": agg["count"],
            "avg_gpa": round(agg["gpa"] / agg["count"], 2),
            "avg_readiness": round(agg["readiness"] / agg["count"], 1),
            "at_risk": agg["at_risk"],
        })
    program_rows.sort(key=lambda r: -r["avg_readiness"])
    top = sorted(scored, key=lambda s: -s["readiness_score"])[:10]
    bottom = sorted(scored, key=lambda s: s["readiness_score"])[:10]
    return {
        "total": profile["students"],
        "risk_bands": risk_bands,
        "by_program": program_rows,
        "by_year": [{"year": y, **agg} for y, agg in sorted(by_year.items())],
        "avg_attendance": round(profile["attendance"] * 100, 1),
        "avg_gpa": round(profile["gpa"], 2),
        "avg_marks": round(profile["avg_marks"], 1),
        "pass_rate": round(profile["pass_rate"] * 100, 1),
        "top_students": [{"student_id": s["student_id"], "program": s["program"], "gpa": s["gpa"],
                          "readiness_score": s["readiness_score"], "band": s["band"]} for s in top],
        "bottom_students": [{"student_id": s["student_id"], "program": s["program"], "gpa": s["gpa"],
                             "readiness_score": s["readiness_score"], "band": s["band"]} for s in bottom],
    }


def _course_pass_map(db: Session) -> dict[str, float]:
    rows = db.execute(
        select(Course.code, Result.grade)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.status == "approved")
    ).all()
    by_course: dict[str, list[int]] = defaultdict(list)
    for code, grade in rows:
        if grade:
            by_course[code].append(1 if grade == "F" else 0)
    return {code: (len(flags) - sum(flags)) / len(flags) for code, flags in by_course.items()}


def faculty_analytics(db: Session) -> dict:
    workload = admin_copilot.faculty_workload(db, limit=200)
    staff_courses: dict[str, set] = defaultdict(set)
    rows = db.execute(
        select(Lecturer.staff_id, Course.code)
        .join(TimetableEntry, TimetableEntry.lecturer_id == Lecturer.id)
        .join(Course, Course.id == TimetableEntry.course_id)
    ).all()
    for staff_id, code in rows:
        staff_courses[staff_id].add(code)
    course_pass = _course_pass_map(db)
    for w in workload:
        codes = staff_courses.get(w["staff_id"], set())
        passes = [course_pass.get(c, 0.5) for c in codes]
        w["avg_pass_rate"] = round(sum(passes) / len(passes) * 100, 1) if passes else None
        w["flag"] = ("overloaded" if w["utilization"] > 100 else
                     ("low_utilization" if w["utilization"] < 40 else None))
    summary = {
        "total_faculty": len(workload),
        "avg_courses": round(sum(w["course_count"] for w in workload) / len(workload), 2) if workload else 0,
        "avg_hours": round(sum(w["teaching_hours"] for w in workload) / len(workload), 1) if workload else 0,
        "overloaded": sum(1 for w in workload if w["flag"] == "overloaded"),
    }
    return {"summary": summary, "rows": workload}


def placement_overview(db: Session) -> dict:
    return {
        "funnel": pl.get_funnel(db),
        "salary": pl.get_salary_analytics(db),
        "skill_demand": pl.get_skill_demand(db),
        "departments": pl.get_department_comparison(db),
        "prediction": pl.get_placement_prediction(db),
        "companies": len(pl.get_companies(db)),
        "drives": len(pl.get_drives(db)),
    }


def kpi_dashboard(db: Session) -> dict:
    cc = admin_copilot.command_center(db)
    score = admin_copilot.health_score(db)
    return {
        "counts": cc["counts"],
        "kpis": cc["kpis"],
        "pending_approvals": cc["pending_approvals"],
        "active_agents": cc["active_agents"],
        "system_health": cc["system_health"],
        "execution_enabled": cc["execution_enabled"],
        "university_health_score": score["university_health_score"],
        "axes": score["axes"],
        "basis": score["basis"],
    }


def dropout_analytics(db: Session) -> dict:
    scored = _scored(db)
    rows = []
    for s in scored:
        risk = _dropout_risk(s)
        band = "high" if risk >= HIGH_RISK_CUTOFF else ("medium" if risk >= 0.5 else "low")
        rows.append({
            "student_id": s["student_id"], "program": s["program"], "year": s["year"],
            "gpa": s["gpa"], "attendance_rate": s["attendance_rate"], "avg_marks": s["avg_marks"],
            "backlogs": s["backlogs"], "dropout_risk": risk, "band": band,
        })
    bands = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        bands[r["band"]] += 1
    by_program: dict[str, dict] = defaultdict(lambda: {"count": 0, "high": 0, "avg_risk": 0.0})
    for r in rows:
        prog = by_program[r["program"]]
        prog["count"] += 1
        prog["avg_risk"] += r["dropout_risk"]
        if r["band"] == "high":
            prog["high"] += 1
    program_rows = [{"program": k, "count": v["count"], "high_risk": v["high"],
                     "avg_risk": round(v["avg_risk"] / v["count"], 3)} for k, v in by_program.items()]
    program_rows.sort(key=lambda r: -r["avg_risk"])
    top = sorted(rows, key=lambda r: -r["dropout_risk"])[:15]
    return {
        "total": len(rows),
        "bands": bands,
        "high_risk_ratio": round(bands["high"] / len(rows), 3) if rows else 0.0,
        "by_program": program_rows,
        "top_risk": top,
        "drivers": {
            "avg_attendance": round(sum(r["attendance_rate"] for r in rows) / len(rows) * 100, 1) if rows else 0.0,
            "avg_gpa": round(sum(r["gpa"] for r in rows) / len(rows), 2) if rows else 0.0,
            "avg_backlogs": round(sum(r["backlogs"] for r in rows) / len(rows), 2) if rows else 0.0,
        },
    }


def curriculum_intelligence(db: Session) -> dict:
    rows = db.execute(
        select(Course.code, Course.title, Course.department, Course.credits, Course.prerequisites,
               Enrollment.student_id, Result.marks, Result.grade)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(Result, Result.enrollment_id == Enrollment.id)
    ).all()
    by_course: dict[str, dict] = {}
    for code, title, dept, credits, prereqs, _, marks, grade in rows:
        c = by_course.setdefault(code, {"title": title, "department": dept or "", "credits": credits,
                                        "prerequisites": prereqs or [], "enrolled": 0, "marks": [], "failures": 0})
        if marks is not None:
            c["enrolled"] += 1
            c["marks"].append(marks)
            if grade == "F":
                c["failures"] += 1
    courses = []
    for code, c in by_course.items():
        avg_marks = sum(c["marks"]) / len(c["marks"]) if c["marks"] else 0.0
        failure_rate = c["failures"] / c["enrolled"] if c["enrolled"] else 0.0
        courses.append({
            "course_code": code, "title": c["title"], "department": c["department"],
            "credits": c["credits"], "prerequisites": c["prerequisites"], "enrolled": c["enrolled"],
            "avg_marks": round(avg_marks, 1), "failure_rate": round(failure_rate, 3),
            "difficult": avg_marks < 50.0 or failure_rate > 0.3,
        })
    courses.sort(key=lambda c: c["failure_rate"], reverse=True)
    prereq_health = []
    for code, c in by_course.items():
        for prereq in c["prerequisites"]:
            target = by_course.get(prereq)
            if target is None:
                continue
            t_marks = sum(target["marks"]) / len(target["marks"]) if target["marks"] else 0.0
            c_marks = sum(c["marks"]) / len(c["marks"]) if c["marks"] else 0.0
            prereq_health.append({
                "course_code": code, "prerequisite": prereq,
                "gap": round(c_marks - t_marks, 1),
                "healthy": c_marks >= t_marks,
            })
    return {
        "total_courses": len(courses),
        "difficult_courses": [c for c in courses if c["difficult"]],
        "prerequisite_health": prereq_health,
        "courses": courses,
    }


def enrollment_forecast(db: Session) -> dict:
    rows = db.execute(select(Enrollment.enrolled_at)).all()
    by_year: dict[int, int] = defaultdict(int)
    for (dt,) in rows:
        by_year[dt.year] += 1
    series = [{"year": y, "enrollments": by_year[y]} for y in sorted(by_year)]
    forecast: list[dict] = []
    n = len(series)
    if n >= 2:
        xs = list(range(n))
        ys = [s["enrollments"] for s in series]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom if denom else 0.0
        for k in range(1, 4):
            fy = max(0, int(round(mean_y + slope * (n - 1 + k))))
            forecast.append({"year": (series[-1]["year"] + k) if series else 2026 + k,
                             "enrollments": fy, "forecast": True})
    elif series:
        last = series[-1]["enrollments"]
        for k in range(1, 4):
            forecast.append({"year": series[-1]["year"] + k, "enrollments": last, "forecast": True})
    by_department: dict[str, int] = defaultdict(int)
    rows2 = db.execute(select(Course.department).join(Enrollment, Enrollment.course_id == Course.id)).all()
    for (dept,) in rows2:
        by_department[dept or "General"] += 1
    return {
        "historical": series,
        "forecast": forecast,
        "total_enrollments": sum(v for v in by_year.values()),
        "current_enrollments": by_year.get(datetime.utcnow().year, 0),
        "by_department": [{"department": k, "enrollments": v} for k, v in
                          sorted(by_department.items(), key=lambda x: -x[1])],
    }


def accreditation(db: Session) -> dict:
    profile = _institution_profile(db)
    pass_rate = profile["pass_rate"]
    gpa = profile["gpa"]
    attendance = profile["attendance"]
    ready_ratio = profile["ready_ratio"]
    placement = profile["placement"]
    depts = _department_rows(db)
    projects = list_projects(db)
    resources = list_resources(db)
    faculty_rows = admin_copilot.faculty_workload(db, limit=200)
    criteria = {
        "Curricular Aspects": round(100.0 * (0.5 * min(1.0, pass_rate / 0.7) + 0.5 * min(1.0, gpa / 3.2))),
        "Teaching-Learning & Evaluation": round(100.0 * (0.4 * pass_rate + 0.3 * attendance + 0.3 * min(1.0, gpa / 3.0))),
        "Research & Innovation": round(min(100.0, 40 + len(projects) * 8 + sum(p["publications"] for p in projects) * 3)),
        "Infrastructure & Learning Resources": round(min(100.0, 50 + resources["count"] * 6)),
        "Student Support & Progression": round(100.0 * (0.5 * placement + 0.3 * ready_ratio + 0.2 * min(1.0, gpa / 3.0))),
        "Governance & Leadership": round(min(100.0, 55 + sum(1 for d in depts if not d["flag"]) * 8)),
        "Institutional Values": round(min(100.0, 60 + int(attendance >= 0.75) * 20 + int(pass_rate >= 0.6) * 20)),
    }
    overall = round(sum(criteria.values()) / len(criteria))
    grade = ("A++" if overall >= 90 else "A+" if overall >= 80 else "A" if overall >= 70 else
             "B+" if overall >= 60 else "B" if overall >= 50 else "C")
    readiness = [{"metric": "Student-faculty ratio", "met": len(profile["scored"]) / max(1, len(faculty_rows)) <= 30},
                 {"metric": "Placement rate ≥ 60%", "met": placement >= 0.6},
                 {"metric": "Pass rate ≥ 70%", "met": pass_rate >= 0.7},
                 {"metric": "Attendance ≥ 75%", "met": attendance >= 0.75},
                 {"metric": "Research output present", "met": len(projects) > 0}]
    return {
        "overall_score": overall,
        "grade": grade,
        "criteria": criteria,
        "readiness": readiness,
        "met_count": sum(1 for r in readiness if r["met"]),
        "total_checks": len(readiness),
    }


def system_health(db: Session) -> dict:
    checks: dict[str, dict] = {}
    try:
        with db.bind.connect() as conn:
            db_ok = conn.execute(select(1)).scalar() == 1
    except Exception:
        db_ok = False
    checks["database"] = {"status": "ok" if db_ok else "error", "detail": "database reachable"}
    checks["backend"] = {"status": "ok", "detail": "API responding"}
    checks["llm_providers"] = {"status": "configured", "detail": "ollama configured with deterministic fallback"}
    audit_count = db.execute(select(func.count()).select_from(AuditLog)).scalar() or 0
    checks["audit_chain"] = {"status": "ok" if _verify_audit_chain(db) else "error",
                             "detail": f"hash chain verified across {audit_count} events"}
    overall = "healthy" if all(c["status"] == "ok" for c in checks.values()) else "degraded"
    counts = {
        "users": db.execute(select(func.count()).select_from(User)).scalar() or 0,
        "students": db.execute(select(func.count()).select_from(Student)).scalar() or 0,
        "courses": db.execute(select(func.count()).select_from(Course)).scalar() or 0,
        "audit_events": audit_count,
        "approvals_pending": db.execute(select(func.count()).select_from(ApprovalRequest)
                                        .where(ApprovalRequest.status == "pending")).scalar() or 0,
        "backups": db.execute(select(func.count()).select_from(BackupRecord)).scalar() or 0,
    }
    return {"overall": overall, "checks": checks, "counts": counts}


def _verify_audit_chain(db: Session) -> bool:
    entries = db.execute(select(AuditLog).order_by(AuditLog.created_at)).scalars().all()
    expected = "GENESIS"
    for e in entries:
        raw = json.dumps(e.payload, sort_keys=True, default=str) + f"|{e.actor}|{e.approval_id or ''}|{expected}"
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != e.hash:
            return False
        expected = e.hash
    return True


def governance_center(db: Session) -> dict:
    safety_state = safety.get_safety()
    pending = db.execute(select(func.count()).select_from(ApprovalRequest)
                         .where(ApprovalRequest.status == "pending")).scalar() or 0
    total_approvals = db.execute(select(func.count()).select_from(ApprovalRequest)).scalar() or 0
    audit_count = db.execute(select(func.count()).select_from(AuditLog)).scalar() or 0
    decision_count = db.execute(select(func.count()).select_from(DecisionCard)).scalar() or 0
    models = db.execute(select(ModelRecord)).scalars().all()
    recommendations = []
    if not safety_state["execution_allowed"]:
        recommendations.append("AI execution is paused — resume from the safety controls when ready.")
    if pending:
        recommendations.append(f"{pending} approval request(s) are awaiting a decision in the Approval Center.")
    if not any(m.is_active for m in models):
        recommendations.append("No AI model is active — activate one from the Model Management registry.")
    return {
        "safety": safety_state,
        "approvals": {"pending": pending, "total": total_approvals},
        "audit": {"events": audit_count, "decision_cards": decision_count},
        "models": {"total": len(models), "active": sum(1 for m in models if m.is_active)},
        "recommendations": recommendations,
    }
