import asyncio
import json
import logging
from typing import Dict, List, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.user_connections[id(websocket)] = user_id
        logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket):
        ws_id = id(websocket)
        user_id = self.user_connections.pop(ws_id, None)
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected. User {user_id} remaining connections: {len(self.active_connections.get(user_id, set()))}")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id not in self.active_connections:
            return
        dead_connections = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send message to {user_id}: {e}")
                dead_connections.add(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast(self, message: dict, exclude_users: List[str] = None):
        exclude = set(exclude_users or [])
        for user_id, connections in self.active_connections.items():
            if user_id in exclude:
                continue
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to broadcast to {user_id}: {e}")

    def get_connected_users(self) -> List[str]:
        return list(self.active_connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


manager = ConnectionManager()


async def notify_user(user_id: str, event: str, data: dict):
    """Send a notification to a specific user via WebSocket."""
    message = {
        "type": "notification",
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time(),
    }
    await manager.send_personal_message(message, user_id)


async def notify_role(role: str, event: str, data: dict):
    """Send a notification to all users with a specific role."""
    # This would need a way to get user IDs by role
    # For now, we'll broadcast to all and let clients filter
    message = {
        "type": "notification",
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time(),
        "target_role": role,
    }
    await manager.broadcast(message)


async def broadcast_system(event: str, data: dict):
    """Broadcast a system-wide notification."""
    message = {
        "type": "system",
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time(),
    }
    await manager.broadcast(message)