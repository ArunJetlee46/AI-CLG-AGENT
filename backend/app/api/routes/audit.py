import csv
import io

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import AuditLog, DecisionCard
from app.schemas.audit import AuditRow

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditRow])
def list_audit(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "lecturer")),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    return list(db.execute(stmt).scalars())


@router.get("/export")
def export_csv(
    actor: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> Response:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    rows = db.execute(stmt).scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "actor", "action", "entity_type", "entity_id", "approval_id", "payload", "hash", "created_at"])
    for row in rows:
        writer.writerow([row.id, row.actor, row.action, row.entity_type, row.entity_id, row.approval_id, row.payload, row.hash, row.created_at.isoformat()])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit.csv"})


@router.get("/decision-cards/{card_id}")
def get_decision_card(card_id: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))) -> dict:
    card = db.get(DecisionCard, card_id)
    if card is None:
        return {"error": "not found"}
    return {
        "id": card.id,
        "decision_type": card.decision_type,
        "inputs": card.inputs,
        "reasoning": card.reasoning,
        "model_version": card.model_version,
        "approver_id": card.approver_id,
        "decided_at": card.decided_at.isoformat(),
    }
