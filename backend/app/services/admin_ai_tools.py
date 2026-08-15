"""Admin AI tools: AI Admin Copilot, University Digital Twin (with what-if
scenarios), AI Timetable Optimization, and the AI Evaluation Center.

Same contract as the faculty/student tools: LLM-first through the
app.services.llm gateway with a deterministic fallback so the API never depends
on Ollama being up. Tests run with an unreachable Ollama and exercise the
fallbacks; a fake gateway covers the LLM path.
"""
import json
import logging
import re
from datetime import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import safety
from app.core.audit import record_event
from app.models.entities import Course, Enrollment, Lecturer, Room, TimetableEntry
from app.services import admin_copilot as ac, admin_intelligence
from app.services.llm import get_llm_gateway

logger = logging.getLogger(__name__)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

GRADES = [(90, "A+"), (80, "A"), (70, "B"), (60, "C"), (50, "D"), (0, "F")]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _safe_json(text: str) -> dict | list | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, cleaned, re.S)
        if not match:
            continue
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    return None


def _llm_json(system: str, user: str) -> dict | list | None:
    try:
        response = get_llm_gateway().complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Admin AI tool call failed (%s); using deterministic fallback", exc)
        return None
    if response.provider == "local-fallback":
        return None
    return _safe_json(response.content)


def _llm_text(system: str, user: str) -> str | None:
    try:
        response = get_llm_gateway().complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Admin AI text call failed (%s); using deterministic fallback", exc)
        return None
    if response.provider == "local-fallback":
        return None
    content = (response.content or "").strip()
    return content or None


def _grade(marks: float, total: float) -> str:
    ratio = (marks / total * 100) if total else 0.0
    for threshold, grade in GRADES:
        if ratio >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# 1. AI Admin Copilot
# ---------------------------------------------------------------------------

_COPILOT_INTENTS = {
    "placement": (["placement", "recruit", "drive", "company", "offer", "hiring"], "placement"),
    "dropout": (["dropout", "attrition", "risk", "at risk", "intervention", "warn"], "dropout"),
    "departments": (["department", "faculty", "staff", "workload", "program"], "departments"),
    "forecast": (["forecast", "enrollment", "intake", "admission", "trend", "next year"], "forecast"),
    "accreditation": (["accredit", "naac", "grade", "readiness", "criteria"], "accreditation"),
    "resources": (["resource", "room", "infrastructure", "timetable", "capacity", "lab"], "resources"),
    "governance": (["approval", "audit", "governance", "safety", "kill", "models", "backup"], "governance"),
    "health": (["health", "kpi", "score", "overall", "performance", "status", "how", "summary"], "health"),
}


def _detect_intent(question: str) -> str:
    lowered = question.lower()
    for intent, (keywords, _) in _COPILOT_INTENTS.items():
        if any(k in lowered for k in keywords):
            return intent
    return "health"


def _copilot_context(db: Session, intent: str) -> tuple[dict, list[str]]:
    """Return (context_jsonable, citations) for an intent."""
    if intent == "placement":
        return admin_intelligence.placement_overview(db), ["placement_funnel", "salary_analytics", "skill_demand"]
    if intent == "dropout":
        return admin_intelligence.dropout_analytics(db), ["dropout_risk", "attendance", "gpa"]
    if intent == "departments":
        return {
            "departments": admin_intelligence.list_departments(db),
            "faculty": admin_intelligence.faculty_analytics(db),
        }, ["departments", "faculty_workload"]
    if intent == "forecast":
        return admin_intelligence.enrollment_forecast(db), ["enrollment_forecast", "by_department"]
    if intent == "accreditation":
        return admin_intelligence.accreditation(db), ["accreditation_score", "criteria"]
    if intent == "resources":
        return {
            "resources": admin_intelligence.list_resources(db),
            "timetable": timetable_conflicts(db),
        }, ["resources", "timetable_conflicts"]
    if intent == "governance":
        return admin_intelligence.governance_center(db), ["governance", "approvals", "audit", "models"]
    return {
        "command_center": ac.command_center(db),
        "health": ac.health_score(db),
        "warnings": ac.early_warnings(db),
    }, ["health_score", "command_center", "early_warnings"]


def _copilot_key_numbers(context: dict) -> list[dict]:
    numbers: list[dict] = []
    cc = context.get("command_center")
    if cc:
        numbers.append({"label": "Students", "value": cc["counts"]["students"]})
        numbers.append({"label": "Attendance", "value": f"{cc['kpis']['attendance']}%"})
        numbers.append({"label": "Academic success", "value": f"{cc['kpis']['academic_success']}%"})
        numbers.append({"label": "Placement", "value": f"{cc['kpis']['placement']}%"})
        numbers.append({"label": "At-risk", "value": f"{cc['kpis']['at_risk']}%"})
    health = context.get("health") or (context.get("projected") if context.get("baseline") else None)
    if health and isinstance(health, dict) and "university_health_score" in health:
        numbers.append({"label": "Health score", "value": str(health["university_health_score"])})
    if context.get("high_risk") is not None:
        numbers.append({"label": "High-risk students", "value": str(context["high_risk"])})
    dropout = context.get("bands")
    if dropout:
        numbers.append({"label": "High dropout risk", "value": str(dropout.get("high", 0))})
    depts = context.get("departments")
    if depts and isinstance(depts, dict) and depts.get("count") is not None:
        numbers.append({"label": "Departments", "value": str(depts["count"])})
    numbers = numbers[:6]
    return numbers


def _copilot_actions(context: dict, warnings: list[dict]) -> list[str]:
    actions = [w["recommendation"] for w in warnings[:3]]
    if not actions:
        health = context.get("health") if isinstance(context.get("health"), dict) else None
        if health:
            actions.append("Maintain current interventions to keep the institutional health score stable.")
    return actions


def admin_copilot(db: Session, *, question: str, actor: str) -> dict:
    intent = _detect_intent(question)
    context, citations = _copilot_context(db, intent)
    if intent == "health":
        warnings = context["warnings"]
    else:
        warnings = ac.early_warnings(db)

    summary = _llm_text(
        (
            "You are the AI Admin Copilot for a university. Answer the administrator's "
            "question concisely (2-4 sentences) using ONLY the provided institution data. "
            "Lead with the most important number. Do not invent figures."
        ),
        f"Question: {question}\n\nInstitution data (JSON):\n{json.dumps(context, default=str, indent=2)[:4000]}",
    )
    provider = "local-fallback"
    if summary is None:
        summary = (
            f"Based on the current institution data, here is the picture for '{intent}' "
            f"({question[:120]}). "
        )
        if intent == "health":
            summary += (
                f"The university health score is {context['health']['university_health_score']} "
                f"with {len(warnings)} active early-warning signal(s)."
            )
        elif intent == "placement":
            pred = context.get("prediction", {})
            summary += f"Expected placement rate is {pred.get('expected_placement_rate', 'n/a')}."
        elif intent == "dropout":
            bands = context.get("bands", {})
            summary += f"{bands.get('high', 0)} students are at high dropout risk."
        elif intent == "departments":
            depts = context.get("departments", {})
            summary += f"{depts.get('count', 0)} departments are tracked with workload intelligence."
        elif intent == "forecast":
            summary += f"Next-year enrollment forecast is available for {len(context.get('by_department', []))} departments."
        elif intent == "accreditation":
            summary += f"Projected accreditation grade is {context.get('grade', 'n/a')} (score {context.get('overall_score', 'n/a')})."
        elif intent == "resources":
            res = context.get("resources", {})
            summary += f"{res.get('count', 0)} campus resources tracked with {len(context.get('timetable', {}).get('conflicts', []))} timetable conflict(s)."
        elif intent == "governance":
            summary += f"{context.get('approvals', {}).get('pending', 0)} approvals pending and audit chain intact."

    record_event(
        db,
        actor=actor,
        action="copilot_query",
        entity_type="admin_copilot",
        payload={"question": question, "intent": intent},
    )
    return {
        "question": question,
        "intent": intent,
        "summary": summary,
        "key_numbers": _copilot_key_numbers(context),
        "suggested_actions": _copilot_actions(context, warnings),
        "citations": citations,
        "provider": provider,
    }


# ---------------------------------------------------------------------------
# 2. University Digital Twin + what-if scenarios
# ---------------------------------------------------------------------------


def _entity_counts(db: Session) -> dict:
    from app.models.entities import Student

    def count(model):
        return db.execute(select(func.count()).select_from(model)).scalar() or 0

    return {
        "students": count(Student),
        "faculty": count(Lecturer),
        "courses": count(Course),
        "rooms": count(Room),
        "timetable_entries": count(TimetableEntry),
    }


def university_digital_twin(db: Session) -> dict:
    health = ac.health_score(db)
    cc = ac.command_center(db)
    axes = health["axes"]

    subsystems = []
    for name, label in [("academic", "Academic"), ("student_success", "Student Success"),
                        ("placement", "Placement"), ("faculty", "Faculty"),
                        ("ai_operations", "AI Operations")]:
        score = axes[name]
        trajectory = "improving" if score >= 70 else ("declining" if score < 55 else "stable")
        subsystems.append({
            "key": name,
            "label": label,
            "score": score,
            "trajectory": trajectory,
            "weight": round(ac.HEALTH_WEIGHTS[name] * 100),
        })

    return {
        "state": {
            "counts": cc["counts"],
            "kpis": cc["kpis"],
            "pending_approvals": cc["pending_approvals"],
            "execution_enabled": cc["execution_enabled"],
        },
        "health": health,
        "subsystems": subsystems,
        "entities": _entity_counts(db),
        "warnings": ac.early_warnings(db),
        "trajectory": "improving" if health["university_health_score"] >= 70 else (
            "declining" if health["university_health_score"] < 55 else "stable"),
    }


def run_scenario(
    db: Session,
    *,
    attendance_delta: float = 0.0,
    pass_rate_delta: float = 0.0,
    placement_delta: float = 0.0,
    readiness_delta: float = 0.0,
    interventions: int = 0,
) -> dict:
    """What-if simulation: applies deltas to the live profile and recomputes the
    health score with the same weighted formula as ac.health_score."""
    profile = ac._institution_profile(db)
    health = ac.health_score(db)

    def clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    students = profile["students"]
    high_risk = max(0, profile["high_risk"] - max(0, interventions))

    p_attendance = clamp01(profile["attendance"] + attendance_delta / 100.0)
    p_pass = clamp01(profile["pass_rate"] + pass_rate_delta / 100.0)
    p_placement = clamp01(profile["placement"] + placement_delta / 100.0)
    p_readiness = clamp01(profile["avg_readiness"] / 100.0 + readiness_delta / 100.0)

    academic = 100.0 * (0.4 * p_pass + 0.3 * min(1.0, profile["gpa"] / 4.0) + 0.3 * p_attendance)
    high_risk_ratio = high_risk / students if students else 0.0
    student_success = 100.0 * (0.5 * max(0.0, min(1.0, 1 - 2 * high_risk_ratio)) + 0.5 * p_readiness)
    placement_axis = 100.0 * p_placement
    avg_courses = ac._avg_courses_per_lecturer(db)
    faculty_util = min(1.0, avg_courses / 8.0) if avg_courses is not None else 0.5
    faculty_axis = 100.0 * (0.6 * faculty_util + 0.4 * p_pass)
    ai_ops = 100.0 if safety.get_safety()["execution_allowed"] else 60.0

    projected_axes = {
        "academic": round(academic),
        "student_success": round(student_success),
        "placement": round(placement_axis),
        "faculty": round(faculty_axis),
        "ai_operations": round(ai_ops),
    }
    projected_overall = int(round(sum(projected_axes[k] * ac.HEALTH_WEIGHTS[k] for k in ac.HEALTH_WEIGHTS)))
    projected_overall = max(0, min(100, projected_overall))

    baseline = health["university_health_score"]
    return {
        "baseline": {
            "university_health_score": baseline,
            "axes": health["axes"],
            "kpis": ac.command_center(db)["kpis"],
        },
        "projected": {
            "university_health_score": projected_overall,
            "axes": projected_axes,
            "kpis": {
                "attendance": round(p_attendance * 100, 1),
                "academic_success": round(p_pass * 100, 1),
                "placement": round(p_placement * 100, 1),
                "at_risk": round(high_risk_ratio * 100, 1),
            },
        },
        "impact": {
            "score_delta": projected_overall - baseline,
            "per_axis_deltas": {k: projected_axes[k] - health["axes"][k] for k in health["axes"]},
        },
        "assumptions": [
            "Attendance shifts by {} percentage points".format(attendance_delta),
            "Pass rate shifts by {} percentage points".format(pass_rate_delta),
            "Placement rate shifts by {} percentage points".format(placement_delta),
            "Placement readiness shifts by {} percentage points".format(readiness_delta),
            "{} high-risk student(s) rescued by interventions".format(max(0, interventions)),
        ],
    }


# ---------------------------------------------------------------------------
# 3. AI Timetable Optimization
# ---------------------------------------------------------------------------


def _entries_for(db: Session, *, room_id: str | None = None, lecturer_id: str | None = None,
                 day: str | None = None) -> list[TimetableEntry]:
    stmt = select(TimetableEntry)
    if room_id:
        stmt = stmt.where(TimetableEntry.room_id == room_id)
    if lecturer_id:
        stmt = stmt.where(TimetableEntry.lecturer_id == lecturer_id)
    if day:
        stmt = stmt.where(TimetableEntry.day == day)
    return db.execute(stmt).scalars().all()


def _overlaps(a: TimetableEntry, day: str, start: time, end: time) -> bool:
    if a.day != day:
        return False
    return start < a.end_time and a.start_time < end


def timetable_conflicts(db: Session) -> dict:
    entries = db.execute(select(TimetableEntry)).scalars().all()
    conflicts: list[dict] = []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if a.day != b.day:
                continue
            if not (a.start_time < b.end_time and b.start_time < a.end_time):
                continue
            if a.room_id == b.room_id:
                conflicts.append({
                    "type": "room", "day": a.day,
                    "start": a.start_time.strftime("%H:%M"), "end": a.end_time.strftime("%H:%M"),
                    "first": f"{_course_code(db, a.course_id)} in {_room_no(db, a.room_id)}",
                    "second": f"{_course_code(db, b.course_id)} in {_room_no(db, b.room_id)}",
                })
            if a.lecturer_id == b.lecturer_id:
                conflicts.append({
                    "type": "lecturer", "day": a.day,
                    "start": a.start_time.strftime("%H:%M"), "end": a.end_time.strftime("%H:%M"),
                    "first": f"{_course_code(db, a.course_id)} ({_staff(db, a.lecturer_id)})",
                    "second": f"{_course_code(db, b.course_id)} ({_staff(db, b.lecturer_id)})",
                })
    return {"conflicts": conflicts[:50], "count": len(conflicts), "total_entries": len(entries)}


def _course_code(db: Session, course_id: str) -> str:
    row = db.execute(select(Course.code).where(Course.id == course_id)).scalar_one_or_none()
    return row or course_id[:8]


def _room_no(db: Session, room_id: str) -> str:
    row = db.execute(select(Room.room_no).where(Room.id == room_id)).scalar_one_or_none()
    return row or room_id[:8]


def _staff(db: Session, lecturer_id: str) -> str:
    row = db.execute(select(Lecturer.staff_id).where(Lecturer.id == lecturer_id)).scalar_one_or_none()
    return row or lecturer_id[:8]


def optimize_timetable(db: Session, *, commit: bool = False, start_hour: int = 9,
                       end_hour: int = 17, slot_minutes: int = 60) -> dict:
    if commit and not safety.execution_allowed():
        raise ValueError("AI execution is paused by the safety kill switch; cannot commit timetable.")

    courses = db.execute(select(Course)).scalars().all()
    rooms = sorted(db.execute(select(Room)).scalars().all(), key=lambda r: r.capacity, reverse=True)
    lecturers = db.execute(select(Lecturer)).scalars().all()

    enrolled: dict[str, int] = {}
    for course_id, n in db.execute(
        select(Enrollment.course_id, func.count())
        .where(Enrollment.status == "approved")
        .group_by(Enrollment.course_id)
    ).all():
        enrolled[course_id] = n

    order = sorted(courses, key=lambda c: enrolled.get(c.id, 0), reverse=True)
    slots = []
    hour = start_hour
    while hour + slot_minutes // 60 <= end_hour:
        slots.append((hour, hour + slot_minutes // 60))
        hour += slot_minutes // 60

    busy: dict[str, dict[str, list[tuple[time, time]]]] = {"rooms": {}, "lecturers": {}}
    proposed: list[dict] = []
    unassigned: list[dict] = []

    for course in order:
        class_size = enrolled.get(course.id, 0)
        dept_lecturers = [l for l in lecturers if l.department == course.department] or list(lecturers)
        assigned = False
        for day in DAYS:
            for start_h, end_h in slots:
                st = time(hour=start_h)
                et = time(hour=end_h)
                room = next(
                    (r for r in rooms
                     if r.capacity >= max(class_size, 1)
                     and not any(o[0] < et and st < o[1] for o in busy["rooms"].get(r.id, []))),
                    None,
                )
                if room is None:
                    continue
                lecturer = next(
                    (l for l in dept_lecturers
                     if not any(o[0] < et and st < o[1] for o in busy["lecturers"].get(l.id, []))),
                    None,
                )
                if lecturer is None:
                    continue
                busy["rooms"].setdefault(room.id, []).append((st, et))
                busy["lecturers"].setdefault(lecturer.id, []).append((st, et))
                proposed.append({
                    "course_code": course.code,
                    "title": course.title,
                    "course_id": course.id,
                    "room_no": room.room_no,
                    "room_id": room.id,
                    "staff_id": lecturer.staff_id,
                    "lecturer_id": lecturer.id,
                    "department": course.department,
                    "day": day,
                    "start": st.strftime("%H:%M"),
                    "end": et.strftime("%H:%M"),
                    "enrolled": class_size,
                    "capacity": room.capacity,
                })
                assigned = True
                break
            if assigned:
                break
        if not assigned:
            unassigned.append({"course_code": course.code, "title": course.title,
                               "enrolled": class_size, "reason": "no free room+lecturer slot"})

    room_slots = len(DAYS) * len(slots)
    stats = {
        "courses_scheduled": len(proposed),
        "courses_unassigned": len(unassigned),
        "unassigned": unassigned[:20],
        "room_utilization": round(len({p["room_id"] for p in proposed}) / max(1, len(rooms)) * 100),
        "lecturer_utilization": round(len({p["lecturer_id"] for p in proposed}) / max(1, len(lecturers)) * 100),
        "slots_available": len(DAYS) * len(slots),
        "room_slots": room_slots,
    }

    if commit and proposed:
        for p in proposed:
            db.add(TimetableEntry(
                course_id=p["course_id"], room_id=p["room_id"], lecturer_id=p["lecturer_id"],
                day=p["day"], start_time=time.fromisoformat(p["start"]),
                end_time=time.fromisoformat(p["end"]), term="optimized",
            ))
        record_event(
            db, actor="admin-ai", action="timetable_optimized", entity_type="timetable",
            payload={"scheduled": len(proposed), "unassigned": len(unassigned)},
        )

    return {"proposed": proposed[:200], "stats": stats, "commit": commit,
            "conflicts_before": timetable_conflicts(db)["count"]}


# ---------------------------------------------------------------------------
# 4. AI Evaluation Center
# ---------------------------------------------------------------------------


_EVAL_SYSTEM = (
    "You are a strict, fair university examiner. Grade the student answer using "
    "the given rubric. " + "Reply with ONLY a valid JSON payload. No prose, no code fences."
)


def evaluate_answer(db: Session, *, course_code: str, question: str, rubric: str,
                    answer: str, max_marks: int) -> dict:
    user = (
        f"Course: {course_code}\nQuestion: {question}\nMax marks: {max_marks}\n"
        f"Rubric:\n{rubric}\n\nStudent answer:\n{answer}\n\n"
        'Return JSON: {"criteria":[{"name":str,"max":int,"marks":int,"comment":str}],'
        '"feedback":str,"strengths":[str],"improvements":[str]}'
    )
    payload = _llm_json(_EVAL_SYSTEM, user)
    provider = "local-fallback"

    if isinstance(payload, dict) and isinstance(payload.get("criteria"), list) and payload["criteria"]:
        criteria = []
        for c in payload["criteria"]:
            c_max = max(1, int(c.get("max", 1)))
            c_marks = max(0, min(c_max, int(c.get("marks", 0))))
            criteria.append({
                "name": str(c.get("name", "Criteria")).strip(),
                "max": c_max,
                "marks": c_marks,
                "comment": str(c.get("comment", "")).strip(),
            })
        total = sum(c["marks"] for c in criteria)
        if sum(c["max"] for c in criteria) == max_marks:
            total = round(total / sum(c["max"] for c in criteria) * max_marks, 1)
        feedback = str(payload.get("feedback", "")).strip() or "Graded by AI."
        strengths = [str(s).strip() for s in payload.get("strengths", []) if str(s).strip()][:5]
        improvements = [str(s).strip() for s in payload.get("improvements", []) if str(s).strip()][:5]
        return _eval_response(course_code, question, max_marks, criteria, total, feedback,
                              strengths, improvements, provider)

    criteria, total = _fallback_eval(rubric, answer, max_marks)
    return _eval_response(
        course_code, question, max_marks, criteria, total,
        _fallback_feedback(criteria),
        _fallback_strengths(answer),
        _fallback_improvements(answer),
        provider,
    )


def _fallback_eval(rubric: str, answer: str, max_marks: int) -> tuple[list[dict], float]:
    lowered = answer.lower()
    parts = [p.strip() for p in re.split(r"[\n;]", rubric) if p.strip() and ":" in p]
    if not parts:
        parts = [f"Understanding: max {max_marks}"] if rubric else [f"Overall quality: max {max_marks}"]
    per = max_marks / len(parts)
    criteria = []
    for part in parts:
        name, _, desc = part.partition(":")
        desc = desc.strip()
        keywords = [w for w in re.split(r"\W+", desc.lower()) if len(w) > 3][:6]
        hits = sum(1 for w in keywords if w in lowered)
        ratio = (hits / len(keywords)) if keywords else 0.5
        if not desc:
            ratio = 0.5
        marks = round(per * min(1.0, max(0.2, ratio)), 1)
        criteria.append({
            "name": name.strip() or "Criteria",
            "max": round(per, 1),
            "marks": min(round(per, 1), marks),
            "comment": f"covers {hits} of {len(keywords)} rubric keywords" if keywords else "generic rubric",
        })
    total = round(sum(c["marks"] for c in criteria), 1)
    if sum(c["max"] for c in criteria) and abs(sum(c["max"] for c in criteria) - max_marks) > 0.01:
        total = round(total / sum(c["max"] for c in criteria) * max_marks, 1)
    return criteria, min(max_marks, total)


def _fallback_feedback(criteria: list[dict]) -> str:
    total = sum(c["marks"] for c in criteria)
    if not criteria:
        return "No rubric provided."
    ratio = total / sum(c["max"] for c in criteria)
    if ratio >= 0.8:
        return "Strong submission overall; key rubric points are well covered."
    if ratio >= 0.6:
        return "Adequate submission; several rubric points need fuller development."
    return "Submission misses several rubric points and needs significant revision."


def _fallback_strengths(answer: str) -> list[str]:
    length = len(answer.split())
    strengths = []
    if length >= 100:
        strengths.append("Substantial written output.")
    if length >= 50:
        strengths.append("Structured response with multiple ideas.")
    if not strengths:
        strengths.append("Response submitted for evaluation.")
    return strengths


def _fallback_improvements(answer: str) -> list[str]:
    length = len(answer.split())
    if length < 50:
        return ["Expand the answer to cover each rubric point in detail.",
                "Support claims with course-specific concepts."]
    return ["Tighten argumentation around the rubric's core criteria.",
            "Add examples to strengthen the analysis."]


def _eval_response(course_code: str, question: str, max_marks: int, criteria: list[dict],
                   total: float, feedback: str, strengths: list[str], improvements: list[str],
                   provider: str) -> dict:
    return {
        "course_code": course_code,
        "question": question,
        "max_marks": max_marks,
        "total_marks": total,
        "grade": _grade(total, max_marks),
        "criteria": criteria,
        "feedback": feedback,
        "strengths": strengths,
        "improvements": improvements,
        "provider": provider,
    }
