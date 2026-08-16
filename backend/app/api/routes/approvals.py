from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.supervisor import approve_request
from app.api.deps import require_role
from app.db import get_db
from app.models.entities import ApprovalRequest
from app.schemas.approval import ApprovalDecision

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals(status: str = "pending", db: Session = Depends(get_db), _=Depends(require_role("admin"))) -> list[dict]:
    stmt = select(ApprovalRequest).where(ApprovalRequest.status == status).order_by(ApprovalRequest.created_at.desc())
    return [
        {
            "id": a.id,
            "intent": a.intent,
            "payload": a.payload,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in db.execute(stmt).scalars()
    ]


@router.post("/{request_id}")
def decide(
    request_id: str,
    body: ApprovalDecision,
    user=Depends(require_role("admin", "lecturer")),
    db: Session = Depends(get_db),
) -> dict:
    if user.role == "lecturer":
        request = db.execute(select(ApprovalRequest).where(ApprovalRequest.id == request_id)).scalar_one_or_none()
        if request is None:
            raise HTTPException(status_code=404, detail="approval request not found")
        if request.intent != "intervention":
            raise HTTPException(status_code=403, detail="Lecturers may only decide intervention approvals")
        if request.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only decide interventions you proposed")
    result = approve_request(request_id, decision=body.decision, admin_user_id=user.id, comment=body.comment)
    if not result.get("ok"):
        raise HTTPException(status_code=404 if "not found" in result.get("error", "") else 409, detail=result["error"])
    return result
