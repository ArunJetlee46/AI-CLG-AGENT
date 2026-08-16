"""Theme D: SSE token streaming for /agents/chat."""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.rag.llm import get_llm_gateway

client = TestClient(app)


def _login() -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_streaming_chat_emits_chunks_then_done() -> None:
    token = _login()["access_token"]
    response = client.post(
        "/api/v1/agents/chat",
        json={"message": "what courses exist at the college", "stream": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    lines = response.text.strip().split("\n\n")
    events = [json.loads(line[len("data: "):]) for line in lines if line.startswith("data: ")]
    assert len(events) >= 2
    assert events[-1]["type"] == "done"
    assert events[-1]["answer"]
    assert any(e["type"] == "chunk" for e in events)


def test_gateway_complete_invokes_on_token_on_fallback() -> None:
    # Hermetic: no Groq key, Ollama unreachable -> local-fallback. on_token
    # must still be invoked exactly once with the full fallback text.
    collected: list[str] = []
    response = get_llm_gateway().complete(
        [{"role": "user", "content": "hello"}],
        on_token=collected.append,
    )
    assert response.provider == "local-fallback"
    assert collected == [response.content]
