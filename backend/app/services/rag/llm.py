import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _httpx_timeout() -> httpx.Timeout:
    """Request timeout with a bounded CONNECT phase.

    A refused/unreachable provider must fail in ~2s (not the full read timeout),
    so the agent's rule-based fallback kicks in quickly when the LLM is down.
    """
    return httpx.Timeout(settings.llm_timeout_seconds, connect=2.0, pool=2.0)


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class _ProviderState:
    consecutive_failures: int = 0
    tripped_until: float = 0.0


class LLMGateway:
    """Fallback chain: Groq -> Gemini -> Ollama. Degrades to a deterministic
    rule-based responder when no provider is available (offline guarantee)."""

    def __init__(self) -> None:
        self._states: dict[str, _ProviderState] = {p: _ProviderState() for p in settings.llm_providers}
        self._all_down_until: float = 0.0

    def _is_tripped(self, name: str) -> bool:
        st = self._states[name]
        if st.tripped_until and time.time() < st.tripped_until:
            return True
        if st.tripped_until and time.time() >= st.tripped_until:
            st.consecutive_failures = 0
            st.tripped_until = 0.0
        return False

    def _record_failure(self, name: str) -> None:
        st = self._states[name]
        st.consecutive_failures += 1
        if st.consecutive_failures >= settings.llm_circuit_breaker_failures:
            st.tripped_until = time.time() + 60.0
            logger.warning("Circuit breaker tripped for LLM provider '%s' for 60s", name)

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if time.time() < self._all_down_until:
            return self._rule_fallback(messages)
        errors: list[str] = []
        for name in settings.llm_providers:
            if self._is_tripped(name):
                continue
            try:
                return self._call(name, messages, tools, max_tokens)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")
                self._record_failure(name)
        logger.warning("All LLM providers failed (%s); using local rule-based fallback", "; ".join(errors))
        self._all_down_until = time.time() + settings.llm_down_cooldown_seconds
        return self._rule_fallback(messages)

    def _call(
        self,
        name: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None,
        max_tokens: int | None,
    ) -> LLMResponse:
        started = time.perf_counter()
        if name == "groq":
            return self._groq(messages, started, max_tokens)
        if name == "gemini":
            return self._gemini(messages, started, max_tokens)
        if name == "ollama":
            return self._ollama(messages, started, max_tokens)
        raise ValueError(f"Unknown provider: {name}")

    def _groq(self, messages: list[dict[str, str]], started: float, max_tokens: int | None = None) -> LLMResponse:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not configured")
        body: dict[str, Any] = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": 0.3,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json=body,
            timeout=_httpx_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider="groq",
            model=settings.groq_model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            tokens_in=data.get("usage", {}).get("prompt_tokens", 0),
            tokens_out=data.get("usage", {}).get("completion_tokens", 0),
        )

    def _gemini(
        self, messages: list[dict[str, str]], started: float, max_tokens: int | None = None
    ) -> LLMResponse:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        payload: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}]}
        if max_tokens:
            payload["generationConfig"] = {"maxOutputTokens": max_tokens}
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            params={"key": settings.gemini_api_key},
            json=payload,
            timeout=_httpx_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return LLMResponse(
            content=text,
            provider="gemini",
            model=settings.gemini_model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _ollama(
        self, messages: list[dict[str, str]], started: float, max_tokens: int | None = None
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.ollama_keep_alive,
        }
        if max_tokens:
            body["num_predict"] = max_tokens
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=body,
            timeout=_httpx_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["message"]["content"],
            provider="ollama",
            model=data.get("model", settings.ollama_model),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _rule_fallback(self, messages: list[dict[str, str]]) -> LLMResponse:
        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        return LLMResponse(
            content=(
                "[local-fallback] No LLM provider is reachable (Groq/Gemini/Ollama unavailable). "
                f"I received your request: '{last_user[:200]}'. "
                "Start Ollama (or set GROQ_API_KEY / GEMINI_API_KEY) to enable AI reasoning. "
                "Deterministic rule-based responses are still available for registration checks."
            ),
            provider="local-fallback",
            model="rule-based",
            latency_ms=0,
        )


_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
