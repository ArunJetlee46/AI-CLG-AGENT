"""LLM-gated agent reasoning tests (Phase B).

Covers the config-gated LLM router / planner / reflection / debate critic with
a stub gateway: rules are used when the gateway reports local-fallback or emits
unparseable output; the LLM path is used when it returns valid constrained JSON.
"""
import pytest

from app.agents import reasoning
from app.agents.debate import debate_node
from app.agents.supervisor import planner_node, reflect_node, router_node
from app.config import get_settings
from app.services.rag.llm import LLMResponse

settings = get_settings()


class _StubGateway:
    def __init__(self, *responses: str):
        self.responses = list(responses)
        self.calls: list[list[dict]] = []
        self.max_tokens: list[int | None] = []

    def complete(self, messages, tools=None, max_tokens=None):
        self.calls.append(messages)
        self.max_tokens.append(max_tokens)
        content = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        provider = "groq" if "[local-fallback]" not in content else "local-fallback"
        return LLMResponse(content=content, provider=provider, model="stub", latency_ms=0)


def _patch_gateway(monkeypatch, *responses: str) -> _StubGateway:
    stub = _StubGateway(*responses)
    monkeypatch.setattr(reasoning, "get_llm_gateway", lambda: stub)
    return stub


# ---------------------------------------------------------------------------
# classify_intent / plan_intent (fused router+planner)
# ---------------------------------------------------------------------------


def test_classify_falls_back_to_none_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    assert reasoning.classify_intent("who teaches CS301") is None


def test_classify_uses_llm_intent(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"intent": "knowledge"}')
    assert reasoning.classify_intent("who teaches CS301") == "knowledge"


def test_classify_rejects_out_of_vocabulary_intent(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"intent": "hack-the-campus"}')
    assert reasoning.classify_intent("anything") is None


def test_classify_ignores_non_json(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "I cannot answer that.")
    assert reasoning.classify_intent("anything") is None


def test_plan_intent_fuses_intent_and_steps_in_one_call(monkeypatch) -> None:
    stub = _patch_gateway(monkeypatch, '{"intent": "resources", "steps": ["classify", "analyze", "propose"]}')
    assert reasoning.plan_intent("build a timetable for CS301") == (
        "resources",
        ["classify", "analyze", "propose"],
    )
    assert len(stub.calls) == 1  # fused: one LLM call instead of two


def test_plan_intent_falls_back_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    assert reasoning.plan_intent("anything") == (None, None)


def test_plan_intent_planner_disabled_still_returns_intent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_llm_reasoning_stages", "router")
    _patch_gateway(monkeypatch, '{"intent": "success", "steps": ["classify", "analyze"]}')
    intent, steps = reasoning.plan_intent("who is at risk")
    assert intent == "success"
    assert steps is None  # planner stage off -> rules produce the plan


def test_reasoning_calls_are_max_tokens_capped(monkeypatch) -> None:
    stub = _patch_gateway(monkeypatch, '{"intent": "knowledge"}')
    reasoning.classify_intent("who teaches CS301")
    assert stub.max_tokens == [settings.llm_reasoning_max_tokens]


def test_router_uses_rules_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    state = {"messages": [{"role": "user", "content": "which students are at risk of dropping out"}]}
    router_node(state)
    assert state["intent"] == "success"
    assert state["llm_plan"] is None


def test_router_uses_llm_when_gateway_returns_intent(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"intent": "resources"}')
    state = {"messages": [{"role": "user", "content": "who teaches CS301"}]}
    router_node(state)
    assert state["intent"] == "resources"  # LLM overrides the keyword rule


def test_planner_reuses_router_llm_plan_single_call(monkeypatch) -> None:
    stub = _patch_gateway(monkeypatch, '{"intent": "academic", "steps": ["classify", "query_db"]}')
    state = {"messages": [{"role": "user", "content": "what courses exist"}]}
    router_node(state)
    planner_node(state)
    assert state["intent"] == "academic"
    assert state["plan"] == ["classify", "query_db"]
    assert len(stub.calls) == 1  # router+planner share one LLM call


def test_reasoning_disabled_skips_gateway(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_llm_reasoning", False)
    stub = _patch_gateway(monkeypatch, '{"intent": "knowledge"}')
    assert reasoning.classify_intent("who teaches CS301") is None
    assert stub.calls == []


# ---------------------------------------------------------------------------
# build_plan
# ---------------------------------------------------------------------------


def test_plan_uses_llm_steps(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"steps": ["classify", "query_db", "analyze"]}')
    plan = reasoning.build_plan({"messages": [{"role": "user", "content": "timetable for CS301"}]})
    assert plan == ["classify", "query_db", "analyze"]


def test_plan_rejects_unknown_steps(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"steps": ["classify", "drop_the_database"]}')
    assert reasoning.build_plan({"messages": [{"role": "user", "content": "x"}]}) is None


def test_plan_rejects_empty_or_garbage(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"steps": []}')
    assert reasoning.build_plan({"messages": [{"role": "user", "content": "x"}]}) is None


def test_planner_uses_rules_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    state = {"intent": "academic", "messages": [{"role": "user", "content": "what courses exist and what is the timetable"}]}
    planner_node(state)
    assert any("multi-domain" in step for step in state["plan"])


# ---------------------------------------------------------------------------
# reflect_answer / reflect_node
# ---------------------------------------------------------------------------


def test_reflect_uses_llm_findings(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"issues": ["no citations attached"], "confidence_delta": 0.1}')
    state = {"intent": "academic", "answer": "CS301 is offered.", "citations": [], "messages": [{"role": "user", "content": "x"}]}
    reflect_node(state)
    assert "no citations attached" in state["reflection"]


def test_reflect_keeps_deterministic_checks_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    state = {"intent": "knowledge", "answer": "Neo4j is not reachable right now.", "citations": []}
    reflect_node(state)
    assert any("admitted uncertainty" in f for f in state["reflection"])
    assert state["confidence"] < 0.9
    assert "[self-check:" in state["answer"]


def test_reflect_noop_when_llm_finds_nothing(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"issues": [], "confidence_delta": 0.0}')
    state = {"intent": "academic", "answer": "CS301 is offered next term.", "citations": ["[0] course"], "messages": [{"role": "user", "content": "x"}]}
    reflect_node(state)
    assert state["confidence"] == 0.95  # deterministic checks clean + LLM silent


# ---------------------------------------------------------------------------
# critique_claim / debate_node
# ---------------------------------------------------------------------------


def test_critique_uses_llm_verdict(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"verdict": "agree", "confidence": 0.8, "reasons": ["evidence supports"]}')
    result = reasoning.critique_claim({"risk_level": "high", "student_id": "STU00000"})
    assert result == {"validator": "llm-critic", "verdict": "agree", "confidence": 0.8, "reasons": ["evidence supports"]}


def test_critique_rejects_bad_verdict(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"verdict": "totally-unsupported", "confidence": 0.9}')
    assert reasoning.critique_claim({"risk_level": "high"}) is None


def test_critique_disabled_when_stage_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_llm_reasoning_stages", "router,planner,reflect")
    stub = _patch_gateway(monkeypatch, '{"verdict": "agree", "confidence": 0.8}')
    assert reasoning.critique_claim({"risk_level": "high"}) is None
    assert stub.calls == []


def test_debate_falls_back_to_sql_only_when_gateway_down(monkeypatch) -> None:
    _patch_gateway(monkeypatch, "[local-fallback] no provider reachable")
    state = {"confidence": 0.95, "agent": "success", "answer": "Student flagged high risk.",
             "data": {"top_risk": {"risk_level": "high"}}, "audit_events": []}
    debate_node(state)
    assert state["debate"]["validator_verdict"] == "evidence_gap"
    assert state["debate"]["critic_verdict"] is None
    assert state["confidence"] == 0.5 * 0.95 + 0.5 * 0.45
    assert state["requires_approval"] is True


def test_debate_fuses_llm_critic_when_gateway_up(monkeypatch) -> None:
    _patch_gateway(monkeypatch, '{"verdict": "agree", "confidence": 0.8, "reasons": ["ok"]}')
    state = {"confidence": 0.95, "agent": "success", "answer": "Student flagged high risk.",
             "data": {"top_risk": {"risk_level": "high"}}, "audit_events": []}
    debate_node(state)
    assert state["debate"]["validator_verdict"] == "evidence_gap"
    assert state["debate"]["critic_verdict"] == "agree"
    assert state["debate"]["critic_confidence"] == 0.8
    assert state["debate"]["fused_confidence"] == round(0.4 * 0.95 + 0.3 * 0.45 + 0.3 * 0.8, 3)
    assert state["requires_approval"] is True  # evidence gap escalates regardless of the critic
    assert any(e["action"] == "debate_validation" for e in state["audit_events"])


@pytest.mark.parametrize("bad", ['not json at all', '{"steps": 42}', '"just a string"'])
def test_helpers_tolerate_garbage(monkeypatch, bad) -> None:
    _patch_gateway(monkeypatch, bad)
    assert reasoning.classify_intent("x") is None
    assert reasoning.build_plan({"messages": [{"role": "user", "content": "x"}]}) is None
    assert reasoning.reflect_answer({"intent": "academic", "answer": "ok", "citations": []}) is None
    assert reasoning.critique_claim({"risk_level": "high"}) is None
