import logging

from sqlalchemy import func, select

from app.agents.state import AgentState
from app.db import SessionLocal
from app.models.entities import Enrollment, Student
from app.services.llm import get_llm_gateway

logger = logging.getLogger(__name__)


class StudentSuccessAgent:
    """Success Agent: predicts at-risk students (ML-backed, heuristic fallback) and
    drafts an intervention. Propose-only - the write is gated by an approval."""

    name = "success"

    def run(self, state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        db = SessionLocal()
        try:
            from app.ml.predict import predict_risk

            student_count = db.execute(select(func.count(Student.id))).scalar_one()
            results = predict_risk(db, limit=10)
            if results:
                top = results[0]
                state["answer"] = (
                    f"Success snapshot: {student_count} students scored. "
                    f"Top risk: {top['student_id']} in {top['course_code']} "
                    f"at {top['probability']:.0%} risk ({top['risk_level']}). "
                    f"Drivers: {top['explanation']}."
                )
                state["data"] = {"scored": len(results), "top_risk": results[0]}
                if top["risk_level"] == "high":
                    state["requires_approval"] = True
                    state["data"].update(
                        {
                            "action": "intervention",
                            "student_id": top["student_id"],
                            "course_code": top["course_code"],
                            "probability": top["probability"],
                            "plan_text": (
                                f"targeted tutoring + attendance check for "
                                f"{top['student_id']} in {top['course_code']}"
                            ),
                        }
                    )
                    state["answer"] += (
                        "\nRecommended intervention: targeted tutoring + attendance check. "
                        "This requires admin approval before it is applied."
                    )
                state["audit_events"].append(
                    {
                        "action": "risk_prediction",
                        "entity_type": "prediction",
                        "payload": {
                            "scored": len(results),
                            "model_version": results[0].get("model_version", ""),
                            "top_risk": results[0]["student_id"],
                            "requires_approval": bool(state.get("requires_approval")),
                        },
                    }
                )
            else:
                state["answer"] = (
                    "No enrollment data yet. Run the synthetic data generator first "
                    "(python -m synthetic.cli --students 500 --courses 40 --seed 42) and re-try."
                )
            return state
        finally:
            db.close()


class ResourceOptimizerAgent:
    """Resource Agent: timetable optimization via OR-Tools (lazy import); heuristic
    fallback. Propose-only - persisting the solution is gated by an approval."""

    name = "resource"

    def run(self, state: AgentState) -> AgentState:
        db = SessionLocal()
        try:
            from app.ml.optimize import solve_timetable

            report = solve_timetable(db)
            state["answer"] = (
                f"Timetable optimization: {report['courses']} courses over {report['slots']} slots. "
                f"Scheduled: {report.get('scheduled', 0)}. Conflicts: {report['conflicts']}. "
                f"Status: {report['status']} ({report.get('algorithm', 'heuristic')})."
            )
            report["action"] = "apply_timetable"
            report["term"] = "2026-S1"
            state["data"] = report
            state["requires_approval"] = True
            state["answer"] += "\nApplying this timetable requires admin approval."
            state["audit_events"].append(
                {
                    "action": "timetable_proposed",
                    "entity_type": "timetable",
                    "payload": {
                        "courses": report.get("courses"),
                        "scheduled": report.get("scheduled"),
                        "conflicts": report.get("conflicts"),
                        "status": report.get("status"),
                    },
                }
            )
            return state
        finally:
            db.close()


class KnowledgeAgent:
    """NL -> Cypher -> Neo4j cross-domain queries."""

    name = "knowledge"

    def run(self, state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        from app.services.graph_service import get_graph_service

        graph = get_graph_service()
        intent, cypher, rows = graph.answer(text)
        if rows:
            preview = "; ".join(str(r) for r in rows[:5])
            state["answer"] = (
                f"Knowledge graph query resolved ({intent}):\n{preview}\n"
                f"Cypher used: {cypher}"
            )
        else:
            state["answer"] = f"Knowledge query {intent}: Neo4j is not reachable right now. {cypher}"
        state["data"] = {"intent": intent, "cypher": cypher, "rows": len(rows)}
        state["audit_events"].append(
            {
                "action": "knowledge_query",
                "entity_type": "neo4j",
                "payload": {"intent": intent, "cypher": cypher, "rows": len(rows)},
            }
        )
        return state
