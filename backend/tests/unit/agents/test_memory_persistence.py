"""Theme B: persistent conversation memory.

The in-process cache is the fast path; the DB store (conversations /
conversation_messages) survives restarts and is what memory_node loads from.
"""

from app import agents
from app.agents.memory import (
    MAX_HISTORY_PER_ACTOR,
    clear_history,
    load_recent,
    memory_node,
    persist_exchange,
    persist_turn,
    total_stored_turns,
)
from app.agents.supervisor import SupervisorGraph, get_supervisor
from app.db import SessionLocal

ACTOR = "mem-actor"


def _db():
    return SessionLocal()


def test_persist_and_load_roundtrip_in_order() -> None:
    db = _db()
    try:
        clear_history(db, actor=ACTOR)
        persist_turn(db, actor=ACTOR, role="user", content="hello")
        persist_turn(db, actor=ACTOR, role="assistant", content="hi there")
        recent = load_recent(db, actor=ACTOR)
        assert [t["content"] for t in recent] == ["hello", "hi there"]
    finally:
        clear_history(db, actor=ACTOR)
        db.close()


def test_persist_is_scoped_by_session() -> None:
    db = _db()
    try:
        clear_history(db, actor=ACTOR)
        persist_turn(db, actor=ACTOR, role="user", content="thread-a", session_id="a")
        persist_turn(db, actor=ACTOR, role="user", content="thread-b", session_id="b")
        assert [t["content"] for t in load_recent(db, actor=ACTOR, session_id="a")] == ["thread-a"]
        assert [t["content"] for t in load_recent(db, actor=ACTOR, session_id="b")] == ["thread-b"]
        assert load_recent(db, actor=ACTOR) == []
    finally:
        clear_history(db, actor=ACTOR, session_id="a")
        clear_history(db, actor=ACTOR, session_id="b")
        db.close()


def test_persist_prunes_to_max_turns() -> None:
    db = _db()
    try:
        clear_history(db, actor=ACTOR)
        for i in range(MAX_HISTORY_PER_ACTOR + 5):
            persist_turn(db, actor=ACTOR, role="user", content=f"turn-{i}")
        recent = load_recent(db, actor=ACTOR, turns=MAX_HISTORY_PER_ACTOR + 5)
        assert len(recent) == MAX_HISTORY_PER_ACTOR
        assert recent[-1]["content"] == f"turn-{MAX_HISTORY_PER_ACTOR + 4}"
    finally:
        clear_history(db, actor=ACTOR)
        db.close()


def test_clear_history_removes_messages() -> None:
    db = _db()
    try:
        persist_turn(db, actor=ACTOR, role="user", content="x")
        assert total_stored_turns(db) >= 1
        clear_history(db, actor=ACTOR)
        assert load_recent(db, actor=ACTOR) == []
    finally:
        db.close()


def test_memory_node_loads_from_db() -> None:
    db = _db()
    try:
        clear_history(db, actor=ACTOR)
        persist_turn(db, actor=ACTOR, role="user", content="stored question")
        persist_turn(db, actor=ACTOR, role="assistant", content="stored answer")
        state = {"actor": ACTOR, "messages": []}
        memory_node(state)
        contents = [t["content"] for t in state["memory"]]
        assert "stored question" in contents
        assert "stored answer" in contents
    finally:
        clear_history(db, actor=ACTOR)
        db.close()


def test_memory_survives_process_restart() -> None:
    # exchange 1 (fresh in-process cache, persisted to DB)
    supervisor = SupervisorGraph()
    first = supervisor.invoke("what courses are available", actor="restart-user")
    assert first["answer"]

    # simulate a process restart: drop the in-process singleton
    agents.memory._memory = None

    second = get_supervisor().invoke("and the timetable?", actor="restart-user")
    contents = [t["content"] for t in second["memory"]]
    assert any("courses" in c for c in contents)

    agents.memory._memory = None
