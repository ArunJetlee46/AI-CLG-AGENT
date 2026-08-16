"""Faculty Copilot LLM tools: question papers, lesson plans, teaching material,
assignment evaluation, code review, lab assistant, and viva questions.

Same contract as app.services.student_tools: every feature is LLM-first through
the app.services.llm gateway with a deterministic rule-based fallback so the API
never depends on Ollama being up. Tests run with an unreachable Ollama and
exercise the fallbacks; a fake gateway covers the JSON-parsing LLM path.
"""
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Course, Lecturer
from app.services.rag.llm import get_llm_gateway

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _safe_json(text: str) -> dict | list | None:
    """Extract the first JSON object or array from a model response."""
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
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Faculty tool call failed (%s); using deterministic fallback", exc)
        return None
    if response.provider == "local-fallback":
        return None
    return _safe_json(response.content)


def _course(db: Session, course_code: str | None) -> Course | None:
    if not course_code:
        return None
    return db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()


_JSON_ONLY = (
    "Reply with ONLY a valid JSON payload. No prose, no code fences, no markdown."
)

_LEVELS = ("foundational", "intermediate", "advanced")


def _level(difficulty: str) -> str:
    lowered = (difficulty or "").lower()
    return lowered if lowered in _LEVELS else "intermediate"


# ---------------------------------------------------------------------------
# 1. question paper generator
# ---------------------------------------------------------------------------

_QP_SYSTEM = (
    "You are a university examiner writing a balanced question paper. Questions "
    "must test understanding and be answerable from the syllabus. " + _JSON_ONLY
)


def get_question_paper(db: Session, lecturer: Lecturer, course_code: str, topic: str = "", difficulty: str = "medium", count: int = 5) -> dict:
    course = _course(db, course_code)
    level = _level(difficulty)
    course_line = (
        f"course_code={course.code}, title={course.title!r}, credits={course.credits}, "
        f"prerequisites={course.prerequisites!r}"
        if course
        else "course is unspecified"
    )
    user = (
        f"Build a {level} question paper. Course: {course_line}. "
        f"Focus topic: {topic or 'the whole syllabus'}. "
        f"Include {count} questions mixing recall, application and analysis. "
        'Return JSON: {"questions":[{"type":"short|long|mcq","marks":int,"question":str,"rubric":str}]}'
    )
    payload = _llm_json(_QP_SYSTEM, user)
    if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        questions = [
            {
                "qno": i + 1,
                "type": str(q.get("type", "short")),
                "marks": max(1, int(q.get("marks", 5))),
                "question": str(q.get("question", "")).strip(),
                "rubric": str(q.get("rubric", "")).strip(),
            }
            for i, q in enumerate(payload["questions"][:count])
            if str(q.get("question", "")).strip()
        ]
        if questions:
            return _paper(lecturer, "llm", course, topic, level, questions)
    return _fallback_question_paper(db, lecturer, course, topic, level, count)


def _fallback_question_paper(db: Session, lecturer: Lecturer, course: Course | None, topic: str, level: str, count: int) -> dict:
    prereqs = [p for p in (course.prerequisites or []) if p] if course else []
    questions = []
    if course:
        if prereqs:
            questions.append(
                {
                    "qno": len(questions) + 1,
                    "type": "short",
                    "marks": 5,
                    "question": f"Why is {prereqs[0]} listed as a prerequisite of {course.code} ({course.title})?",
                    "rubric": "Award for correctly identifying the foundational concepts needed before this course.",
                }
            )
        questions.append(
            {
                "qno": len(questions) + 1,
                "type": "long",
                "marks": 10,
                "question": f"Describe the core themes of {course.title} ({course.code}) and how they build on each other.",
                "rubric": "Structure, coverage of core themes, and correct use of course terminology.",
            }
        )
        questions.append(
            {
                "qno": len(questions) + 1,
                "type": "application",
                "marks": 10,
                "question": f"Give a real-world scenario where a concept from {course.title} is applied, and justify your choice.",
                "rubric": "Relevant scenario, correct concept mapping, clear justification.",
            }
        )
    for i in range(len(questions), count):
        tag = f" (topic: {topic})" if topic else ""
        questions.append(
            {
                "qno": len(questions) + 1,
                "type": "short",
                "marks": 5,
                "question": f"Explain one key learning outcome of {course.code if course else 'the course'}{tag} in your own words.",
                "rubric": "Accuracy of the outcome and clarity of the explanation.",
            }
        )
    return _paper(lecturer, "deterministic", course, topic, level, questions)


def _paper(lecturer: Lecturer, provider: str, course: Course | None, topic: str, level: str, questions: list) -> dict:
    return {
        "staff_id": lecturer.staff_id,
        "provider": provider,
        "course_code": course.code if course else "",
        "course_title": course.title if course else "",
        "topic": topic or "full syllabus",
        "difficulty": level,
        "total_marks": sum(q["marks"] for q in questions),
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# 2. lesson plan generator
# ---------------------------------------------------------------------------

_LP_SYSTEM = (
    "You are an experienced university lecturer. Produce a timed lesson plan "
    "with clear learning outcomes and an active-learning structure. " + _JSON_ONLY
)


def get_lesson_plan(db: Session, lecturer: Lecturer, course_code: str, topic: str, duration_minutes: int = 50) -> dict:
    course = _course(db, course_code)
    minutes = max(10, min(180, int(duration_minutes or 50)))
    user = (
        f"Course: {course.title if course else 'unspecified'} ({course.code if course else '?'}). "
        f"Topic: {topic}. Class duration: {minutes} minutes. "
        'Return JSON: {"learning_outcomes":list[str],"structure":[{"phase":str,"time_minutes":int,"activity":str}],'
        '"assessment":str,"materials":list[str]}'
    )
    payload = _llm_json(_LP_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("structure"):
        return {
            "staff_id": lecturer.staff_id,
            "provider": "llm",
            "course_code": course_code or "",
            "course_title": course.title if course else "",
            "topic": topic,
            "duration_minutes": minutes,
            "learning_outcomes": [str(o) for o in payload.get("learning_outcomes", [])],
            "structure": [
                {"phase": str(p.get("phase", "")), "time_minutes": max(1, int(p.get("time_minutes", 5))), "activity": str(p.get("activity", ""))}
                for p in payload["structure"]
            ],
            "assessment": str(payload.get("assessment", "")),
            "materials": [str(m) for m in payload.get("materials", [])],
        }
    return _fallback_lesson_plan(lecturer, course_code, course.title if course else "", topic, minutes)


def _fallback_lesson_plan(lecturer: Lecturer, course_code: str, course_title: str, topic: str, minutes: int) -> dict:
    intro = max(5, round(minutes * 0.15))
    core = max(10, round(minutes * 0.5))
    activity = max(10, round(minutes * 0.25))
    wrap = max(5, minutes - intro - core - activity)
    return {
        "staff_id": lecturer.staff_id,
        "provider": "deterministic",
        "course_code": course_code,
        "course_title": course_title,
        "topic": topic,
        "duration_minutes": minutes,
        "learning_outcomes": [
            f"Explain the key concepts of '{topic or 'the topic'}'",
            "Apply the concepts to a worked example",
            "Evaluate strengths and limitations of the approach",
        ],
        "structure": [
            {"phase": "Warm-up and recap", "time_minutes": intro, "activity": f"Recall prior knowledge linked to {course_title or course_code or 'the course'}."},
            {"phase": "Core teaching", "time_minutes": core, "activity": f"Present and discuss the main ideas of {topic or 'the topic'}."},
            {"phase": "Guided activity", "time_minutes": activity, "activity": "Students solve a problem or discuss in small groups with peer feedback."},
            {"phase": "Wrap-up and check", "time_minutes": wrap, "activity": "Quick exit-ticket questions to confirm the learning outcomes."},
        ],
        "assessment": "Exit-ticket questions plus a short homework problem applying the topic.",
        "materials": ["Whiteboard or slides", "Handout with the worked example", "Exit-ticket form"],
    }


# ---------------------------------------------------------------------------
# 3. teaching material generator
# ---------------------------------------------------------------------------

_TM_SYSTEM = (
    "You are a lecturer writing teaching material. Return a structured outline "
    "with concise section points. " + _JSON_ONLY
)


def get_teaching_material(db: Session, lecturer: Lecturer, course_code: str, topic: str, fmt: str = "notes") -> dict:
    course = _course(db, course_code)
    fmt = (fmt or "notes").lower()
    if fmt not in ("notes", "slides", "outline"):
        fmt = "notes"
    user = (
        f"Course: {course.title if course else 'unspecified'} ({course.code if course else '?'}). "
        f"Topic: {topic}. Format: {fmt}. "
        'Return JSON: {"summary":str,"outline":[{"section":str,"points":list[str]}]}'
    )
    payload = _llm_json(_TM_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("outline"):
        return {
            "staff_id": lecturer.staff_id,
            "provider": "llm",
            "course_code": course_code or "",
            "course_title": course.title if course else "",
            "topic": topic,
            "format": fmt,
            "summary": str(payload.get("summary", "")),
            "outline": [
                {"section": str(s.get("section", "")), "points": [str(p) for p in (s.get("points") or [])]}
                for s in payload["outline"]
            ],
        }
    return _fallback_teaching_material(lecturer, course_code, course.title if course else "", topic, fmt)


def _fallback_teaching_material(lecturer: Lecturer, course_code: str, course_title: str, topic: str, fmt: str) -> dict:
    outline = [
        {
            "section": "Introduction",
            "points": [
                f"Why this matters for {course_title or course_code or 'the course'}",
                "Learning objectives for this material",
            ],
        },
        {
            "section": f"Core content: {topic or 'key concepts'}",
            "points": [
                "Define the central terms and ideas",
                "Present 2-3 worked examples",
                "Common misconceptions to address",
            ],
        },
        {
            "section": "Application",
            "points": [
                "A guided exercise with a model answer",
                "Discussion questions for small groups",
            ],
        },
        {
            "section": "Summary and further study",
            "points": [
                "Takeaway checklist",
                "Suggested readings and next topics",
            ],
        },
    ]
    return {
        "staff_id": lecturer.staff_id,
        "provider": "deterministic",
        "course_code": course_code,
        "course_title": course_title,
        "topic": topic,
        "format": fmt,
        "summary": f"Structured {fmt} covering the essentials of '{topic or 'the topic'}' for {course_title or course_code or 'the course'}.",
        "outline": outline,
    }


# ---------------------------------------------------------------------------
# 4. assignment evaluation
# ---------------------------------------------------------------------------

_EVAL_SYSTEM = (
    "You are a rigorous but fair marker. Score each rubric criterion out of its "
    "max marks and give actionable feedback. " + _JSON_ONLY
)


def evaluate_assignment(db: Session, lecturer: Lecturer, course_code: str, assignment_brief: str, rubric: str, submission: str) -> dict:
    course = _course(db, course_code)
    user = (
        f"Course: {course.title if course else 'unspecified'} ({course.code if course else '?'}).\n"
        f"Assignment brief: {assignment_brief[:1500]}\n"
        f"Rubric: {rubric[:1500] or 'standard rubric (understanding, structure, evidence, presentation)'}\n"
        f"Student submission: {submission[:4000]}\n"
        'Return JSON: {"criterion_scores":[{"criterion":str,"score":int,"max_marks":int,"comment":str}],'
        '"overall":str,"total_score":int,"max_total":int}'
    )
    payload = _llm_json(_EVAL_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("criterion_scores"):
        criteria = [
            {
                "criterion": str(c.get("criterion", "")),
                "score": max(0, int(c.get("score", 0))),
                "max_marks": max(1, int(c.get("max_marks", 10))),
                "comment": str(c.get("comment", "")),
            }
            for c in payload["criterion_scores"]
        ]
        total = sum(c["score"] for c in criteria)
        max_total = sum(c["max_marks"] for c in criteria)
        pct = (total / max_total * 100) if max_total else 0
        return {
            "staff_id": lecturer.staff_id,
            "provider": "llm",
            "course_code": course_code or "",
            "score": total,
            "max_score": max_total,
            "percentage": round(pct, 1),
            "grade": _grade(pct),
            "criteria": criteria,
            "overall": str(payload.get("overall", "")),
        }
    return _fallback_evaluate(lecturer, course_code, rubric, submission)


def _grade(pct: float) -> str:
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B"
    if pct >= 60:
        return "C"
    if pct >= 50:
        return "D"
    return "F"


def _fallback_evaluate(lecturer: Lecturer, course_code: str, rubric: str, submission: str) -> dict:
    text = (submission or "").lower()
    words = len(re.findall(r"\w+", submission or ""))
    criteria = [
        {"criterion": "Understanding", "score": 0, "max_marks": 30, "comment": ""},
        {"criterion": "Structure", "score": 0, "max_marks": 25, "comment": ""},
        {"criterion": "Evidence", "score": 0, "max_marks": 25, "comment": ""},
        {"criterion": "Presentation", "score": 0, "max_marks": 20, "comment": ""},
    ]
    if words >= 200:
        criteria[0]["score"] = 22
        criteria[1]["score"] = 18
    elif words >= 100:
        criteria[0]["score"] = 16
        criteria[1]["score"] = 14
    else:
        criteria[0]["score"] = 10
        criteria[1]["score"] = 10
    covered = sum(1 for t in re.findall(r"\w+", rubric.lower()) if len(t) > 3 and t in text)
    criteria[2]["score"] = min(20, 8 + 2 * covered)
    has_headers = sum(1 for h in ("introduction", "conclusion", "references", "abstract") if h in text)
    criteria[3]["score"] = min(18, 8 + 4 * has_headers)
    for c in criteria:
        if c["score"] >= c["max_marks"] * 0.8:
            c["comment"] = "Strong on this criterion; keep it up."
        elif c["score"] >= c["max_marks"] * 0.5:
            c["comment"] = "Adequate; develop depth and specificity."
        else:
            c["comment"] = "Needs significant improvement; revisit the brief."
    total = sum(c["score"] for c in criteria)
    max_total = sum(c["max_marks"] for c in criteria)
    pct = total / max_total * 100
    return {
        "staff_id": lecturer.staff_id,
        "provider": "deterministic",
        "course_code": course_code,
        "score": total,
        "max_score": max_total,
        "percentage": round(pct, 1),
        "grade": _grade(pct),
        "criteria": criteria,
        "overall": (
            f"A ~{words}-word submission scored {total}/{max_total} ({pct:.0f}%). "
            "Compare against the rubric criterion-by-criterion and expand thin sections with evidence."
        ),
    }


# ---------------------------------------------------------------------------
# 5. code review
# ---------------------------------------------------------------------------

_REVIEW_SYSTEM = (
    "You are a senior code reviewer. Review for correctness, readability, "
    "performance and edge cases. " + _JSON_ONLY
)


def review_code(db: Session, lecturer: Lecturer, code: str, language: str = "") -> dict:
    user = (
        f"Language: {language or 'unspecified'}.\nCode:\n```\n{code[:5000]}\n```\n"
        'Return JSON: {"score":int(0-100),"summary":str,"strengths":list[str],'
        '"issues":[{"severity":"low|medium|high","line":int,"message":str}],"suggestions":list[str]}'
    )
    payload = _llm_json(_REVIEW_SYSTEM, user)
    if isinstance(payload, dict) and "score" in payload:
        issues = [
            {"severity": str(i.get("severity", "medium")), "line": int(i.get("line", 0)), "message": str(i.get("message", ""))}
            for i in payload.get("issues", [])
        ]
        return {
            "staff_id": lecturer.staff_id,
            "provider": "llm",
            "language": language or "unspecified",
            "score": max(0, min(100, int(payload.get("score", 0)))),
            "summary": str(payload.get("summary", "")),
            "strengths": [str(s) for s in payload.get("strengths", [])],
            "issues": issues,
            "suggestions": [str(s) for s in payload.get("suggestions", [])],
        }
    return _fallback_code_review(lecturer, code, language)


def _fallback_code_review(lecturer: Lecturer, code: str, language: str) -> dict:
    lines = (code or "").splitlines()
    issues = []
    strengths = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if len(line) > 100:
            issues.append({"severity": "low", "line": i, "message": "Line exceeds 100 characters; split it for readability."})
        if stripped.startswith("todo") or "TODO" in stripped:
            issues.append({"severity": "medium", "line": i, "message": "Unresolved TODO; complete or document it."})
        if "except:" in stripped or "except :" in stripped:
            issues.append({"severity": "high", "line": i, "message": "Bare except clause hides errors; catch specific exceptions."})
        if stripped.startswith("print(") and len(lines) > 30:
            issues.append({"severity": "low", "line": i, "message": "Debug print left in code; use a logger."})
        if "password" in stripped.lower() and "=" in stripped and "print" not in stripped:
            issues.append({"severity": "high", "line": i, "message": "Potential secret literal; move to environment configuration."})
    if not lines:
        issues.append({"severity": "medium", "line": 1, "message": "Empty submission."})
    elif len(lines) <= 15:
        strengths.append("Small, focused function or snippet — easy to reason about.")
    if not issues:
        strengths.append("No obvious style or correctness red flags detected.")
    high = sum(1 for i in issues if i["severity"] == "high")
    medium = sum(1 for i in issues if i["severity"] == "medium")
    score = max(20, min(98, 85 - high * 15 - medium * 5))
    return {
        "staff_id": lecturer.staff_id,
        "provider": "deterministic",
        "language": language or "unspecified",
        "score": score,
        "summary": f"Reviewed {len(lines)} lines of {language or 'code'}; found {len(issues)} issue(s).",
        "strengths": strengths,
        "issues": issues[:12],
        "suggestions": ["Add unit tests for edge cases.", "Extract repeated logic into small named functions.", "Keep functions under ~25 lines."],
    }


# ---------------------------------------------------------------------------
# 6. lab assistant
# ---------------------------------------------------------------------------

_LAB_SYSTEM = (
    "You are a lab instructor helping a student safely complete a lab exercise. "
    "Give step-by-step guidance, not the full answer sheet. " + _JSON_ONLY
)


def lab_assistant(db: Session, lecturer: Lecturer, question: str) -> dict:
    user = (
        f"Student's lab question: {question[:2000]}\n"
        'Return JSON: {"answer":str,"steps":list[str],"safety_note":str}'
    )
    payload = _llm_json(_LAB_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("steps"):
        return {
            "staff_id": lecturer.staff_id,
            "provider": "llm",
            "question": question,
            "answer": str(payload.get("answer", "")),
            "steps": [str(s) for s in payload["steps"]],
            "safety_note": str(payload.get("safety_note", "")),
        }
    return _fallback_lab(lecturer, question)


def _fallback_lab(lecturer: Lecturer, question: str) -> dict:
    lowered = question.lower()
    safety = "Follow lab induction rules, wear required PPE, and ask your instructor before handling unfamiliar equipment or substances."
    if any(k in lowered for k in ("chemical", "acid", "reagent", "solution", "titration")):
        answer = "This looks like a chemistry procedure. Identify the exact reagent and its hazards before mixing anything."
        steps = [
            "Read the Material Safety Data Sheet (MSDS) for each chemical.",
            "Note quantities and order of addition; never add water to concentrated acid.",
            "Use the smallest practical volumes and label every container.",
            "Record observations, not assumptions.",
        ]
        safety = "Wear gloves and goggles; work in a ventilated area and neutralise spills per the MSDS."
    elif any(k in lowered for k in ("circuit", "voltage", "wiring", "battery", "current")):
        answer = "This is an electrical lab task. Treat every circuit as live until you verify it is not."
        steps = [
            "Sketch the circuit and confirm the component ratings match the supply.",
            "Wire with power off, then check connections before energising.",
            "Measure with the correct multimeter range and probe placement.",
            "Log readings and compare against the expected theoretical values.",
        ]
        safety = "Keep the supply low, one hand away from the circuit when live, and never bypass fuses."
    elif any(k in lowered for k in ("error", "crash", "exception", "python", "java", "debug", "compile")):
        answer = "Start by reproducing the error with the smallest input that triggers it, then read the full traceback."
        steps = [
            "Copy the complete error message, not just the last line.",
            "Isolate the failing line and print intermediate values.",
            "Check assumptions about types and boundaries.",
            "Re-test after each single change.",
        ]
        safety = "Save your work and keep code in version control before experimenting."
    else:
        answer = "Break the lab exercise into observable steps and verify each before moving on."
        steps = [
            "Restate what the lab asks you to demonstrate.",
            "List the equipment, materials, or software you need.",
            "Run each step and record the outcome.",
            "Summarise what the result tells you.",
        ]
    return {
        "staff_id": lecturer.staff_id,
        "provider": "deterministic",
        "question": question,
        "answer": answer,
        "steps": steps,
        "safety_note": safety,
    }


# ---------------------------------------------------------------------------
# 7. viva questions
# ---------------------------------------------------------------------------

_VIVA_SYSTEM = (
    "You are a lecturer preparing viva voce questions. Questions probe "
    "understanding, not memory. " + _JSON_ONLY
)


def get_viva_questions(db: Session, lecturer: Lecturer, course_code: str, topic: str = "", count: int = 5) -> dict:
    course = _course(db, course_code)
    user = (
        f"Course: {course.title if course else 'unspecified'} ({course.code if course else '?'}). "
        f"Topic: {topic or 'the whole syllabus'}. Generate {count} viva questions. "
        'Return JSON: {"questions":[{"question":str,"focus":str,"expected_points":list[str]}]}'
    )
    payload = _llm_json(_VIVA_SYSTEM, user)
    if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        questions = [
            {
                "qno": i + 1,
                "question": str(q.get("question", "")).strip(),
                "focus": str(q.get("focus", "understanding")),
                "expected_points": [str(p) for p in (q.get("expected_points") or [])],
            }
            for i, q in enumerate(payload["questions"][:count])
            if str(q.get("question", "")).strip()
        ]
        if questions:
            return _viva(lecturer, "llm", course, topic, questions)
    return _fallback_viva(lecturer, course, topic, count)


def _fallback_viva(lecturer: Lecturer, course: Course | None, topic: str, count: int) -> dict:
    questions = []
    if course:
        prereqs = [p for p in (course.prerequisites or []) if p]
        questions.append(
            {
                "qno": 1,
                "question": f"Which course must be completed before {course.code}, and what key idea does it contribute?",
                "focus": "foundation",
                "expected_points": [f"Identify {prereqs[0] if prereqs else 'the prerequisite'} and state one concept it establishes."],
            }
        )
        questions.append(
            {
                "qno": 2,
                "question": f"Summarise the main objective of {course.title} in two sentences.",
                "focus": "understanding",
                "expected_points": ["State the course purpose", "Mention one concrete outcome a student achieves."],
            }
        )
    for i in range(len(questions), count):
        tag = f" in '{topic}'" if topic else ""
        questions.append(
            {
                "qno": len(questions) + 1,
                "question": f"Give an example that illustrates a key concept of {course.code if course else 'this course'}{tag}.",
                "focus": "application",
                "expected_points": ["Give a concrete example", "Explain why it illustrates the concept"],
            }
        )
    return _viva(lecturer, "deterministic", course, topic, questions)


def _viva(lecturer: Lecturer, provider: str, course: Course | None, topic: str, questions: list) -> dict:
    return {
        "staff_id": lecturer.staff_id,
        "provider": provider,
        "course_code": course.code if course else "",
        "course_title": course.title if course else "",
        "topic": topic or "full syllabus",
        "questions": questions,
    }
