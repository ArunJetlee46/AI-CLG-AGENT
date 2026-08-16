import logging
import threading
from typing import Any

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.entities import AgentMemory

logger = logging.getLogger(__name__)

MAX_HISTORY_PER_ACTOR = 20
CONTEXT_TURNS = 6


class ConversationMemory:
    """In-process shared memory: per-actor recent turns.

    Long-term persistence across restarts is delegated to the DB via
    `PersistentConversationMemory` - the memory node reads from the store, the
    supervisor writes back after each run. This plain class is the in-memory
    fallback and unit-test target.
    """

    def __init__(self, max_turns: int = MAX_HISTORY_PER_ACTOR) -> None:
        self._lock = threading.RLock()
        self._history: dict[str, list[dict[str, str]]] = {}
        self._max_turns = max_turns

    def add(self, actor: str, role: str, content: str) -> None:
        if not actor:
            return
        with self._lock:
            turns = self._history.setdefault(actor, [])
            turns.append({"role": role, "content": content})
            if len(turns) > self._max_turns:
                del turns[: len(turns) - self._max_turns]

    def recent(self, actor: str, turns: int = CONTEXT_TURNS) -> list[dict[str, str]]:
        with self._lock:
            return self._history.get(actor, [])[-turns:]

    def clear(self, actor: str) -> None:
        with self._lock:
            self._history.pop(actor, None)


class PersistentConversationMemory(ConversationMemory):
    """DB-backed conversation memory (Tier 1.4).

    Every turn is written to the `agent_memory` table and trimmed to the newest
    `MAX_HISTORY_PER_ACTOR` per actor, so conversations survive process
    restarts. The in-process dict from the base class is kept as a fast mirror
    and used as the fallback whenever the DB is unavailable.
    """

    def add(self, actor: str, role: str, content: str) -> None:
        super().add(actor, role, content)
        if not actor:
            return
        db = SessionLocal()
        try:
            db.add(AgentMemory(actor=actor, role=role, content=content))
            stale_ids = [
                row.id
                for row in db.execute(
                    select(AgentMemory.id)
                    .where(AgentMemory.actor == actor)
                    .order_by(AgentMemory.created_at.desc())
                    .offset(MAX_HISTORY_PER_ACTOR)
                ).scalars()
            ]
            if stale_ids:
                db.execute(delete(AgentMemory).where(AgentMemory.id.in_(stale_ids)))
            db.commit()
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            db.rollback()
            logger.warning("agent memory persist failed (%s); in-process only", exc)
        finally:
            db.close()

    def recent(self, actor: str, turns: int = CONTEXT_TURNS) -> list[dict[str, str]]:
        try:
            db = SessionLocal()
            try:
                rows = list(
                    db.execute(
                        select(AgentMemory)
                        .where(AgentMemory.actor == actor)
                        .order_by(AgentMemory.created_at.desc())
                        .limit(turns)
                    ).scalars()
                )
            finally:
                db.close()
            if rows:
                return [{"role": r.role, "content": r.content} for r in reversed(rows)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent memory read failed (%s); in-process fallback", exc)
        return super().recent(actor, turns)

    def clear(self, actor: str) -> None:
        super().clear(actor)
        db = SessionLocal()
        try:
            db.execute(delete(AgentMemory).where(AgentMemory.actor == actor))
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning("agent memory clear failed (%s)", exc)
        finally:
            db.close()


_memory: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = PersistentConversationMemory()
    return _memory


def memory_node(state: dict[str, Any], memory: ConversationMemory | None = None) -> dict[str, Any]:
    """Loads recent turns for the current actor into the state (shared memory)."""
    actor = state.get("actor", "")
    state["memory"] = (memory or get_memory()).recent(actor)
    return state
