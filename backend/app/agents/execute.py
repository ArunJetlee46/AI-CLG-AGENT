"""Execute Agent - the only component with write access to domain records.

It is a pure dispatcher: it reads an approved ApprovalRequest and routes it to
the matching gated operation in `app.services.execution`. It has no write
primitives of its own, so nothing can be written outside the approval gate.
"""
import logging

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.core.approvals import require_approved
from app.db import SessionLocal
from app.models.entities import ApprovalRequest
from app.services import execution

logger = logging.getLogger(__name__)

_ACTIONS = {
    "register": execution.apply_registration,
    "apply_timetable": execution.apply_timetable,
    "intervention": execution.apply_intervention,
}


class ExecuteAgent(BaseAgent):
    """Sole writer. Applies an already-approved request via the gated services."""

    name = "execute"

    def apply(self, db: Session, approval: ApprovalRequest, actor: str) -> dict:
        require_approved(db, approval.id)
        action = approval.payload.get("action")
        fn = _ACTIONS.get(action)
        if fn is None:
            raise ValueError(f"unknown approved action '{action}'")
        return fn(db, approval_id=approval.id, actor=actor)

    def run(self, state: AgentState) -> AgentState:
        """Graph node: executes only when an approved approval_id is in state.

        In the interactive flow approvals are created *pending* and decided via
        the HITL endpoint, so this node is a no-op during a normal chat run -
        it exists so the graph topology matches the propose -> execute split.
        """
        approval_id = state.get("approval_id")
        if not approval_id:
            return state
        db = SessionLocal()
        try:
            approval = db.get(ApprovalRequest, approval_id)
            if approval is not None and approval.status == "approved":
                result = self.apply(db, approval, state.get("actor", "system"))
                state["answer"] = f"{state.get('answer', '')}\n{result.get('message', 'Applied.')}"
                state["execution"] = result
        except Exception as exc:  # noqa: BLE001
            logger.warning("execute node skipped for %s: %s", approval_id, exc)
        finally:
            db.close()
        return state


execute = ExecuteAgent()
