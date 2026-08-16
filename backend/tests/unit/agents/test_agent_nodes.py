"""LangGraph node-level and end-to-end tests (Phase 12).

Node-level: router, memory (eviction), debate (escalation + fusion), terminal
(audit + decision card + approval request). End-to-end: full graph runs for
each intent, memory carries across turns, and approval escalation persists.
"""

from sqlalchemy import select

from app.agents.debate import debate_node, fuse_confidences
from app.agents.memory import ConversationMemory, memory_node
from app.agents.supervisor import SupervisorGraph, get_supervisor, router_node
from app.db import SessionLocal
from app.models.entities import ApprovalRequest, AuditLog, DecisionCard

INTENT_CASES = [
    ("which students are at risk of dropping out this semester", "success"),
    ("build a conflict-free timetable for CS301 using room 401", "resources"),
    ("who teaches CS301 and what is the cypher schema", "knowledge"),
    ("what courses are available next term", "academic"),
    ("what is my placement readiness for campus drives", "placement"),
    ("is my attendance below 75% in any course", "attendance"),
    ("generate practice questions for CS301", "exam"),
    ("am I eligible to take CS302", "advising"),
]


def test_router_classifies_all_intents() -> None:
    for text, expected in INTENT_CASES:
        state = {"messages": [{"role": "user", "content": text}]}
        router_node(state)
        assert state["intent"] == expected, f"{text!r} -> {state['intent']}"


def test_memory_evicts_oldest_turns() -> None:
    mem = ConversationMemory(max_turns=3)
    for i in range(5):
        mem.add("alice", "user", f"turn-{i}")
    recent = mem.recent("alice", turns=10)
    assert [t["content"] for t in recent] == ["turn-2", "turn-3", "turn-4"]

    state = {"actor": "alice", "messages": []}
    memory_node(state, memory=mem)
    assert [t["content"] for t in state["memory"]] == ["turn-2", "turn-3", "turn-4"]


def test_memory_is_per_actor() -> None:
    mem = ConversationMemory(max_turns=10)
    mem.add("a", "user", "x")
    state_b = {"actor": "b", "messages": []}
    memory_node(state_b, memory=mem)
    assert state_b["memory"] == []


def test_fusion_caps_at_ninety_percent() -> None:
    assert fuse_confidences([(0.99, 1.0)]) == 0.90
    assert fuse_confidences([(0.8, 0.5), (0.6, 0.5)]) == 0.70


def test_debate_escalates_on_evidence_gap_and_persists() -> None:
    state = {
        "confidence": 0.95,
        "agent": "success",
        "answer": "Student flagged high risk.",
        "data": {"top_risk": {"risk_level": "high"}},  # no student_id -> evidence gap
        "audit_events": [],
    }
    debate_node(state)
    assert state["debate"]["validator_verdict"] == "evidence_gap"
    assert state["debate"]["escalated"] is True
    assert state["requires_approval"] is True
    assert state["confidence"] == 0.5 * 0.95 + 0.5 * 0.45
    assert any(e["action"] == "debate_validation" for e in state["audit_events"])


def test_terminal_writes_audit_decision_card_and_approval() -> None:
    supervisor = get_supervisor()
    initial = {
        "messages": [{"role": "user", "content": "register me for CS301 and CS302"}],
        "actor": "e2e-terminal",
        "actor_id": "u-e2e",
        "intent": "academic",
        "requires_approval": True,
        "data": {"action": "register", "course_codes": ["CS301", "CS302"]},
        "audit_events": [{"action": "approval_requested", "entity_type": "agent", "payload": {"action": "register"}}],
    }
    state = supervisor.graph.invoke(initial)

    assert state["approval_id"]
    assert "Approval request" in state["answer"]
    assert state["decision_card_id"]

    db = SessionLocal()
    try:
        approval = db.get(ApprovalRequest, state["approval_id"])
        assert approval is not None and approval.status == "pending"
        assert approval.intent == "register"

        audit = db.execute(
            select(AuditLog).where(AuditLog.action == "approval_requested").order_by(AuditLog.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        assert audit is not None and audit.actor == "e2e-terminal"

        card = db.get(DecisionCard, state["decision_card_id"])
        assert card is not None and card.decision_type == "academic"
        assert card.inputs.get("action") == "register"
    finally:
        db.close()


def test_end_to_end_runs_for_every_intent() -> None:
    supervisor = SupervisorGraph()
    for text, expected in INTENT_CASES:
        state = supervisor.invoke(text, actor="e2e-every-intent")
        assert state["answer"], f"no answer for {text!r}"
        assert state["plan"]
        assert 0.0 <= state["confidence"] <= 1.0
        assert state["reflection"] is not None
        assert state["intent"] == expected


def test_end_to_end_memory_carries_across_turns() -> None:
    supervisor = SupervisorGraph()
    first = supervisor.invoke("what courses are available", actor="e2e-memory")
    assert first["answer"]

    second = supervisor.invoke("and the timetable?", actor="e2e-memory")
    # the memory node loaded the previous exchange before this run
    assert any(t["role"] == "user" and "courses" in t["content"] for t in second["memory"])


def test_end_to_end_risk_query_flows_through_debate() -> None:
    supervisor = SupervisorGraph()
    state = supervisor.invoke("which students are at risk of dropping out", actor="e2e-risk")
    assert state["intent"] == "success"
    assert "debate" in state and state["debate"]["rounds"] >= 1
    assert any(e["action"] == "debate_validation" for e in state.get("audit_events", []))
