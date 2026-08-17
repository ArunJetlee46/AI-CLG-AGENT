import json
import logging
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.supervisor import get_supervisor
from app.api.deps import get_current_user
from app.config import get_settings
from app.core.audit import record_event
from app.core.ratelimit import limiter
from app.db import get_db, SessionLocal
from app.models.entities import Student, User
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])
settings = get_settings()


def _caller_student_id(db: Session, user: User) -> str:
    """Personalize chat for genuine students: a linked Student row or a username
    that matches a Student id. Admins/lecturers get no personalization."""
    if user.student is not None:
        return user.student.student_id
    linked = db.execute(select(Student.student_id).where(Student.student_id == user.username)).scalar_one_or_none()
    return linked or ""


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _stream_chat(body: ChatRequest, user: User, student_id: str) -> StreamingResponse:
    """SSE generator: runs the supervisor pipeline in a worker thread and relays
    answer tokens as they arrive, then emits a final done event."""

    def _run(events: queue.Queue) -> None:
        state: dict | None = None
        try:
            state = get_supervisor().invoke(
                body.message,
                actor=user.username,
                actor_id=user.id,
                student_id=student_id,
                session_id=body.session_id,
                on_token=lambda token: events.put(("token", token)),
            )
            events.put(("done", state))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed for %s", user.username)
            events.put(("error", str(exc)))
        finally:
            audit_db = SessionLocal()
            try:
                record_event(
                    audit_db,
                    actor=user.username,
                    action="chat_completed",
                    entity_type="chat",
                    payload={"intent": state.get("intent"), "agent": state.get("agent")}
                    if state
                    else {},
                )
            except Exception:  # noqa: BLE001 - audit must never break the stream
                logger.warning("Failed to audit streaming chat for %s", user.username)
            finally:
                audit_db.close()

    def _stream():
        events: queue.Queue = queue.Queue()
        worker = threading.Thread(target=_run, args=(events,), daemon=True)
        worker.start()
        while True:
            kind, payload = events.get()
            if kind == "token":
                yield _sse({"type": "chunk", "content": payload})
            elif kind == "error":
                yield _sse({"type": "error", "message": payload})
                break
            elif kind == "done":
                state = payload
                yield _sse(
                    {
                        "type": "done",
                        "intent": state.get("intent", "academic"),
                        "agent": state.get("agent", "unknown"),
                        "answer": state.get("answer", "No response."),
                        "citations": state.get("citations", []),
                        "requires_approval": bool(state.get("requires_approval")),
                        "approval_id": state.get("approval_id"),
                        "decision_card_id": state.get("decision_card_id"),
                        "provider": state.get("provider", ""),
                        "model": state.get("model", ""),
                    }
                )
                break
        worker.join()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.chat_rate_limit)
def chat(request: Request, body: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student_id = _caller_student_id(db, user)
    if body.stream:
        return _stream_chat(body, user, student_id)

    state = get_supervisor().invoke(
        body.message,
        actor=user.username,
        actor_id=user.id,
        student_id=student_id,
        session_id=body.session_id,
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


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    """Server-Sent-Events stream of the agent run (Tier 1.5).

    Events (one JSON object per `data:` line): `intent`, `chunk` (answer
    bursts), `meta` (final metadata), or `error`. The blocking `/chat` endpoint
    remains as the non-streaming fallback.
    """

    supervisor = get_supervisor()

    async def event_source():
        try:
            async for event in supervisor.stream(body.message, actor=user.username, actor_id=user.id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 - stream must never die silently
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        finally:
            db = SessionLocal()
            try:
                record_event(
                    db,
                    actor=user.username,
                    action="chat_streamed",
                    entity_type="chat",
                    payload={"message": body.message[:200]},
                )
            finally:
                db.close()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
