"""Student Copilot LLM tools: exam prep, assignment assistant, mock interview,
resume/ATS, and project mentor.

Every feature is LLM-first (through the app.services.llm gateway) with a
deterministic rule-based fallback so the API never depends on Ollama being up:
tests run with an unreachable Ollama and therefore exercise the fallbacks.

Prompting notes
---------------
- llama3.2:3b is CPU-only in this deployment, so prompts are kept small and ask
  for strict JSON. _safe_json extracts the first JSON object/array regardless of
  prose around it.
- All factual anchors (course titles, prereqs, program) come from the database,
  never from the model.
"""
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Course, Student
from app.services.llm import get_llm_gateway
from app.services.students import get_profile

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
    """Call the gateway and return parsed JSON, or None on any failure
    (including the offline local-fallback provider)."""
    try:
        response = get_llm_gateway().complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM tool call failed (%s); using deterministic fallback", exc)
        return None
    if response.provider == "local-fallback":
        return None
    return _safe_json(response.content)


def _course(db: Session, course_code: str | None) -> Course | None:
    if not course_code:
        return None
    return db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()


def _course_names(db: Session) -> list[str]:
    return [c for (c,) in db.execute(select(Course.title)).all()]


_JSON_ONLY = (
    "Reply with ONLY a valid JSON payload. No prose, no code fences, no markdown."
)

# ---------------------------------------------------------------------------
# 1. exam prep
# ---------------------------------------------------------------------------

_EXAM_SYSTEM = (
    "You are a university exam-prep tutor. You write concise multiple-choice "
    "questions that test understanding, not trivia. " + _JSON_ONLY
)


def get_exam_prep(db: Session, student: Student, course_code: str | None, count: int = 5) -> dict:
    course = _course(db, course_code)
    profile = get_profile(db, student)
    titles = _course_names(db)
    course_line = (
        f"course_code={course.code}, title={course.title!r}, credits={course.credits}, "
        f"prerequisites={course.prerequisites!r}"
        if course
        else "course is unspecified"
    )
    user = (
        f"Generate {count} multiple-choice exam-prep questions for the course: {course_line}. "
        f"The student is in {profile['program']!r} (year {profile['year']}). "
        f"Other course titles at the college: {titles[:12]}. "
        'Return JSON: {"questions":[{"question":str,"options":[4 strings],"answer_index":int(0-3),"explanation":str}]}'
    )

    payload = _llm_json(_EXAM_SYSTEM, user)
    if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
        questions = []
        for i, q in enumerate(payload["questions"][:count]):
            options = q.get("options") or []
            if len(options) < 2:
                continue
            questions.append(
                {
                    "id": f"q{i + 1}",
                    "course_code": course.code if course else (course_code or ""),
                    "question": str(q.get("question", "")).strip(),
                    "options": [str(o) for o in options[:4]],
                    "answer_index": int(q.get("answer_index", 0)) % len(options[:4]),
                    "explanation": str(q.get("explanation", "")).strip(),
                }
            )
        if questions:
            return {"student_id": student.student_id, "provider": "llm", "course_code": course_code or "", "questions": questions}

    return _fallback_exam(db, student, course, count)


def _fallback_exam(db: Session, student: Student, course: Course | None, count: int) -> dict:
    questions = []
    if course:
        prereqs = [p for p in (course.prerequisites or []) if p]
        if prereqs:
            q = prereqs[0]
            options = list(dict.fromkeys([q] + [c for c in (course.prerequisites or []) if c != q]))
            while len(options) < 4:
                options.append(f"Not-a-prerequisite-{len(options)}")
            questions.append(
                {
                    "id": "q1",
                    "course_code": course.code,
                    "question": f"Which course is a direct prerequisite of {course.code} ({course.title})?",
                    "options": options[:4],
                    "answer_index": 0,
                    "explanation": f"Prerequisites for {course.code} are: {', '.join(prereqs)}.",
                }
            )
        questions.append(
            {
                "id": "q2",
                "course_code": course.code,
                "question": f"What is the main focus of {course.title} ({course.code})?",
                "options": [
                    f"Core topics in {course.title}",
                    f"Topics from a different course",
                    "General non-curriculum content",
                    "Practical sessions only",
                ],
                "answer_index": 0,
                "explanation": f"{course.title} ({course.credits} credits) is an approved course in your program.",
            }
        )
    # pad with reflection-style questions so count is always met
    for i in range(len(questions), count):
        code = course.code if course else (course_code_from_profile(db, student))
        questions.append(
            {
                "id": f"q{i + 1}",
                "course_code": code,
                "question": f"Explain one core learning outcome of {code} in your own words.",
                "options": ["Describe the outcome precisely", "Paraphrase the course title", "List unrelated topics", "Skip the question"],
                "answer_index": 0,
                "explanation": "Re-read the syllabus section for that course and state the outcome you must demonstrate in the exam.",
            }
        )
    return {"student_id": student.student_id, "provider": "deterministic", "course_code": course_code_or(course), "questions": questions}


def course_code_from_profile(db: Session, student: Student) -> str:
    profile = get_profile(db, student)
    return profile["courses"][0]["course_code"] if profile["courses"] else ""


def course_code_or(course: Course | None) -> str:
    return course.code if course else ""


# ---------------------------------------------------------------------------
# 2. assignment assistant
# ---------------------------------------------------------------------------

_ASSIGN_SYSTEM = (
    "You are an academic assignment assistant. You never do the work for the "
    "student; you give a plan, hints, and a rubric to self-check. " + _JSON_ONLY
)


def get_assignment_assist(db: Session, student: Student, course_code: str | None, assignment_text: str, ask: str = "plan") -> dict:
    course = _course(db, course_code)
    profile = get_profile(db, student)
    user = (
        f"Assignment brief: {assignment_text[:3000]}\n"
        f"Course: {course.title if course else 'unspecified'} ({course.code if course else '?'})\n"
        f"Student program: {profile['program']!r}.\n"
        f"Kind of help requested: {ask} (plan = step-by-step plan, hints = study hints, rubric = marking rubric).\n"
        'Return JSON: {"kind":"plan|hints|rubric","summary":str,"points":[{"title":str,"detail":str}]}'
    )
    payload = _llm_json(_ASSIGN_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("points"):
        return {
            "student_id": student.student_id,
            "course_code": course_code or "",
            "provider": "llm",
            "kind": str(payload.get("kind", ask)),
            "summary": str(payload.get("summary", "")),
            "points": [{"title": str(p.get("title", "")), "detail": str(p.get("detail", ""))} for p in payload["points"]],
        }
    return _fallback_assign(ask, assignment_text)


def _fallback_assign(ask: str, assignment_text: str) -> dict:
    words = len(re.findall(r"\w+", assignment_text or ""))
    if ask == "hints":
        points = [
            {"title": "Read the brief twice", "detail": "Underline the verbs (analyse, compare, design) to see what is asked."},
            {"title": "Connect to lecture topics", "detail": "Map each requirement to a concept covered in class and cite it."},
            {"title": "Draft before polishing", "detail": "Write a rough structure first; refine wording afterwards."},
        ]
    elif ask == "rubric":
        points = [
            {"title": "Understanding (30%)", "detail": "Did you address every part of the brief with accurate concepts?"},
            {"title": "Structure (25%)", "detail": "Clear introduction, body, conclusion with logical flow."},
            {"title": "Evidence (25%)", "detail": "Examples, data, and references support each claim."},
            {"title": "Presentation (20%)", "detail": "Grammar, formatting, and citation style are correct."},
        ]
    else:
        points = [
            {"title": "Understand", "detail": "Break the brief into the requirements and mark what you already know."},
            {"title": "Outline", "detail": "Sketch sections and the evidence each one needs (about 3-5 sections)."},
            {"title": "Draft", "detail": "Write each section, then improve weak parts with course material."},
            {"title": "Review", "detail": "Self-check against a rubric and fix gaps before submission."},
        ]
    return {
        "student_id": "",
        "course_code": "",
        "provider": "deterministic",
        "kind": ask,
        "summary": f"Assignment of ~{words} words: work through these steps to deliver a complete submission.",
        "points": points,
    }


# ---------------------------------------------------------------------------
# 3. mock interview
# ---------------------------------------------------------------------------

_INTERVIEW_SYSTEM = (
    "You are a campus placement interviewer for the given role. Ask ONE concise "
    "role-specific technical or behavioural question. " + _JSON_ONLY
)


def get_mock_interview_question(db: Session, student: Student, role: str) -> dict:
    profile = get_profile(db, student)
    user = (
        f"Role: {role}. Candidate program: {profile['program']!r}, GPA {profile['gpa']}, "
        f"courses: {[c['course_code'] for c in profile['courses']]}.\n"
        'Return JSON: {"question":str,"focus":"technical|behavioural","tip":str}'
    )
    payload = _llm_json(_INTERVIEW_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("question"):
        return {
            "student_id": student.student_id,
            "provider": "llm",
            "role": role,
            "question": str(payload["question"]),
            "focus": str(payload.get("focus", "behavioural")),
            "tip": str(payload.get("tip", "")),
        }
    return _fallback_interview(role)


def _fallback_interview(role: str) -> dict:
    lowered = role.lower()
    if any(k in lowered for k in ("data sci", "analyst", "ml", "machine learning", "ai")):
        question = "Walk me through a data project from raw data to insight. What were the hardest decisions?"
        focus = "technical"
    elif any(k in lowered for k in ("software", "developer", "engineer", "full stack", "backend", "frontend")):
        question = "Describe how you would design a system to handle a sudden 10x increase in traffic."
        focus = "technical"
    elif any(k in lowered for k in ("intern", "fresher", "graduate", "entry")):
        question = "Tell me about a time you had to learn a new technology quickly. How did you approach it?"
        focus = "behavioural"
    else:
        question = "Why do you want this role, and what makes you a strong fit for it?"
        focus = "behavioural"
    return {"student_id": "", "provider": "deterministic", "role": role, "question": question, "focus": focus, "tip": "Structure your answer as Situation-Task-Action-Result."}


_SCORE_SYSTEM = (
    "You are a strict but fair interviewer who scores a candidate answer 0-100 "
    "with feedback and one improvement tip. " + _JSON_ONLY
)


def score_mock_interview(db: Session, student: Student, role: str, question: str, answer: str) -> dict:
    user = (
        f"Role: {role}\nQuestion: {question}\nCandidate answer: {answer[:2500]}\n"
        'Return JSON: {"score":int(0-100),"strengths":list[str],"weaknesses":list[str],"improvement_tip":str}'
    )
    payload = _llm_json(_SCORE_SYSTEM, user)
    if isinstance(payload, dict) and "score" in payload:
        score = max(0, min(100, int(payload.get("score", 0))))
        return {
            "student_id": student.student_id,
            "provider": "llm",
            "score": score,
            "strengths": [str(s) for s in payload.get("strengths", [])],
            "weaknesses": [str(w) for w in payload.get("weaknesses", [])],
            "improvement_tip": str(payload.get("improvement_tip", "")),
        }
    return _fallback_score(question, answer)


def _fallback_score(question: str, answer: str) -> dict:
    words = len(re.findall(r"\w+", answer or ""))
    qterms = {t for t in re.findall(r"\w+", question.lower()) if len(t) > 3}
    covered = sum(1 for t in qterms if t in answer.lower())
    coverage = covered / len(qterms) if qterms else 0.5
    base = min(1.0, words / 80) * 60 + coverage * 40
    score = max(0, min(100, int(round(base))))
    return {
        "student_id": "",
        "provider": "deterministic",
        "score": score,
        "strengths": [f"You gave a structured {words}-word answer"] if words >= 40 else ["Good attempt; develop your points further"],
        "weaknesses": ["Answer is short; expand with an example."] if words < 40 else ["Quantify results and outcomes where possible."],
        "improvement_tip": "Use the STAR format and include at least one concrete example.",
    }


# ---------------------------------------------------------------------------
# 4. resume / ATS
# ---------------------------------------------------------------------------

_ATS_SYSTEM = (
    "You are an ATS (applicant tracking system) expert. Score a resume 0-100 "
    "and give concrete improvements. " + _JSON_ONLY
)


def get_resume_ats(db: Session, student: Student, resume_text: str) -> dict:
    profile = get_profile(db, student)
    user = (
        f"Candidate: program {profile['program']!r}, GPA {profile['gpa']}, courses {[c['course_code'] for c in profile['courses']]}.\n"
        f"Resume text:\n{resume_text[:3500]}\n"
        'Return JSON: {"score":int(0-100),"section_scores":{"format":int,"content":int,"skills":int},"matched_skills":list[str],"suggestions":list[str]}'
    )
    payload = _llm_json(_ATS_SYSTEM, user)
    if isinstance(payload, dict) and "score" in payload:
        return {
            "student_id": student.student_id,
            "provider": "llm",
            "score": max(0, min(100, int(payload.get("score", 0)))),
            "section_scores": payload.get("section_scores", {}),
            "matched_skills": [str(s) for s in payload.get("matched_skills", [])],
            "suggestions": [str(s) for s in payload.get("suggestions", [])],
        }
    return _fallback_ats(db, student, resume_text)


def _fallback_ats(db: Session, student: Student, resume_text: str) -> dict:
    text = (resume_text or "").lower()
    words = len(re.findall(r"\w+", resume_text or ""))
    sections = {name: name in text for name in ("education", "skills", "project", "experience", "achievement")}
    format_score = 70 if words >= 150 else max(30, 30 + words)
    content_score = 50 + 15 * sum(sections.values())
    course_skills = [c for c in _course_names(db) if any(k in c.lower() for k in ("python", "data", "machine", "ai", "sql", "web", "java", "c"))]
    matched = [c for c in course_skills if any(w in text for w in c.lower().split()[:3])]
    skills_score = 40 + min(40, 10 * len(matched))
    score = max(0, min(100, int(round(0.4 * format_score + 0.35 * content_score + 0.25 * skills_score))))
    suggestions = []
    missing = [name for name, present in sections.items() if not present]
    if missing:
        suggestions.append(f"Add a clear '{', '.join(missing)}' section — ATS parsers look for these labels.")
    if words < 150:
        suggestions.append("Expand the resume to at least 150 words with quantified achievements.")
    suggestions.append("Tailor keywords to the job description to improve ATS keyword matching.")
    return {
        "student_id": student.student_id,
        "provider": "deterministic",
        "score": score,
        "section_scores": {"format": format_score, "content": content_score, "skills": skills_score},
        "matched_skills": matched,
        "suggestions": suggestions or ["Resume looks solid; keep it under two pages."],
    }


# ---------------------------------------------------------------------------
# 5. project mentor
# ---------------------------------------------------------------------------

_MENTOR_SYSTEM = (
    "You are a project mentor for a university student. Give a milestone plan "
    "and directly answer the blocker question. " + _JSON_ONLY
)


def get_project_mentor(db: Session, student: Student, project_title: str, project_description: str, question: str) -> dict:
    profile = get_profile(db, student)
    user = (
        f"Project: {project_title}\nDescription: {project_description[:2000]}\n"
        f"Student program: {profile['program']!r}.\n"
        f"Question/blocker: {question}\n"
        'Return JSON: {"milestones":list[str],"advice":str,"next_action":str}'
    )
    payload = _llm_json(_MENTOR_SYSTEM, user)
    if isinstance(payload, dict) and payload.get("milestones"):
        return {
            "student_id": student.student_id,
            "provider": "llm",
            "project_title": project_title,
            "milestones": [str(m) for m in payload["milestones"]],
            "advice": str(payload.get("advice", "")),
            "next_action": str(payload.get("next_action", "")),
        }
    return _fallback_mentor(project_title, project_description, question)


def _fallback_mentor(project_title: str, project_description: str, question: str) -> dict:
    lowered = question.lower()
    if any(k in lowered for k in ("stuck", "error", "bug", "not working", "issue")):
        next_action = "Isolate the smallest failing input, read the full error trace, and test each component in isolation."
    elif any(k in lowered for k in ("idea", "scope", "what should", "where to start")):
        next_action = "Define a minimal viable version of the project, then list the 3 hardest technical risks to solve first."
    elif any(k in lowered for k in ("deadline", "time", "behind", "schedule")):
        next_action = "Cut scope to the core deliverable, protect daily progress blocks, and flag slips early to your mentor."
    else:
        next_action = "Write the next milestone as a small, testable step and start with the piece you understand best."
    return {
        "student_id": "",
        "provider": "deterministic",
        "project_title": project_title or "Untitled project",
        "milestones": [
            "Scope and requirements",
            "Design / architecture sketch",
            "Core implementation",
            "Testing and edge cases",
            "Documentation and presentation",
        ],
        "advice": (
            f"For '{project_title or 'your project'}', keep each milestone to 3-7 days so progress stays visible. "
            f"Your question: {question or 'how do I proceed'}."
        ),
        "next_action": next_action,
    }
