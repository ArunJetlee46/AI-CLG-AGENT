import logging

from sqlalchemy import func, select

from app.agents.state import AgentState
from app.config import get_settings
from app.core.audit import record_event
from app.db import SessionLocal
from app.models.entities import Course, Enrollment, Student
from app.services.llm import get_llm_gateway
from app.services.prereqs import prereq_status
from app.services.rag import get_rag

logger = logging.getLogger(__name__)
settings = get_settings()


class AcademicOpsAgent:
    """Advising Agent: handles course Q&A (RAG -> College AI fallback), registration
    validation (propose-only), and report generation. Read-only - never writes."""

    name = "advising"

    def run(self, state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        lowered = text.lower()

        if any(k in lowered for k in ("register", "enroll", "add course", "sign up")):
            return self._register(state, text)
        if any(k in lowered for k in ("prerequisite", "prereq", "can i take", "eligible", "require")):
            return self._prereqs(state, text)
        if any(k in lowered for k in ("attendance", "report", "grades", "transcript")):
            return self._report(state, text)
        return self._answer(state, text)

    def _answer(self, state: AgentState, text: str) -> AgentState:
        rag = get_rag()
        answer, citations, llm_resp = rag.answer(text, on_token=state.get("stream_callback"))
        state["answer"] = answer
        state["citations"] = citations
        state["agent"] = self.name
        state["provider"] = llm_resp.provider
        state["model"] = llm_resp.model
        state["audit_events"].append(
            {
                "action": "agent_llm_call",
                "entity_type": "chat",
                "payload": {
                    "provider": llm_resp.provider,
                    "model": llm_resp.model,
                    "latency_ms": llm_resp.latency_ms,
                    "citations": citations,
                },
            }
        )
        return state

    def _prereqs(self, state: AgentState, text: str) -> AgentState:
        codes = _extract_course_codes(text, fallback=False)
        if not codes:
            return self._answer(state, text)
        db = SessionLocal()
        try:
            student = None
            if state.get("actor_id"):
                student = db.execute(select(Student).where(Student.user_id == state["actor_id"])).scalar_one_or_none()
            student_id = student.id if student is not None else None
            statuses = {code: prereq_status(db, code, student_id=student_id) for code in codes}
            lines: list[str] = []
            for code in codes:
                status = statuses[code]
                if not status["exists"]:
                    lines.append(f"{code}: not found in the catalog.")
                    continue
                direct = ", ".join(status["direct"]) if status["direct"] else "none"
                chain = " > ".join(c["code"] for c in status["chain"]) if status["chain"] else "none"
                lines.append(f"{code} directly requires: {direct}. Full prerequisite chain: {chain}.")
                if status["cycle"]:
                    lines.append(f"Warning: prerequisite cycle detected involving {code}.")
                if status["missing"]:
                    lines.append(f"Missing courses in catalog: {', '.join(status['missing'])}.")
                if status["unmet"]:
                    lines.append(f"You have not yet completed: {', '.join(status['unmet'])}.")
            state["answer"] = " ".join(lines)
            state["agent"] = self.name
            state["data"] = {"courses": statuses}
            state["audit_events"].append(
                {"action": "prereq_queried", "entity_type": "course", "payload": {"codes": codes}}
            )
            return state
        finally:
            db.close()

    def _register(self, state: AgentState, text: str) -> AgentState:
        db = SessionLocal()
        try:
            student = None
            if state.get("actor_id"):
                student = db.execute(select(Student).where(Student.user_id == state["actor_id"])).scalar_one_or_none()
            course_codes = _extract_course_codes(text)
            validation = self._validate(db, course_codes, student_id=student.id if student is not None else None)
            if validation["ok"]:
                state["answer"] = (
                    f"Registration validation passed for {validation['course_codes']}. "
                    "This action requires an admin approval before the enrollment is created."
                )
                state["requires_approval"] = True
                state["data"] = {"action": "register", "course_codes": validation["course_codes"], "validations": validation["checks"]}
                state["audit_events"].append(
                    {
                        "action": "registration_validated",
                        "entity_type": "enrollment",
                        "payload": {"course_codes": validation["course_codes"], "checks": validation["checks"]},
                    }
                )
            else:
                state["answer"] = f"Registration blocked: {validation['reasons']}"
                state["audit_events"].append(
                    {
                        "action": "registration_blocked",
                        "entity_type": "enrollment",
                        "payload": {"reasons": validation["reasons"]},
                    }
                )
            return state
        finally:
            db.close()

    def _validate(self, db, course_codes: list[str], student_id: str | None = None) -> dict:
        reasons: list[str] = []
        checks: list[dict] = []
        for code in course_codes:
            course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
            if course is None:
                reasons.append(f"Course {code} does not exist")
                continue
            status = prereq_status(db, code, student_id=student_id)
            if status["cycle"]:
                reasons.append(f"prerequisite cycle detected for {code}")
            for prereq in status["missing"]:
                reasons.append(f"{code} requires missing prerequisite {prereq}")
            if student_id is not None and status["unmet"]:
                reasons.append(f"{code} requires prerequisites you have not completed: {', '.join(status['unmet'])}")
            enrolled = db.execute(
                select(func.count(Enrollment.id)).where(Enrollment.course_id == course.id, Enrollment.status == "approved")
            ).scalar_one()
            checks.append(
                {
                    "course": code,
                    "capacity_left": max(0, course.capacity - enrolled),
                    "prerequisites": status["direct"],
                    "prereq_chain": [c["code"] for c in status["chain"]],
                }
            )
        return {"ok": not reasons, "reasons": reasons, "checks": checks, "course_codes": course_codes}

    def _report(self, state: AgentState, text: str) -> AgentState:
        db = SessionLocal()
        try:
            student_count = db.execute(select(func.count(Student.id))).scalar_one()
            course_count = db.execute(select(func.count(Course.id))).scalar_one()
            approved = db.execute(select(func.count(Enrollment.id)).where(Enrollment.status == "approved")).scalar_one()
            state["answer"] = (
                f"Academic snapshot: {student_count} students, {course_count} courses, "
                f"{approved} approved enrollments. (Rule-based report; LLM reporting lands in Phase 4.)"
            )
            state["data"] = {"students": student_count, "courses": course_count, "approved_enrollments": approved}
            state["audit_events"].append(
                {
                    "action": "report_generated",
                    "entity_type": "academics",
                    "payload": {"students": student_count, "courses": course_count, "approved_enrollments": approved},
                }
            )
            return state
        finally:
            db.close()


def _extract_course_codes(text: str, fallback: bool = True) -> list[str]:
    import re

    codes = re.findall(r"\b[A-Z]{2,4}\s?\d{3}\b", text.upper())
    codes = [c.replace(" ", "") for c in codes]
    return codes or (["CS101"] if fallback else [])
