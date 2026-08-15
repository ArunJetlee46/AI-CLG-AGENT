from app.agents.debate import RiskSanityValidator, fuse_confidences
from app.agents.memory import ConversationMemory, memory_node
from app.agents.supervisor import get_supervisor, planner_node, reflect_node


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
