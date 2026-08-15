import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

MAX_HISTORY_PER_ACTOR = 20
CONTEXT_TURNS = 6


class ConversationMemory:
    """In-process shared memory: per-actor recent turns.

    Long-term persistence across restarts is delegated to Postgres (🔜) - the
    memory node reads from this store, the supervisor writes back after each run.
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


_memory: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory


def memory_node(state: dict[str, Any], memory: ConversationMemory | None = None) -> dict[str, Any]:
    """Loads recent turns for the current actor into the state (shared memory)."""
    actor = state.get("actor", "")
    state["memory"] = (memory or get_memory()).recent(actor)
    return state
