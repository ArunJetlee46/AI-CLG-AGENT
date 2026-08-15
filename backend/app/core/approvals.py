"""Structural approval enforcement.

The one non-negotiable rule: nothing mutates a record without a checked
approval. Every mutating repository/service method takes an `approval_id` and
calls `require_approved` *inside itself* - enforcement cannot be routed around
by a forgetful caller.
"""
from sqlalchemy.orm import Session

from app.models.entities import ApprovalRequest


class ApprovalRequiredError(RuntimeError):
    """Raised when a mutating operation is attempted without a valid approved approval."""


def require_approved(db: Session, approval_id: str | None) -> ApprovalRequest:
    """Return the approval row only when it exists and is status=approved.

    Raises ApprovalRequiredError otherwise - callers may never fall through to
    a write path after this fails.
    """
    if not approval_id:
        raise ApprovalRequiredError("approval_id is required for mutating operations")
    approval = db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise ApprovalRequiredError(f"approval '{approval_id}' not found")
    if approval.status != "approved":
        raise ApprovalRequiredError(
            f"approval '{approval_id}' is '{approval.status}', not 'approved'"
        )
    return approval
