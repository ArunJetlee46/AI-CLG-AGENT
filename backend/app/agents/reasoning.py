"""LLM-gated agent reasoning helpers (router, planner, reflection, debate critic).

Every helper returns `None` when the LLM gateway is unavailable (all providers
down -> local-fallback) or returns an unparseable / out-of-vocabulary answer, so
callers always fall back to the deterministic rule-based logic.

LLM output is advisory only: it never opens new write paths - approvals, the
Execute Agent, and the audit trail are unchanged. The prompts are constrained to
a fixed vocabulary and the results are validated before use.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.services.rag.llm import LLMResponse, get_llm_gateway

logger = logging.getLogger(__name__)
settings = get_settings()

INTENTS = ("academic", "success", "resources", "knowledge", "placement", "attendance", "exam", "advising")
PLAN_STEPS = ("classify", "retrieve", "query_db", "analyze", "propose", "debate", "reflect", "execute")


def _safe_json(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _llm_ok(response: LLMResponse | None) -> bool:
    return response is not None and response.provider != "local-fallback"


def _stage_enabled(stage: str) -> bool:
    if not settings.agent_llm_reasoning:
        return False
    stages = {s.strip().lower() for s in settings.agent_llm_reasoning_stages.split(",") if s.strip()}
    return stage in stages


def _complete_json(system: str, user: str) -> dict | None:
    if not settings.agent_llm_reasoning:
        return None
    try:
        response = get_llm_gateway().complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=settings.llm_reasoning_max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - reasoning must never break the agent
        logger.warning("LLM reasoning call failed (%s); using rule fallback", exc)
        return None
    if not _llm_ok(response):
        return None
    parsed = _safe_json(response.content)
    return parsed if isinstance(parsed, dict) else None


def plan_intent(text: str) -> tuple[str | None, list[str] | None]:
    """Fused LLM intent + plan in a single call.

    Returns (intent, steps); either half is None when the gateway is down, the
    stage is disabled, or the output is out-of-vocabulary - callers fall back to
    the deterministic rules per half independently.
    """
    if not _stage_enabled("router"):
        return None, None
    result = _complete_json(
        "You are an intent router and planner for a university AI assistant. Pick exactly one intent from "
        f"{', '.join(INTENTS)} and an ordered plan using ONLY steps from: {', '.join(PLAN_STEPS)}. "
        "Routing is critical - the wrong intent sends the request to the wrong specialist. Examples:\n"
        "- 'which students are at risk of dropping out' -> success (risk/dropout/predictions)\n"
        "- 'build a conflict-free timetable for CS301' -> resources (timetable/rooms/conflicts)\n"
        "- 'who teaches CS301' -> knowledge (knowledge graph/lecturer/department)\n"
        "- 'what courses are offered next term' -> academic (courses/registration/catalog)\n"
        "- 'what is my placement readiness' -> placement (placement/job/career/readiness)\n"
        "- 'is my attendance below 75% in any course' -> attendance (attendance/absent)\n"
        "- 'generate practice questions for CS301' -> exam (exam/quiz/mock/practice)\n"
        "- 'am I eligible to take CS302' -> advising (prerequisites/eligibility)\n"
        'Reply with ONLY a JSON object: {"intent": "<one intent>", "steps": ["classify", "retrieve", "analyze"]}.',
        text[:500],
    )
    if not result:
        return None, None
    intent = str(result.get("intent", "")).strip().lower()
    intent = intent if intent in INTENTS else None

    steps: list[str] | None = None
    if _stage_enabled("planner"):
        raw = result.get("steps")
        if isinstance(raw, list) and raw:
            cleaned = [str(s).strip().lower() for s in raw]
            if not any(s not in PLAN_STEPS for s in cleaned):
                if "classify" not in cleaned:
                    cleaned.insert(0, "classify")
                steps = cleaned
    return intent, steps


def classify_intent(text: str) -> str | None:
    """LLM intent classification; returns one of INTENTS or None (use the rules)."""
    intent, _ = plan_intent(text)
    return intent


def build_plan(state: dict) -> list[str] | None:
    """LLM plan decomposition; returns whitelisted steps or None (use the rules)."""
    messages = state.get("messages") or []
    text = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    _, steps = plan_intent(text)
    return steps


def reflect_answer(state: dict) -> dict | None:
    """LLM self-critique over the produced answer; additive to deterministic checks."""
    if not _stage_enabled("reflect"):
        return None
    messages = state.get("messages") or []
    question = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    payload = {
        "question": question,
        "intent": state.get("intent", ""),
        "answer": (state.get("answer") or "")[:1500],
        "citations": state.get("citations") or [],
    }
    result = _complete_json(
        "You are a self-critique reviewer. Given the assistant's answer, identify problems such as "
        "unsupported claims, missing citations, admitted uncertainty, or off-topic content. "
        'Reply ONLY with JSON: {"issues": ["..."], "confidence_delta": 0.05}. '
        "confidence_delta is a positive float between 0 and 0.3 indicating how much to lower the "
        "confidence score; use 0.0 when the answer is solid.",
        json.dumps(payload, default=str)[:2500],
    )
    if not result:
        return None
    issues = result.get("issues")
    if not isinstance(issues, list):
        return None
    try:
        delta = min(0.30, max(0.0, float(result.get("confidence_delta", 0.0))))
    except (TypeError, ValueError):
        delta = 0.0
    if not issues and delta == 0.0:
        return None
    return {"issues": [str(i) for i in issues], "confidence_delta": delta}


def critique_claim(claim: dict) -> dict | None:
    """Independent LLM critic for the debate node; returns a verdict dict or None."""
    if not _stage_enabled("critic"):
        return None
    result = _complete_json(
        "You are an independent critic reviewing a risk claim made by another AI agent. Decide whether "
        "the claim is supported by the stated evidence. "
        'Reply ONLY with JSON: {"verdict": "agree|disagree|evidence_gap", "confidence": 0.0-1.0, '
        '"reasons": ["..."]}.',
        json.dumps(claim, default=str)[:2000],
    )
    if not result:
        return None
    verdict = str(result.get("verdict", "")).strip().lower()
    if verdict not in ("agree", "disagree", "evidence_gap"):
        return None
    try:
        confidence = min(1.0, max(0.0, float(result.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5
    reasons = result.get("reasons")
    return {
        "validator": "llm-critic",
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "reasons": [str(r) for r in reasons] if isinstance(reasons, list) else [],
    }
