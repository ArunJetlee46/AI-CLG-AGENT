"""Agent conversation memory.

Two layers:

- `ConversationMemory` is the fast in-process per-actor cache used by the graph
  nodes.
- The Postgres/SQLite-backed store (`persist_turn`, `load_recent`) keeps the
  last `MAX_HISTORY_PER_ACTOR` turns per (actor, session) so history survives
  process restarts. The supervisor persists every exchange after a run; the
  memory node reads from the DB first and falls back to the in-process cache.
"""

import logging
import threading
from typing import Any

from sqlalchemy import delete, func, select

logger = logging.getLogger(__name__)

MAX_HISTORY_PER_ACTOR = 20
CONTEXT_TURNS = 6


class ConversationMemory:
    """In-process shared memory: per-actor recent turns."""

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


# ---------------------------------------------------------------------------
# Persistent (database) store
# ---------------------------------------------------------------------------


def _conversation_key(actor: str, session_id: str | None) -> str:
    return f"{actor}|{session_id or ''}"


def _load_conversation_id(db, actor: str, session_id: str | None) -> str | None:
    from app.models.entities import Conversation

    conversation = db.execute(
        select(Conversation).where(
            Conversation.actor == actor,
            Conversation.session_id == (session_id or None),
        )
    ).scalar_one_or_none()
    return conversation.id if conversation is not None else None


def persist_turn(
    db,
    *,
    actor: str,
    role: str,
    content: str,
    session_id: str | None = None,
) -> None:
    """Append one turn to the persistent store, pruning to the most recent
    MAX_HISTORY_PER_ACTOR turns for the (actor, session) key."""
    if not actor or not content:
        return
    from app.models.entities import Conversation, ConversationMessage

    conversation = db.execute(
        select(Conversation).where(
            Conversation.actor == actor,
            Conversation.session_id == (session_id or None),
        )
    ).scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(actor=actor, session_id=session_id or None)
        db.add(conversation)
        db.flush()
    db.add(ConversationMessage(conversation_id=conversation.id, role=role, content=content))
    db.flush()  # autoflush is off; the prune query below must see this row

    overflow = (
        db.execute(
            select(ConversationMessage.id)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.id.desc())
            .offset(MAX_HISTORY_PER_ACTOR)
        )
        .scalars()
        .all()
    )
    for message_id in overflow:
        db.delete(db.get(ConversationMessage, message_id))
    db.commit()


def load_recent(
    db,
    *,
    actor: str,
    session_id: str | None = None,
    turns: int = CONTEXT_TURNS,
) -> list[dict[str, str]]:
    """Return the most recent `turns` messages for the (actor, session) key."""
    if not actor:
        return []
    conversation_id = _load_conversation_id(db, actor, session_id)
    if conversation_id is None:
        return []
    from app.models.entities import ConversationMessage

    rows = db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.id.desc())
        .limit(turns)
    ).scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def clear_history(db, *, actor: str, session_id: str | None = None) -> None:
    """Delete a (actor, session) conversation and all of its messages."""
    from app.models.entities import Conversation

    conversation = db.execute(
        select(Conversation).where(
            Conversation.actor == actor,
            Conversation.session_id == (session_id or None),
        )
    ).scalar_one_or_none()
    if conversation is not None:
        db.delete(conversation)
        db.commit()


def total_stored_turns(db) -> int:
    from app.models.entities import ConversationMessage

    return db.execute(select(func.count(ConversationMessage.id))).scalar_one()


def prune_actor(db, *, actor: str, keep: int = MAX_HISTORY_PER_ACTOR) -> None:
    """Bound stored history per actor across sessions."""
    from app.models.entities import Conversation, ConversationMessage

    conversation_ids = db.execute(select(Conversation.id).where(Conversation.actor == actor)).scalars().all()
    if not conversation_ids:
        return
    rows = (
        db.execute(
            select(ConversationMessage.id)
            .where(ConversationMessage.conversation_id.in_(conversation_ids))
            .order_by(ConversationMessage.id.desc())
            .offset(keep)
        )
        .scalars()
        .all()
    )
    if rows:
        db.execute(delete(ConversationMessage).where(ConversationMessage.id.in_(rows)))
        db.commit()


# ---------------------------------------------------------------------------
# node + singleton
# ---------------------------------------------------------------------------

_memory: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = PersistentConversationMemory()
    return _memory


def memory_node(state: dict[str, Any], memory: ConversationMemory | None = None) -> dict[str, Any]:
    """Loads recent turns for the current actor into the state.

    Reads the persistent store first (it survives restarts), then falls back to
    the in-process cache. An explicit `memory` argument (unit tests) bypasses
    the database entirely.
    """
    actor = state.get("actor", "")
    session_id = state.get("session_id")

    if memory is not None:
        state["memory"] = memory.recent(actor)
        return state

    try:
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            stored = load_recent(db, actor=actor, session_id=session_id)
        finally:
            db.close()
        if stored:
            state["memory"] = stored
            return state
    except Exception as exc:  # noqa: BLE001 - memory must never break the graph
        logger.warning("persistent memory load failed (%s); using in-process", exc)

    state["memory"] = get_memory().recent(actor)
    return state


def persist_exchange(
    *,
    actor: str,
    user_message: str,
    assistant_answer: str,
    session_id: str | None = None,
) -> None:
    """Persist a user/assistant exchange. Never raises - memory is best-effort."""
    try:
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            persist_turn(db, actor=actor, role="user", content=user_message, session_id=session_id)
            if assistant_answer:
                persist_turn(db, actor=actor, role="assistant", content=assistant_answer, session_id=session_id)
            prune_actor(db, actor=actor)
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("persistent memory write failed (%s)", exc)
