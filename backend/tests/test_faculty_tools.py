"""Tests for the Faculty Copilot LLM tools (question paper, lesson plan,
teaching material, assignment evaluation, code review, lab assistant, viva).

Ollama is unreachable in CI (conftest points OLLAMA_BASE_URL at a dead port), so
most tests exercise the deterministic fallbacks. A fake gateway covers the
JSON-parsing LLM path.
"""
from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import Course, Lecturer, User
from app.services import faculty_tools
from app.services.llm import LLMResponse


def _make_lecturer(staff_id: str = "LECTTOOL") -> Lecturer:
    db = SessionLocal()
    try:
        user = User(username=staff_id, password_hash=hash_password("lecturer123"), role="lecturer",
                    email=f"{staff_id.lower()}@beru.edu")
        db.add(user)
        db.flush()
        lecturer = Lecturer(user_id=user.id, staff_id=staff_id, department="Computer Science", max_hours=20)
        db.add(lecturer)
        db.commit()
        db.refresh(lecturer)
        return lecturer
    finally:
        db.close()


def _course(db, code: str) -> Course:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=["MATH101"])
        db.add(course)
        db.commit()
        db.refresh(course)
    return course


class FakeGateway:
    def __init__(self, content: str) -> None:
        self.content = content

    def complete(self, messages, tools=None):
        return LLMResponse(content=self.content, provider="ollama", model="llama3.2:3b", latency_ms=1)


def test_safe_json_shared_parser():
    assert faculty_tools._safe_json('```json\n{"x": 1}\n```') == {"x": 1}
    assert faculty_tools._safe_json("plain text") is None


def test_question_paper_fallback_uses_course_facts():
    lecturer = _make_lecturer("LCTOOL1")
    db = SessionLocal()
    try:
        _course(db, "FTL101")
        paper = faculty_tools.get_question_paper(db, lecturer, "FTL101", topic="Databases", difficulty="advanced", count=3)
        assert paper["provider"] == "deterministic"
        assert paper["course_code"] == "FTL101"
        assert len(paper["questions"]) == 3
        assert paper["difficulty"] == "advanced"
        assert paper["total_marks"] == sum(q["marks"] for q in paper["questions"])
        assert all(q["question"] and q["rubric"] for q in paper["questions"])
    finally:
        db.close()


def test_question_paper_llm_path(monkeypatch):
    content = '{"questions":[{"type":"long","marks":10,"question":"Q?","rubric":"R"}]}'
    monkeypatch.setattr(faculty_tools, "get_llm_gateway", lambda: FakeGateway(content))
    lecturer = _make_lecturer("LCTOOL2")
    db = SessionLocal()
    try:
        paper = faculty_tools.get_question_paper(db, lecturer, "", topic="", difficulty="medium", count=2)
        assert paper["provider"] == "llm"
        assert paper["questions"][0]["question"] == "Q?"
        assert paper["questions"][0]["marks"] == 10
    finally:
        db.close()


def test_lesson_plan_structure_is_timed():
    lecturer = _make_lecturer("LCTOOL3")
    db = SessionLocal()
    try:
        plan = faculty_tools.get_lesson_plan(db, lecturer, "", topic="Normalisation", duration_minutes=50)
        assert plan["provider"] == "deterministic"
        assert plan["learning_outcomes"]
        assert sum(s["time_minutes"] for s in plan["structure"]) == 50
        assert plan["assessment"]
        assert plan["materials"]
    finally:
        db.close()


def test_lesson_plan_llm_path(monkeypatch):
    content = '{"structure":[{"phase":"Intro","time_minutes":10,"activity":"Recap"}],"learning_outcomes":["LO"],"assessment":"Quiz","materials":["Board"]}'
    monkeypatch.setattr(faculty_tools, "get_llm_gateway", lambda: FakeGateway(content))
    lecturer = _make_lecturer("LCTOOL4")
    db = SessionLocal()
    try:
        plan = faculty_tools.get_lesson_plan(db, lecturer, "", topic="SQL", duration_minutes=60)
        assert plan["provider"] == "llm"
        assert plan["duration_minutes"] == 60
        assert plan["structure"][0]["phase"] == "Intro"
    finally:
        db.close()


def test_teaching_material_formats():
    lecturer = _make_lecturer("LCTOOL5")
    db = SessionLocal()
    try:
        notes = faculty_tools.get_teaching_material(db, lecturer, "", topic="Machine Learning", fmt="notes")
        slides = faculty_tools.get_teaching_material(db, lecturer, "", topic="Machine Learning", fmt="slides")
        assert notes["provider"] == "deterministic"
        assert notes["format"] == "notes"
        assert slides["format"] == "slides"
        assert notes["summary"]
        assert notes["outline"][0]["points"]
    finally:
        db.close()


def test_assignment_evaluation_scores_and_grades():
    lecturer = _make_lecturer("LCTOOL6")
    db = SessionLocal()
    try:
        result = faculty_tools.evaluate_assignment(
            db, lecturer, "", "Write a report on databases.", "Understanding, Structure, Evidence, Presentation",
            "Introduction: databases store data. The relational model uses tables. Conclusion: databases are useful. References: textbooks.",
        )
        assert result["provider"] == "deterministic"
        assert result["score"] <= result["max_score"]
        assert result["percentage"] == round(result["score"] / result["max_score"] * 100, 1)
        assert result["grade"] in ("A", "B", "C", "D", "F")
        assert all(c["comment"] for c in result["criteria"])
    finally:
        db.close()


def test_assignment_evaluation_llm_path(monkeypatch):
    content = '{"criterion_scores":[{"criterion":"Understanding","score":25,"max_marks":30,"comment":"Good"}],"overall":"Solid work","total_score":25,"max_total":30}'
    monkeypatch.setattr(faculty_tools, "get_llm_gateway", lambda: FakeGateway(content))
    lecturer = _make_lecturer("LCTOOL7")
    db = SessionLocal()
    try:
        result = faculty_tools.evaluate_assignment(db, lecturer, "", "Brief", "Rubric", "Submission text here.")
        assert result["provider"] == "llm"
        assert result["criteria"][0]["score"] == 25
        assert result["grade"] == "A"
    finally:
        db.close()


def test_code_review_flags_bare_except():
    lecturer = _make_lecturer("LCTOOL8")
    db = SessionLocal()
    try:
        result = faculty_tools.review_code(
            db, lecturer, "try:\n    run()\nexcept:\n    pass\nprint('done')\n", "Python"
        )
        assert result["provider"] == "deterministic"
        assert result["score"] <= 100
        assert any(i["severity"] == "high" for i in result["issues"])
        assert result["summary"]
    finally:
        db.close()


def test_lab_assistant_safety_tailored_to_domain():
    lecturer = _make_lecturer("LCTOOL9")
    db = SessionLocal()
    try:
        chem = faculty_tools.lab_assistant(db, lecturer, "How do I neutralise a spill of dilute acid?")
        prog = faculty_tools.lab_assistant(db, lecturer, "My Python program crashes with an exception.")
        assert chem["provider"] == "deterministic"
        assert chem["steps"]
        assert "goggles" in chem["safety_note"].lower() or "ppp" in chem["safety_note"].lower() or "ppe" in chem["safety_note"].lower()
        assert any(k in prog["answer"].lower() for k in ("error", "traceback", "reproduc"))
        assert prog["steps"]
    finally:
        db.close()


def test_viva_questions_fallback_and_llm():
    lecturer = _make_lecturer("LCTOOLA")
    db = SessionLocal()
    try:
        _course(db, "FTL102")
        viva = faculty_tools.get_viva_questions(db, lecturer, "FTL102", topic="ER Models", count=3)
        assert viva["provider"] == "deterministic"
        assert len(viva["questions"]) == 3
        assert all(q["expected_points"] for q in viva["questions"])
    finally:
        db.close()

    content = '{"questions":[{"question":"Explain ER models?","focus":"understanding","expected_points":["Entities and relationships"]}]}'


def test_viva_questions_llm_path(monkeypatch):
    content = '{"questions":[{"question":"Explain ER models?","focus":"understanding","expected_points":["Entities and relationships"]}]}'
    monkeypatch.setattr(faculty_tools, "get_llm_gateway", lambda: FakeGateway(content))
    lecturer = _make_lecturer("LCTOOLB")
    db = SessionLocal()
    try:
        viva = faculty_tools.get_viva_questions(db, lecturer, "", topic="ER Models", count=1)
        assert viva["provider"] == "llm"
        assert viva["questions"][0]["question"] == "Explain ER models?"
    finally:
        db.close()
