"""Admin Copilot API (admin-only)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import Announcement, User
from app.schemas.admin import (
    AnnouncementCreate,
    CopilotRequest,
    EvaluationRequest,
    IndustryPartnerCreate,
    ModelRegister,
    ResearchProjectCreate,
    ResourceCreate,
    ResourceUpdate,
    ScenarioRequest,
    TimetableOptimizeRequest,
)
from app.schemas.auth import UserCreate, UserUpdate
from app.services import admin_ai_tools, admin_copilot, admin_intelligence

router = APIRouter(prefix="/admin", tags=["admin"])

_admin = require_role("admin")

# Anyone who can broadcast announcements (faculty, placement, admin).
_announcer = require_role("admin", "lecturer", "placement")


def _raise400(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class SafetyRequest(BaseModel):
    execution_enabled: bool = Field(default=True)
    read_only: bool = Field(default=False)


@router.get("/command-center")
def command_center(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_copilot.command_center(db)


@router.get("/health-score")
def health_score(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_copilot.health_score(db)


@router.get("/early-warnings")
def early_warnings(_: User = Depends(_admin), db: Session = Depends(get_db)) -> list[dict]:
    return admin_copilot.early_warnings(db)


@router.get("/departments")
def departments(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.list_departments(db)


@router.get("/faculty-workload")
def faculty_workload(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    return admin_copilot.faculty_workload(db, limit=limit)


@router.get("/agents")
def agents(_: User = Depends(_admin), db: Session = Depends(get_db)) -> list[dict]:
    return admin_copilot.agents(db)


@router.get("/safety")
def get_safety(_: User = Depends(_admin)) -> dict:
    return admin_copilot.get_safety_state()


@router.post("/safety")
def set_safety(body: SafetyRequest, _: User = Depends(_admin)) -> dict:
    return admin_copilot.set_safety_state(execution_enabled=body.execution_enabled, read_only=body.read_only)


@router.post("/rag-backfill")
def rag_backfill(_: User = Depends(_admin)) -> dict:
    """Re-render database rows into the RAG corpus on demand."""
    from app.services.rag.backfill import backfill_from_db

    stats = backfill_from_db()
    return {"ok": True, **stats}


# ---------------------------------------------------------------------------
# Management
# ---------------------------------------------------------------------------
@router.get("/users")
def users(_: User = Depends(_admin), db: Session = Depends(get_db)) -> list[dict]:
    return admin_intelligence.list_users(db)


@router.post("/users")
def create_user(body: UserCreate, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return admin_intelligence.create_user(
            db, actor=user.username, username=body.username, password=body.password,
            role=body.role, email=body.email,
        )
    except ValueError as exc:
        raise _raise400(exc)


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return admin_intelligence.update_user(
            db, actor=user.username, user_id=user_id, role=body.role,
            is_active=body.is_active, password=body.password,
        )
    except ValueError as exc:
        raise _raise400(exc)


@router.get("/announcements")
def announcements(_: User = Depends(_announcer), db: Session = Depends(get_db)) -> list[dict]:
    return admin_intelligence.list_announcements(db)


@router.post("/announcements")
def create_announcement(body: AnnouncementCreate, user: User = Depends(_announcer),
                        db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.create_announcement(
        db, actor=user.username, actor_role=user.role, title=body.title, body=body.body,
        audience=body.audience, pinned=body.pinned,
    )


@router.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, user: User = Depends(_announcer),
                        db: Session = Depends(get_db)) -> dict:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="announcement not found")
    if user.role != "admin" and announcement.created_by != user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete announcements you created.",
        )
    try:
        return admin_intelligence.delete_announcement(db, actor=user.username, announcement_id=announcement_id)
    except ValueError as exc:
        raise _raise400(exc)


@router.get("/resources")
def resources(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.list_resources(db)


@router.post("/resources")
def create_resource(body: ResourceCreate, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.create_resource(
        db, actor=user.username, name=body.name, resource_type=body.resource_type,
        capacity=body.capacity, location=body.location, status=body.status,
        utilization=body.utilization, notes=body.notes,
    )


@router.patch("/resources/{resource_id}")
def update_resource(resource_id: str, body: ResourceUpdate, user: User = Depends(_admin),
                    db: Session = Depends(get_db)) -> dict:
    try:
        return admin_intelligence.update_resource(
            db, actor=user.username, resource_id=resource_id, status=body.status, utilization=body.utilization,
        )
    except ValueError as exc:
        raise _raise400(exc)


@router.get("/backups")
def backups(_: User = Depends(_admin), db: Session = Depends(get_db)) -> list[dict]:
    return admin_intelligence.list_backups(db)


@router.post("/backups")
def create_backup(user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.create_backup(db, actor=user.username, note="on-demand from dashboard")


@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return admin_intelligence.restore_backup(db, actor=user.username, backup_id=backup_id)
    except ValueError as exc:
        raise _raise400(exc)


@router.get("/models")
def models(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.list_models(db)


@router.post("/models")
def register_model(body: ModelRegister, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.register_model(
        db, actor=user.username, name=body.name, version=body.version, path=body.path, metrics=body.metrics,
    )


@router.post("/models/{model_id}/activate")
def activate_model(model_id: str, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return admin_intelligence.set_model_active(db, actor=user.username, model_id=model_id)
    except ValueError as exc:
        raise _raise400(exc)


@router.get("/research")
def research(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.research_dashboard(db)


@router.post("/research")
def create_project(body: ResearchProjectCreate, user: User = Depends(_admin),
                   db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.create_project(
        db, actor=user.username, title=body.title, lead_name=body.lead_name,
        department=body.department, status=body.status, funding_amount=body.funding_amount,
        publications=body.publications, start_year=body.start_year,
    )


@router.get("/industry")
def industry(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.industry_intelligence(db)


@router.post("/industry")
def create_partner(body: IndustryPartnerCreate, user: User = Depends(_admin),
                   db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.create_partner(
        db, actor=user.username, name=body.name, sector=body.sector,
        contact_person=body.contact_person, mous=body.mous, active=body.active,
        placement_hires=body.placement_hires,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@router.get("/analytics/students")
def analytics_students(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.student_analytics(db)


@router.get("/analytics/faculty")
def analytics_faculty(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.faculty_analytics(db)


@router.get("/analytics/placement")
def analytics_placement(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.placement_overview(db)


@router.get("/analytics/kpis")
def analytics_kpis(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.kpi_dashboard(db)


@router.get("/analytics/dropout")
def analytics_dropout(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.dropout_analytics(db)


@router.get("/analytics/curriculum")
def analytics_curriculum(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.curriculum_intelligence(db)


@router.get("/analytics/enrollment-forecast")
def analytics_enrollment_forecast(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.enrollment_forecast(db)


@router.get("/analytics/accreditation")
def analytics_accreditation(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.accreditation(db)


@router.get("/system-health")
def system_health(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.system_health(db)


@router.get("/governance")
def governance(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_intelligence.governance_center(db)


# ---------------------------------------------------------------------------
# AI Admin Copilot
# ---------------------------------------------------------------------------
@router.post("/copilot")
def copilot(body: CopilotRequest, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_ai_tools.admin_copilot(db, question=body.question, actor=user.username)


# ---------------------------------------------------------------------------
# University Digital Twin
# ---------------------------------------------------------------------------
@router.get("/digital-twin")
def digital_twin(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_ai_tools.university_digital_twin(db)


@router.post("/digital-twin/scenarios")
def run_scenario(body: ScenarioRequest, _: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_ai_tools.run_scenario(
        db,
        attendance_delta=body.attendance_delta,
        pass_rate_delta=body.pass_rate_delta,
        placement_delta=body.placement_delta,
        readiness_delta=body.readiness_delta,
        interventions=body.interventions,
    )


# ---------------------------------------------------------------------------
# AI Timetable Optimization
# ---------------------------------------------------------------------------
@router.get("/timetable/conflicts")
def timetable_conflicts(_: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    return admin_ai_tools.timetable_conflicts(db)


@router.post("/timetable/optimize")
def timetable_optimize(body: TimetableOptimizeRequest, _: User = Depends(_admin),
                       db: Session = Depends(get_db)) -> dict:
    try:
        return admin_ai_tools.optimize_timetable(
            db, commit=body.commit, start_hour=body.start_hour,
            end_hour=body.end_hour, slot_minutes=body.slot_minutes,
        )
    except ValueError as exc:
        raise _raise400(exc)


# ---------------------------------------------------------------------------
# AI Evaluation Center
# ---------------------------------------------------------------------------
@router.post("/evaluation")
def evaluation(body: EvaluationRequest, user: User = Depends(_admin), db: Session = Depends(get_db)) -> dict:
    result = admin_ai_tools.evaluate_answer(
        db, course_code=body.course_code, question=body.question,
        rubric=body.rubric, answer=body.answer, max_marks=body.max_marks,
    )
    from app.core.audit import record_event

    record_event(
        db, actor=user.username, action="evaluation_completed", entity_type="evaluation",
        payload={"course_code": result.get("course_code", ""), "total_marks": result.get("total_marks"),
                 "max_marks": result.get("max_marks")},
    )
    return result
