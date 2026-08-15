"""Structural approval enforcement (architecture brief, section 4 + 5).

Proves: mutators reject unapproved calls inside the method; every successful
write records the approval_id in the audit chain; the approval endpoint routes
the approved write through the Execute Agent; production default credentials
refuse to boot.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.approvals import ApprovalRequiredError
from app.db import SessionLocal
from app.main import app, assert_secure_boot
from app.models.entities import ApprovalRequest, AuditLog, InterventionPlan
from app.services import execution

client = TestClient(app)


def _login() -> str:
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _make_approval(db, *, action: str, status: str = "pending", payload: dict | None = None) -> ApprovalRequest:
    approval = ApprovalRequest(
        intent=action,
        payload={"action": action, **(payload or {})},
        user_id="",
        status=status,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


# ---------------------------------------------------------------------------
# Structural gate: enforcement lives inside the mutator
# ---------------------------------------------------------------------------


def test_mutator_rejects_missing_approval_id() -> None:
    db = SessionLocal()
    try:
        with pytest.raises(ApprovalRequiredError):
            execution.apply_intervention(db, approval_id=None, actor="tester")
        with pytest.raises(ApprovalRequiredError):
            execution.apply_registration(db, approval_id="does-not-exist", actor="tester")
    finally:
        db.close()


def test_mutator_rejects_pending_approval() -> None:
    db = SessionLocal()
    approval = None
    try:
        approval = _make_approval(db, action="intervention", payload={"plan_text": "tutoring"})
        with pytest.raises(ApprovalRequiredError):
            execution.apply_intervention(db, approval_id=approval.id, actor="tester")
        assert db.query(InterventionPlan).count() == 0
    finally:
        if approval is not None:
            # clean up so the shared test DB stays order-independent
            db.delete(approval)
            db.commit()
        db.close()


def test_apply_intervention_writes_and_audits_approval_id() -> None:
    db = SessionLocal()
    try:
        approval = _make_approval(
            db,
            action="intervention",
            status="approved",
            payload={"student_id": "STU-1", "course_code": "CS101", "plan_text": "tutoring"},
        )
        result = execution.apply_intervention(db, approval_id=approval.id, actor="tester")
        assert result["ok"] is True

        plan = db.query(InterventionPlan).order_by(InterventionPlan.id.desc()).first()
        assert plan is not None and plan.student_id == "STU-1" and plan.status == "active"

        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "intervention_created")
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert audit is not None
        assert audit.approval_id == approval.id  # which approval authorized this row
    finally:
        db.close()


# ---------------------------------------------------------------------------
# End-to-end: approval endpoint -> Execute Agent -> write + audit
# ---------------------------------------------------------------------------


def test_approve_endpoint_runs_execute_agent_and_audits() -> None:
    headers = {"Authorization": f"Bearer {_login()}"}
    db = SessionLocal()
    try:
        approval = _make_approval(
            db,
            action="intervention",
            payload={"student_id": "STU-99", "course_code": "CS202", "plan_text": "attendance check"},
        )
        request_id = approval.id
    finally:
        db.close()

    resp = client.post(f"/api/v1/approvals/{request_id}", json={"decision": "approve"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert "Intervention applied" in resp.json()["message"]

    db = SessionLocal()
    try:
        plan = db.query(InterventionPlan).filter(InterventionPlan.student_id == "STU-99").first()
        assert plan is not None and plan.status == "active"

        approved = db.get(ApprovalRequest, request_id)
        assert approved.status == "approved"

        approving = (
            db.query(AuditLog)
            .filter(AuditLog.action == "approval_approve", AuditLog.entity_id == request_id)
            .first()
        )
        assert approving is not None and approving.approval_id == request_id

        written = (
            db.query(AuditLog)
            .filter(AuditLog.action == "intervention_created", AuditLog.approval_id == request_id)
            .first()
        )
        assert written is not None and written.entity_id == plan.id
    finally:
        db.close()


def test_approve_unknown_action_is_rejected() -> None:
    headers = {"Authorization": f"Bearer {_login()}"}
    db = SessionLocal()
    try:
        approval = _make_approval(db, action="mystery_action", payload={"action": "mystery_action"})
        request_id = approval.id
    finally:
        db.close()

    resp = client.post(f"/api/v1/approvals/{request_id}", json={"decision": "approve"}, headers=headers)
    assert resp.status_code == 409  # approval was decided, but the write could not execute
    assert "execution failed" in resp.json()["detail"]
    assert "unknown approved action" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Production default-credential boot refusal (section 5)
# ---------------------------------------------------------------------------


def test_boot_refused_in_production_with_defaults() -> None:
    bad = SimpleNamespace(
        app_env="production",
        secret_key="dev-secret-change-me",
        default_admin_password="admin123",
    )
    with pytest.raises(RuntimeError):
        assert_secure_boot(bad)


def test_boot_allowed_when_credentials_are_hardened() -> None:
    good = SimpleNamespace(
        app_env="production",
        secret_key="a-real-secret",
        default_admin_password="correct horse battery staple",
    )
    assert_secure_boot(good)


def test_boot_allowed_in_development_with_defaults() -> None:
    dev = SimpleNamespace(
        app_env="development",
        secret_key="dev-secret-change-me",
        default_admin_password="admin123",
    )
    assert_secure_boot(dev)
