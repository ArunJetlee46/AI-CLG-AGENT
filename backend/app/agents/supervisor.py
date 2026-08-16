import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.agents.academic_ops import AcademicOpsAgent
from app.agents.debate import debate_node
from app.agents.execute import ExecuteAgent
from app.agents.memory import get_memory, memory_node
from app.agents.specialists import KnowledgeAgent, ResourceOptimizerAgent, StudentSuccessAgent
from app.agents.state import AgentState
from app.config import get_settings
from app.core.audit import create_decision_card, record_event
from app.db import SessionLocal
from app.models.entities import ApprovalRequest, AuditLog
from app.services.llm import get_llm_gateway

logger = logging.getLogger(__name__)
settings = get_settings()

academic = AcademicOpsAgent()
success = StudentSuccessAgent()
resources = ResourceOptimizerAgent()
knowledge = KnowledgeAgent()

INTENTS = ("academic", "success", "resources", "knowledge")
ROUTER_DOMAINS = ("risk", "timetable", "graph", "course", "exam", "attendance")


def _classify(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ("risk", "predict", "at-risk", "dropout", "success")):
        return "success"
    if any(k in lowered for k in ("timetable", "schedule", "room", "conflict", "utilization", "overload")):
        return "resources"
    if any(k in lowered for k in ("graph", "cypher", "lecturer", "department", "who teaches", "overloaded")):
        return "knowledge"
    return "academic"


def _classify_with_llm(text: str) -> str | None:
    """LLM intent classification. Returns None on any failure so the caller
    falls back to the deterministic keyword rules (offline guarantee)."""
    try:
        response = get_llm_gateway().complete(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an intent router for a university AI assistant. Classify the user's "
                        f"query into EXACTLY one of: {', '.join(INTENTS)}. "
                        "academic = courses, curriculum, registration, exams, syllabi; "
                        "success = student risk, predictions, dropout, at-risk, study plans; "
                        "resources = timetable, schedule, rooms, conflicts, utilization; "
                        "knowledge = knowledge-graph, departments, lecturers, who-teaches queries. "
                        "Reply with the single intent name and nothing else."
                    ),
                },
                {"role": "user", "content": text[:1000]},
            ]
        )
        if response.provider == "local-fallback":
            return None
        lowered = response.content.strip().lower()
        for intent in INTENTS:
            if intent in lowered.split():
                return intent
        return None
    except Exception as exc:  # noqa: BLE001 - LLM routing is best-effort
        logger.warning("LLM intent routing failed (%s); using keyword rules", exc)
        return None


def router_node(state: AgentState) -> AgentState:
    text = state["messages"][-1]["content"]
    intent: str | None = None
    if settings.llm_router_enabled:
        intent = _classify_with_llm(text)
    state["intent"] = intent or _classify(text)
    return state


def planner_node(state: AgentState) -> AgentState:
    """Decomposes the request into ordered execution steps.

    Domains are detected by an LLM call when enabled (llm_router_enabled) and
    fall back to keyword matching; the plan itself stays deterministic. The
    plan is audited with the decision card.
    """
    text = state["messages"][-1]["content"]
    lowered = text.lower()
    domains = _detect_domains(text, lowered)
    state["plan"] = ["classify", "execute", "reflect"] + (["debate"] if state.get("intent") == "success" else [])
    if len(domains) > 1:
        state["plan"].insert(0, f"multi-domain:{'+'.join(domains)}")
    return state


def _detect_domains(text: str, lowered: str) -> list[str]:
    """Domains present in the query (LLM-assisted, keyword fallback)."""
    if settings.llm_router_enabled:
        try:
            response = get_llm_gateway().complete(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a planner. From this list of domains: "
                            f"{', '.join(ROUTER_DOMAINS)}, reply with the comma-separated "
                            "subset relevant to the user's query. If none, reply 'none'."
                        ),
                    },
                    {"role": "user", "content": text[:1000]},
                ]
            )
            if response.provider != "local-fallback":
                found = [d for d in ROUTER_DOMAINS if d in response.content.lower().replace(" ", "")]
                if found:
                    return found
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM planning failed (%s); using keyword domains", exc)
    return [d for d in ROUTER_DOMAINS if d in lowered]


def reflect_node(state: AgentState) -> AgentState:
    """Self-critique pass before finalization (Phase 8 reflection node).

    Rule-based checks: answer presence, admitted uncertainty, citation coverage,
    approval gating. Produces findings + a base confidence used by the debate
    node; appends a visible self-check note only for knowledge answers.
    """
    answer = state.get("answer", "")
    findings: list[str] = []
    confidence = 0.95

    if not answer:
        findings.append("empty answer produced")
        confidence -= 0.40
    elif any(marker in answer.lower() for marker in ("i don't know", "cannot answer", "not reachable", "unavailable")):
        findings.append("agent admitted uncertainty")
        confidence -= 0.15
    if state.get("requires_approval"):
        confidence = min(confidence, 0.70)
    if state.get("intent") in ("academic", "knowledge") and not state.get("citations"):
        findings.append("no citations attached to factual answer")
        confidence -= 0.10

    state["reflection"] = findings
    state["confidence"] = round(max(0.1, confidence), 2)
    if findings and state.get("intent") == "knowledge":
        state["answer"] = f"{answer}\n[self-check: {'; '.join(findings)}]"
    return state


def terminal_node(state: AgentState) -> AgentState:
    events = state.get("audit_events", [])
    if not events:
        return state
    db = SessionLocal()
    try:
        for event in events:
            record_event(
                db,
                actor=state.get("actor", "system"),
                action=event["action"],
                entity_type=event.get("entity_type", "agent"),
                entity_id=event.get("entity_id"),
                payload=event.get("payload", {}),
            )
        if state.get("requires_approval"):
            approval = ApprovalRequest(
                intent=state.get("data", {}).get("action", "register"),
                payload=state.get("data", {}),
                user_id=state.get("actor_id", ""),
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)
            state["approval_id"] = approval.id
            state["answer"] += f"\nApproval request #{approval.id[:8]} created."

        latest_audit = db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        if latest_audit is not None:
            card_inputs = dict(state.get("data", {}))
            card_inputs["confidence"] = state.get("confidence")
            card_inputs["reflection"] = state.get("reflection")
            card_inputs["debate"] = state.get("debate")
            card = create_decision_card(
                db,
                audit_log_id=latest_audit.id,
                decision_type=state.get("intent", "general"),
                inputs=card_inputs,
                reasoning=state.get("answer", "")[:2000],
            )
            state["decision_card_id"] = card.id
    finally:
        db.close()
    return state


class SupervisorGraph:
    """LangGraph state machine:

    START -> memory -> router -> planner -> specialist -> reflect
          -> (conditional) debate | terminal -> END
    """

    def __init__(self) -> None:
        builder = StateGraph(AgentState)
        builder.add_node("memory", memory_node)
        builder.add_node("router", router_node)
        builder.add_node("planner", planner_node)
        builder.add_node("academic", academic.run)
        builder.add_node("success", success.run)
        builder.add_node("resources", resources.run)
        builder.add_node("knowledge", knowledge.run)
        builder.add_node("reflect", reflect_node)
        builder.add_node("debate", debate_node)
        builder.add_node("terminal", terminal_node)

        builder.add_edge(START, "memory")
        builder.add_edge("memory", "router")
        builder.add_edge("router", "planner")
        builder.add_conditional_edges(
            "planner",
            lambda s: s["intent"],
            {
                "academic": "academic",
                "success": "success",
                "resources": "resources",
                "knowledge": "knowledge",
            },
        )
        for agent in ("academic", "success", "resources", "knowledge"):
            builder.add_edge(agent, "reflect")
        builder.add_conditional_edges(
            "reflect",
            lambda s: "debate" if s.get("intent") == "success" else "terminal",
            {"debate": "debate", "terminal": "terminal"},
        )
        builder.add_edge("debate", "terminal")
        builder.add_edge("terminal", END)

        self.graph = builder.compile()

    def invoke(self, message: str, *, actor: str = "system", actor_id: str = "") -> AgentState:
        initial: AgentState = {
            "messages": [{"role": "user", "content": message}],
            "audit_events": [],
            "actor": actor,
            "actor_id": actor_id,
            "requires_approval": False,
        }
        state = self.graph.invoke(initial)
        memory = get_memory()
        memory.add(actor, "user", message)
        if state.get("answer"):
            memory.add(actor, "assistant", state["answer"])
        return state

    async def stream(self, message: str, *, actor: str = "system", actor_id: str = "") -> AsyncGenerator[dict, None]:
        """Runs the graph, yielding SSE-friendly events as it goes (Tier 1.5):

        - intent:   classified intent + plan (as soon as the router/planner run)
        - chunk:    word-bursts of the final answer (typewriter effect)
        - meta:     full result metadata (citations, provider, approval, card id)

        The graph itself is synchronous; LangGraph's `astream` drives it on the
        event loop and yields the accumulated state after every super-step.
        """
        initial: AgentState = {
            "messages": [{"role": "user", "content": message}],
            "audit_events": [],
            "actor": actor,
            "actor_id": actor_id,
            "requires_approval": False,
        }
        state = initial
        intent_emitted = False
        async for state in self.graph.astream(initial, stream_mode="values"):
            if state.get("intent") and not intent_emitted:
                yield {"type": "intent", "intent": state["intent"], "plan": state.get("plan", [])}
                intent_emitted = True

        memory = get_memory()
        memory.add(actor, "user", message)
        answer = state.get("answer", "")
        if answer:
            memory.add(actor, "assistant", answer)
            for i in range(0, len(answer), 8):
                yield {"type": "chunk", "content": answer[i : i + 8]}
                await asyncio.sleep(0.005)
        yield {
            "type": "meta",
            "intent": state.get("intent", "academic"),
            "agent": state.get("agent", "unknown"),
            "citations": state.get("citations", []),
            "requires_approval": bool(state.get("requires_approval")),
            "approval_id": state.get("approval_id"),
            "decision_card_id": state.get("decision_card_id"),
            "provider": state.get("provider", ""),
            "model": state.get("model", ""),
        }


def approve_request(request_id: str, *, decision: str, admin_user_id: str, comment: str = "") -> dict:
    """HITL gate: marks the request decided, then hands the approved write to the
    Execute Agent - the only writer - whose gated services enforce the approval."""
    db = SessionLocal()
    try:
        approval = db.execute(select(ApprovalRequest).where(ApprovalRequest.id == request_id)).scalar_one_or_none()
        if approval is None:
            return {"ok": False, "error": "approval request not found"}
        if approval.status != "pending":
            return {"ok": False, "error": f"request already {approval.status}"}

        if decision == "approve":
            approval.status = "approved"
            approval.decided_at = datetime.now(timezone.utc)
            db.commit()
            record_event(
                db,
                actor=admin_user_id,
                action="approval_approve",
                entity_type="approval_request",
                entity_id=request_id,
                approval_id=request_id,
                payload={"comment": comment},
            )
            try:
                result = ExecuteAgent().apply(db, approval, admin_user_id)
            except Exception as exc:  # noqa: BLE001
                approval.status = "failed"
                db.commit()
                record_event(
                    db,
                    actor=admin_user_id,
                    action="approval_failed",
                    entity_type="approval_request",
                    entity_id=request_id,
                    approval_id=request_id,
                    payload={"error": str(exc), "comment": comment},
                )
                logger.warning("Approved request %s failed to execute: %s", request_id, exc)
                return {"ok": False, "error": f"execution failed: {exc}"}
            return {"ok": True, "message": result["message"]}

        approval.status = decision
        approval.decided_at = datetime.now(timezone.utc)
        record_event(
            db,
            actor=admin_user_id,
            action=f"approval_{decision}",
            entity_type="approval_request",
            entity_id=request_id,
            approval_id=request_id,
            payload={"comment": comment},
        )
        db.commit()
        return {"ok": True, "message": "Rejected. No changes applied."}
    finally:
        db.close()


_supervisor: SupervisorGraph | None = None


def get_supervisor() -> SupervisorGraph:
    global _supervisor
    if _supervisor is None:
        _supervisor = SupervisorGraph()
    return _supervisor
