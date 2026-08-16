from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import User
from app.services import degree_audit as svc

router = APIRouter(prefix="/degree-audit", tags=["degree-audit"])


@router.get("/me")
def my_degree_audit(
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    from app.services.students import resolve_student
    student = resolve_student(db, user)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    audit = svc.compute_degree_audit(db, student)
    return audit


@router.get("/{student_id}")
def get_student_degree_audit(
    student_id: str,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
):
    audit = svc.get_degree_audit(db, student_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Student not found")
    return audit