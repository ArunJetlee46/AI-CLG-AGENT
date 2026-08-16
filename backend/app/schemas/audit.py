from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    approval_id: str | None = None
    payload: dict[str, Any] = {}
    hash: str
    created_at: datetime


class AuditQuery(BaseModel):
    actor: str | None = None
    action: str | None = None
    entity_type: str | None = None
    limit: int = 50
    offset: int = 0
