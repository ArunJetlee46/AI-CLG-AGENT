from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db import get_db
from app.models.entities import User
from app.services import intervention_effectiveness as svc

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("/effectiveness")
def list_effectiveness(
    student_id: str | None = Query(None),
    course_code: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=100),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
):
    return svc.list_intervention_effectiveness(db, student_id, course_code, status, limit)


@router.get("/effectiveness/{intervention_id}")
def get_effectiveness(
    intervention_id: str,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
):
    record = svc.get_intervention_effectiveness(db, intervention_id)
    if not record:
        raise HTTPException(status_code=404, detail="Effectiveness record not found")
    return record


@router.post("/effectiveness/{intervention_id}/followup")
def record_followup(
    intervention_id: str,
    followup_score: float = Query(..., ge=0, le=100),
    notes: str = Query(""),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
):
    record = svc.update_intervention_effectiveness(db, intervention_id, followup_score, notes)
    if not record:
        raise HTTPException(status_code=404, detail="Effectiveness record not found")
    return record


@router.get("/effectiveness/summary")
def get_summary(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return svc.get_effectiveness_summary(db)