from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session
import json
import logging

from app.api.deps import get_current_user
from app.db import get_db
from app.models.entities import User
from app.services import notifications as notifications_service
from app.services.websocket_manager import manager, notify_user

logger = logging.getLogger(__name__)

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


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    from app.core.security import decode_access_token
    from app.db import SessionLocal

    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            await websocket.close(code=4004)
            return
    finally:
        db.close()

    await manager.connect(websocket, user_id)
    try:
        await notify_user(user_id, "connected", {"message": "Real-time notifications connected"})
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
