import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AuditLog, DecisionCard


def _hash_chain(prev_hash: str, payload: dict, actor: str, approval_id: str | None = None) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str) + f"|{actor}|{approval_id or ''}|{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _last_hash(db: Session) -> str:
    row = db.execute(select(AuditLog.hash).order_by(AuditLog.created_at.desc()).limit(1)).scalar_one_or_none()
    return row or "GENESIS"


def record_event(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
    approval_id: str | None = None,
) -> AuditLog:
    payload = payload or {}
    prev = _last_hash(db)
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        approval_id=approval_id,
        payload=payload,
        prev_hash=prev,
        hash=_hash_chain(prev, payload, actor, approval_id),
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_decision_card(
    db: Session,
    *,
    audit_log_id: str,
    decision_type: str,
    inputs: dict[str, Any],
    reasoning: str,
    model_version: str = "",
    approver_id: str | None = None,
) -> DecisionCard:
    card = DecisionCard(
        audit_log_id=audit_log_id,
        decision_type=decision_type,
        inputs=inputs,
        reasoning=reasoning,
        model_version=model_version,
        approver_id=approver_id,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card
