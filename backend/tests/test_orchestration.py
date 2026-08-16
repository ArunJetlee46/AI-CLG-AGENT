from app.agents.debate import RiskSanityValidator, fuse_confidences
from app.agents.memory import ConversationMemory, PersistentConversationMemory, memory_node
from app.agents.supervisor import (
    _classify,
    _classify_with_llm,
    get_supervisor,
    planner_node,
    reflect_node,
    router_node,
)
from app.db import SessionLocal
from app.models.entities import AgentMemory
from app.services.llm import LLMResponse


def test_fusion_formula() -> None:
    fused = fuse_confidences([(0.9, 0.5), (0.8, 0.5)])
    assert abs(fused - 0.85) < 1e-9
    capped = fuse_confidences([(0.99, 0.5), (0.99, 0.5)])
    assert capped == 0.90


def test_shared_memory_roundtrip() -> None:
    mem = ConversationMemory(max_turns=10)
    mem.add("alice", "user", "hello")
    mem.add("alice", "assistant", "hi there")
    mem.add("bob", "user", "different conversation")
    recent = mem.recent("alice")
    assert [t["content"] for t in recent] == ["hello", "hi there"]
    assert len(mem.recent("bob")) == 1

    state = {"actor": "alice", "messages": []}
    memory_node(state, memory=mem)
    assert len(state["memory"]) == 2


def test_persistent_memory_survives_store_recreation() -> None:
    actor = f"persist-{id(__import__('sys').modules[__name__])}"
    store = PersistentConversationMemory()
    store.clear(actor)
    store.add(actor, "user", "which students are at risk?")
    store.add(actor, "assistant", "ADISTU02 is flagged high risk.")

    db = SessionLocal()
    try:
        persisted = db.execute(
            __import__("sqlalchemy").select(AgentMemory)
            .where(AgentMemory.actor == actor)
            .order_by(AgentMemory.created_at)
        ).scalars().all()
        assert len(persisted) == 2
    finally:
        db.close()

    fresh = PersistentConversationMemory()
    assert [t["content"] for t in fresh.recent(actor)] == [
        "which students are at risk?",
        "ADISTU02 is flagged high risk.",
    ]
    fresh.clear(actor)


def test_planner_decomposes_multi_domain() -> None:
    state = {"intent": "academic", "messages": [{"role": "user", "content": "what courses exist and what is the timetable"}]}
    planner_node(state)
    assert state["plan"]
    assert any("multi-domain" in step for step in state["plan"])


def test_reflect_node_scores_and_finds() -> None:
    state = {"intent": "knowledge", "answer": "Neo4j is not reachable right now.", "citations": []}
    reflect_node(state)
    assert any("admitted uncertainty" in f for f in state["reflection"])
    assert state["confidence"] < 0.9
    assert "[self-check:" in state["answer"]


def test_debate_escalates_on_evidence_gap() -> None:
    validator = RiskSanityValidator()
    result = validator.validate({"risk_level": "high"})  # no student_id -> evidence gap
    assert result["verdict"] in ("evidence_gap", "disagree")


def test_supervisor_runs_full_graph_with_new_nodes() -> None:
    supervisor = get_supervisor()
    state = supervisor.invoke("what courses are available?", actor="test-user")
    assert state["answer"]
    assert state["plan"]
    assert state["confidence"] is not None
    assert "reflection" in state

    # shared memory now holds the exchange for the actor
    from app.agents.memory import get_memory

    turns = get_memory().recent("test-user")
    assert len(turns) >= 2


def test_llm_router_uses_llm_when_confident(monkeypatch) -> None:
    class FakeGateway:
        def complete(self, messages, tools=None):
            return LLMResponse(
                content="resources", provider="groq", model="fake",
                latency_ms=1, tokens_in=0, tokens_out=1,
            )

    monkeypatch.setattr("app.agents.supervisor.get_llm_gateway", lambda: FakeGateway())
    state = {"messages": [{"role": "user", "content": "is the timetable overloaded?"}]}
    router_node(state)
    assert state["intent"] == "resources"


def test_llm_router_falls_back_to_keywords_on_local_fallback(monkeypatch) -> None:
    class FakeGateway:
        def complete(self, messages, tools=None):
            return LLMResponse(
                content="[local-fallback] no model available", provider="local-fallback",
                model="fallback", latency_ms=1, tokens_in=0, tokens_out=1,
            )

    monkeypatch.setattr("app.agents.supervisor.get_llm_gateway", lambda: FakeGateway())
    state = {"messages": [{"role": "user", "content": "which students are at risk of dropout?"}]}
    router_node(state)
    assert state["intent"] == "success"


def test_llm_router_returns_none_on_garbage(monkeypatch) -> None:
    class FakeGateway:
        def complete(self, messages, tools=None):
            return LLMResponse(
                content="no idea what you mean", provider="gemini", model="fake",
                latency_ms=1, tokens_in=0, tokens_out=1,
            )

    monkeypatch.setattr("app.agents.supervisor.get_llm_gateway", lambda: FakeGateway())
    assert _classify_with_llm("hello") is None
    assert _classify("hello") == "academic"
