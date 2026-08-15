from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.entities import User
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return notifications_service.list_notifications(db, user)


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    try:
        return notifications_service.mark_read(db, user, notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return notifications_service.mark_all_read(db, user)
