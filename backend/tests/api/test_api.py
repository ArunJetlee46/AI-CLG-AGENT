"""API-level and integration tests (Phase 12).

Covers the FastAPI surface: auth flows, RBAC enforcement, error-shape
contracts, audit export, approval lifecycle, synthetic queueing, and the
prediction endpoints.
"""

import csv
import io
import json
import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db import SessionLocal
from app.main import app
from app.models.entities import ApprovalRequest, User

client = TestClient(app)


def _login(username: str = "admin", password: str = "admin123") -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_user(username: str, role: str) -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username=username).first():
            db.add(User(username=username, password_hash=hash_password("pass123"), role=role, email=f"{username}@beru.edu"))
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth flows
# ---------------------------------------------------------------------------


def test_login_invalid_credentials_401() -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["code"] == "http_error"


def test_refresh_token_roundtrip() -> None:
    tokens = _login()
    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    refreshed = refresh.json()
    assert refreshed["access_token"]

    me = client.get("/api/v1/auth/me", headers=_auth(refreshed["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_refresh_token_cannot_be_used_as_access() -> None:
    tokens = _login()
    me = client.get("/api/v1/auth/me", headers=_auth(tokens["refresh_token"]))
    assert me.status_code == 401


def test_roles_endpoint() -> None:
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    assert {"student", "lecturer", "admin"} <= set(response.json()["roles"])


# ---------------------------------------------------------------------------
# RBAC enforcement
# ---------------------------------------------------------------------------


def test_student_is_forbidden_on_admin_endpoints() -> None:
    _make_user("stu_phase12", "student")
    token = _login("stu_phase12", "pass123")["access_token"]
    headers = _auth(token)

    assert client.get("/api/v1/audit", headers=headers).status_code == 403
    assert client.get("/api/v1/approvals", headers=headers).status_code == 403
    assert client.get("/api/v1/predictions/live", headers=headers).status_code == 403
    assert client.get("/api/v1/predictions/all", headers=headers).status_code == 403
    assert client.get("/api/v1/predictions/models", headers=headers).status_code == 403
    assert client.post("/api/v1/synthetic/generate", json={"students": 5, "courses": 3, "seed": 1}, headers=headers).status_code == 403


def test_lecturer_can_read_audit_but_not_export() -> None:
    _make_user("lect_phase12", "lecturer")
    token = _login("lect_phase12", "pass123")["access_token"]
    headers = _auth(token)

    assert client.get("/api/v1/audit", headers=headers).status_code == 200
    assert client.get("/api/v1/audit/export", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Error-shape contracts (Phase 5)
# ---------------------------------------------------------------------------


def test_unknown_route_returns_stable_error_shape() -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "http_error"
    assert "detail" in body


def test_validation_error_shape_has_errors_list() -> None:
    tokens = _login()
    response = client.post(
        "/api/v1/agents/chat", json={}, headers=_auth(tokens["access_token"])
    )  # missing message, authenticated -> validation path
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["errors"], list)
    assert body["errors"][0]["type"]


def test_x_request_id_is_echoed() -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req-abc-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-abc-123"


# ---------------------------------------------------------------------------
# Audit endpoint + CSV export
# ---------------------------------------------------------------------------


def test_audit_export_csv_roundtrip() -> None:
    tokens = _login()
    headers = _auth(tokens["access_token"])
    # guarantee at least one audit row exists for this DB
    client.post("/api/v1/agents/chat", json={"message": "what courses exist"}, headers=headers)

    export = client.get("/api/v1/audit/export", headers=headers)
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")

    rows = list(csv.reader(io.StringIO(export.text)))
    assert rows[0] == ["id", "actor", "action", "entity_type", "entity_id", "approval_id", "payload", "hash", "created_at"]
    assert len(rows) >= 2  # header + at least the login event
    assert all(len(r) == len(rows[0]) for r in rows)


def test_audit_filter_by_action() -> None:
    tokens = _login()
    headers = _auth(tokens["access_token"])
    client.post("/api/v1/agents/chat", json={"message": "what courses exist"}, headers=headers)

    filtered = client.get("/api/v1/audit?action=chat_completed&limit=10", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()
    assert all(row["action"] == "chat_completed" for row in filtered.json())


# ---------------------------------------------------------------------------
# Streaming chat (Tier 1.5)
# ---------------------------------------------------------------------------


def test_chat_stream_emits_intent_chunk_meta_events() -> None:
    tokens = _login()
    headers = _auth(tokens["access_token"])

    with client.stream(
        "POST",
        "/api/v1/agents/chat/stream",
        json={"message": "which students are at risk of dropout?"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = []
        buffer = ""
        for text in response.iter_text():
            buffer += text
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                data = next((line[6:] for line in block.splitlines() if line.startswith("data: ")), None)
                if data:
                    events.append(json.loads(data))

    types = [event["type"] for event in events]
    assert "intent" in types
    assert "chunk" in types
    assert "meta" in types
    assert "error" not in types

    meta = next(event for event in events if event["type"] == "meta")
    assert meta["intent"] == "success"
    assert meta["citations"] == []
    chunks = [event["content"] for event in events if event["type"] == "chunk"]
    assert chunks, "expected at least one answer chunk"

    # success-intent runs can propose interventions -> a pending ApprovalRequest.
    # Clean it up so `test_command_center_counts_and_kpis` (which asserts
    # pending_approvals == 0) stays order-independent, mirroring the suite's
    # existing cleanup convention.
    if meta.get("approval_id"):
        db = SessionLocal()
        try:
            approval = db.get(ApprovalRequest, meta["approval_id"])
            if approval is not None:
                db.delete(approval)
                db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Approval lifecycle (HITL gate)
# ---------------------------------------------------------------------------


def test_approval_reject_lifecycle() -> None:
    tokens = _login()
    headers = _auth(tokens["access_token"])

    db = SessionLocal()
    try:
        approval = ApprovalRequest(intent="register", payload={"action": "register", "course_codes": []}, user_id="")
        db.add(approval)
        db.commit()
        db.refresh(approval)
        request_id = approval.id
    finally:
        db.close()

    pending = client.get("/api/v1/approvals?status=pending", headers=headers)
    assert any(a["id"] == request_id for a in pending.json())

    rejected = client.post(f"/api/v1/approvals/{request_id}", json={"decision": "reject", "comment": "policy"}, headers=headers)
    assert rejected.status_code == 200
    assert rejected.json()["message"] == "Rejected. No changes applied."

    audit = client.get(f"/api/v1/audit?action=approval_reject&limit=5", headers=headers)
    assert audit.json()

    # already-decided requests are rejected with 409
    again = client.post(f"/api/v1/approvals/{request_id}", json={"decision": "approve"}, headers=headers)
    assert again.status_code == 409

    missing = client.post(f"/api/v1/approvals/{uuid.uuid4()}", json={"decision": "reject"}, headers=headers)
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# Synthetic generation + prediction endpoints (integration)
# ---------------------------------------------------------------------------


def test_synthetic_generate_queues_background_task() -> None:
    tokens = _login()
    response = client.post(
        "/api/v1/synthetic/generate",
        json={"students": 5, "courses": 3, "seed": 42},
        headers=_auth(tokens["access_token"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["students"] == 5


def test_prediction_endpoints_return_expected_shapes() -> None:
    tokens = _login()
    headers = _auth(tokens["access_token"])

    live = client.get("/api/v1/predictions/live?limit=5", headers=headers)
    assert live.status_code == 200
    assert all({"student_id", "probability", "risk_level"} <= set(row) for row in live.json())

    all_tasks = client.get("/api/v1/predictions/all?limit=5", headers=headers)
    assert all_tasks.status_code == 200
    assert all(row["task"] in {"performance", "placement", "attendance", "dropout"} for row in all_tasks.json())

    models = client.get("/api/v1/predictions/models", headers=headers)
    assert models.status_code == 200
    assert all({"name", "version"} <= set(row) for row in models.json())

    history = client.get("/api/v1/predictions?limit=5", headers=headers)
    assert history.status_code == 200
