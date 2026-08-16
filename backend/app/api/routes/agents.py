from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.supervisor import get_supervisor
from app.api.deps import get_current_user
from app.core.audit import record_event
from app.db import get_db
from app.models.entities import Student, User
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/agents", tags=["agents"])


def _caller_student_id(db: Session, user: User) -> str:
    """Personalize chat for genuine students: a linked Student row or a username
    that matches a Student id. Admins/lecturers get no personalization."""
    if user.student is not None:
        return user.student.student_id
    linked = db.execute(select(Student.student_id).where(Student.student_id == user.username)).scalar_one_or_none()
    return linked or ""


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatResponse:
    supervisor = get_supervisor()
    state = supervisor.invoke(
        body.message,
        actor=user.username,
        actor_id=user.id,
        student_id=_caller_student_id(db, user),
    )
    record_event(
        db,
        actor=user.username,
        action="chat_completed",
        entity_type="chat",
        payload={
            "intent": state.get("intent"),
            "agent": state.get("agent"),
            "decision_card_id": state.get("decision_card_id"),
            "provider": state.get("provider"),
            "model": state.get("model"),
        },
    )
    return ChatResponse(
        intent=state.get("intent", "academic"),
        agent=state.get("agent", "unknown"),
        answer=state.get("answer", "No response."),
        citations=state.get("citations", []),
        requires_approval=bool(state.get("requires_approval")),
        approval_id=state.get("approval_id"),
        decision_card_id=state.get("decision_card_id"),
        provider=state.get("provider", ""),
        model=state.get("model", ""),
    )
