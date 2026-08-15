from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # conversation
    messages: list[dict[str, str]]
    memory: list[dict[str, str]]          # recent history loaded by memory node
    intent: str
    plan: list[str]                       # planner output: ordered execution steps
    # specialist output
    agent: str
    answer: str
    citations: list[str]
    data: dict[str, Any]
    # LLM provenance (which provider/model produced the answer)
    provider: str
    model: str
    # reflection & confidence
    reflection: list[str]                 # self-critique findings from reflect node
    confidence: float                     # fused 0..1 score
    # governance
    requires_approval: bool
    approval_id: str | None
    decision_card_id: str | None
    # debate (agent-to-agent validation)
    debate: dict[str, Any]                # transcript + fusion results
    # audit
    audit_events: list[dict[str, Any]]
    actor: str
    actor_id: str
