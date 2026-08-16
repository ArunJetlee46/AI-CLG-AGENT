import logging
from collections import defaultdict

from sqlalchemy import func, select

from app.agents.state import AgentState
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Student
from app.services.llm import get_llm_gateway

logger = logging.getLogger(__name__)


def _student_by_code(db, student_id: str) -> Student | None:
    if not student_id:
        return None
    return db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()


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


class PlacementAgent:
    """Placement Agent: placement readiness overview, or a personalized
    readiness/placement snapshot for the calling student. Read-only."""

    name = "placement"

    def run(self, state: AgentState) -> AgentState:
        db = SessionLocal()
        try:
            from app.services.placement.core import get_overview, get_readiness

            student = _student_by_code(db, state.get("student_id", ""))
            if student is not None:
                rows = get_readiness(db, student_id=student.student_id)
                if rows:
                    row = rows[0]
                    state["answer"] = (
                        f"Placement readiness for {row['student_id']}: {row['readiness_score']}/100 "
                        f"({row['band'].replace('_', ' ')}), predicted placement probability "
                        f"{row['placement_probability']:.0%}. Drivers: {'; '.join(row['drivers'])}."
                    )
                    state["data"] = {"student_id": row["student_id"], "readiness": row}
                    state["audit_events"].append(
                        {
                            "action": "placement_readiness",
                            "entity_type": "placement",
                            "payload": {
                                "student_id": row["student_id"],
                                "readiness_score": row["readiness_score"],
                                "placement_probability": row["placement_probability"],
                                "band": row["band"],
                            },
                        }
                    )
                    return state

            overview = get_overview(db)
            rate = overview.get("predicted_placement_rate")
            state["answer"] = (
                f"Placement overview: {overview['total_students']} students scored"
                + (f", predicted placement rate {rate:.0%}" if rate is not None else "")
                + f" (ready {overview['distribution']['ready']}, needs improvement "
                f"{overview['distribution']['needs_improvement']}, not ready "
                f"{overview['distribution']['not_ready']})."
            )
            state["data"] = {"overview": overview}
            state["audit_events"].append(
                {
                    "action": "placement_overview",
                    "entity_type": "placement",
                    "payload": {
                        "total_students": overview["total_students"],
                        "predicted_placement_rate": rate,
                        "distribution": overview["distribution"],
                    },
                }
            )
            return state
        finally:
            db.close()


class AttendanceAgent:
    """Attendance Agent: per-student attendance summary and warnings, or a
    course-level attendance snapshot when no student is linked. Read-only."""

    name = "attendance"
    ATTENDANCE_MIN = 0.75  # KB rule: below 75% -> ineligible to sit the exam

    def run(self, state: AgentState) -> AgentState:
        db = SessionLocal()
        try:
            from app.services.students.core import get_profile

            student = _student_by_code(db, state.get("student_id", ""))
            if student is not None:
                profile = get_profile(db, student)
                courses = profile["courses"]
                low = [c for c in courses if c["attendance_rate"] < self.ATTENDANCE_MIN]
                summary = " ".join(
                    f"{c['course_code']} {c['attendance_rate']:.0%}" for c in courses
                ) or "no enrolled courses"
                state["answer"] = (
                    f"Attendance for {profile['student_id']}: overall "
                    f"{profile['overall_attendance']:.0%} across {len(courses)} courses "
                    f"({summary})."
                )
                if low:
                    state["answer"] += (
                        " Below the 75% exam threshold: "
                        + ", ".join(
                            f"{c['course_code']} ({c['attendance_rate']:.0%})" for c in low
                        )
                        + "."
                    )
                else:
                    state["answer"] += " No course is below the 75% threshold."
                state["data"] = {
                    "student_id": profile["student_id"],
                    "overall_attendance": profile["overall_attendance"],
                    "courses": courses,
                    "below_threshold": [c["course_code"] for c in low],
                }
                state["audit_events"].append(
                    {
                        "action": "attendance_summary",
                        "entity_type": "attendance",
                        "payload": {
                            "student_id": profile["student_id"],
                            "overall_attendance": profile["overall_attendance"],
                            "below_threshold": [c["course_code"] for c in low],
                        },
                    }
                )
                return state

            rows = db.execute(
                select(Enrollment.id, Enrollment.course_id).where(Enrollment.status == "approved")
            ).all()
            rates: dict[str, list[float]] = defaultdict(list)
            for enrollment_id, course_id in rows:
                present = db.execute(
                    select(func.count(AttendanceRecord.id)).where(
                        AttendanceRecord.enrollment_id == enrollment_id,
                        AttendanceRecord.status == "present",
                    )
                ).scalar_one()
                total = db.execute(
                    select(func.count(AttendanceRecord.id)).where(
                        AttendanceRecord.enrollment_id == enrollment_id
                    )
                ).scalar_one()
                if total:
                    rates[course_id].append(present / total)
            if not rates:
                state["answer"] = (
                    "No attendance data yet. Run the synthetic data generator "
                    "(python -m synthetic.cli --students 500 --courses 40 --seed 42) and re-try."
                )
                state["data"] = {"courses": []}
                return state
            courses = {c.id: c.code for c in db.execute(select(Course)).scalars()}
            lines = []
            for course_id, values in sorted(rates.items()):
                avg = sum(values) / len(values)
                flag = " (below 75%)" if avg < self.ATTENDANCE_MIN else ""
                lines.append(f"{courses.get(course_id, course_id)}: {avg:.0%}{flag}")
            state["answer"] = "Course-level attendance snapshot: " + "; ".join(lines) + "."
            state["data"] = {"courses": lines}
            state["audit_events"].append(
                {
                    "action": "attendance_snapshot",
                    "entity_type": "attendance",
                    "payload": {"courses": len(rates)},
                }
            )
            return state
        finally:
            db.close()


class ExamAgent:
    """Exam Agent: generates practice questions (LLM-first with a deterministic
    fallback). Personalized to the calling student's enrolled courses."""

    name = "exam"

    def run(self, state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        db = SessionLocal()
        try:
            from app.agents.academic_ops import _extract_course_codes
            from app.services.students.tools import get_exam_prep

            student = _student_by_code(db, state.get("student_id", ""))
            if student is None:
                state["answer"] = (
                    "Exam prep is personalized per student. Connect a student account "
                    "and ask again, e.g. 'generate practice questions for CS301'."
                )
                state["data"] = {"questions": []}
                return state
            codes = _extract_course_codes(text, fallback=True)
            course_code = codes[0] if codes else None
            prep = get_exam_prep(db, student, course_code, count=3)
            questions = prep.get("questions", [])
            if questions:
                lines = [f"{q['id']}) {q['question']}" for q in questions]
                state["answer"] = (
                    f"Exam prep for {course_code or prep.get('course_code') or 'your course'} "
                    f"({prep.get('provider')}): " + " | ".join(lines)
                )
            else:
                state["answer"] = (
                    "No practice questions could be generated. Check the course code and try again."
                )
            state["data"] = {"course_code": course_code or prep.get("course_code", ""), "questions": questions}
            state["audit_events"].append(
                {
                    "action": "exam_prep",
                    "entity_type": "exam",
                    "payload": {
                        "student_id": student.student_id,
                        "course_code": course_code or "",
                        "questions": len(questions),
                        "provider": prep.get("provider", ""),
                    },
                }
            )
            return state
        finally:
            db.close()


class AdvisingAgent:
    """Advising Agent: course prerequisites via the prerequisite graph, with a
    personalized eligibility verdict when a student is linked. Read-only."""

    name = "advising"

    def run(self, state: AgentState) -> AgentState:
        text = state["messages"][-1]["content"]
        db = SessionLocal()
        try:
            from app.agents.academic_ops import _extract_course_codes
            from app.services.prereqs import prereq_status

            codes = _extract_course_codes(text, fallback=False)
            if not codes:
                state["answer"] = (
                    "Which course would you like to check? Include the course code, e.g. CS302."
                )
                state["data"] = {"courses": {}}
                return state

            student = _student_by_code(db, state.get("student_id", ""))
            student_id = student.id if student is not None else None
            statuses = {code: prereq_status(db, code, student_id=student_id) for code in codes[:3]}
            lines: list[str] = []
            for code in codes[:3]:
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
                if student is not None and status["unmet"]:
                    lines.append(f"You have not yet completed: {', '.join(status['unmet'])}.")
                elif student is not None:
                    lines.append(f"You are eligible to take {code}.")
            state["answer"] = " ".join(lines)
            state["agent"] = self.name
            state["data"] = {"courses": statuses}
            state["audit_events"].append(
                {
                    "action": "course_advising",
                    "entity_type": "advising",
                    "payload": {
                        "student_id": student.student_id if student is not None else "",
                        "courses": [c for c in statuses],
                    },
                }
            )
            return state
        finally:
            db.close()
