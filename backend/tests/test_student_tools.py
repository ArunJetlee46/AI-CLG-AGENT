"""Tests for the Student Copilot LLM tools (exam prep, assignment assistant,
mock interview, resume/ATS, project mentor).

Ollama is unreachable in CI (conftest points OLLAMA_BASE_URL at a dead port), so
most tests exercise the deterministic fallbacks. A fake gateway is used to cover
the JSON-parsing LLM path.
"""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import AttendanceRecord, Course, Enrollment, Result, Student, User
from app.services import student_tools
from app.services.llm import LLMResponse


def _make_student(student_id: str, *, gpa: float = 3.0, program: str = "Computer Science") -> Student:
    db = SessionLocal()
    try:
        user = User(
            username=student_id,
            password_hash=hash_password("student123"),
            role="student",
            email=f"{student_id.lower()}@beru.edu",
        )
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=2, program=program, gpa=gpa)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


def _enroll(db, student: Student, code: str, *, grade: str = "B", marks: float = 70.0, attendance: float = 0.9) -> Enrollment:
    course = db.execute(select(Course).where(Course.code == code)).scalar_one_or_none()
    if course is None:
        course = Course(code=code, title=f"Course {code}", credits=3, department="Computer Science", prerequisites=["MATH101"])
        db.add(course)
        db.flush()
    enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
    db.add(enrollment)
    db.flush()
    if grade:
        db.add(Result(enrollment_id=enrollment.id, marks=marks, grade=grade, semester="2026-S1"))
    for i in range(10):
        db.add(
            AttendanceRecord(
                enrollment_id=enrollment.id,
                day=date(2026, 3, 2 + i),
                status="present" if i < round(10 * attendance) else "absent",
            )
        )
    db.commit()
    return enrollment


class FakeGateway:
    def __init__(self, content: str) -> None:
        self.content = content

    def complete(self, messages, tools=None):
        return LLMResponse(content=self.content, provider="ollama", model="llama3.2:3b", latency_ms=1)


def test_safe_json_handles_fenced_and_prose():
    assert student_tools._safe_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert student_tools._safe_json('The answer is [1, 2, 3]. That is all.') == [1, 2, 3]
    assert student_tools._safe_json("no json here") is None


def test_exam_prep_fallback_returns_questions():
    stu = _make_student("TOOL01")
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS201")
        result = student_tools.get_exam_prep(db, stu, "CS201", count=3)
        assert result["provider"] == "deterministic"
        assert len(result["questions"]) == 3
        assert all(len(q["options"]) >= 2 for q in result["questions"])
        assert all(0 <= q["answer_index"] < len(q["options"]) for q in result["questions"])
    finally:
        db.close()


def test_exam_prep_llm_path_parses_payload(monkeypatch):
    content = '{"questions":[{"question":"Q1?","options":["a","b","c","d"],"answer_index":2,"explanation":"Because."}]}'
    monkeypatch.setattr(student_tools, "get_llm_gateway", lambda: FakeGateway(content))
    stu = _make_student("TOOL02")
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS202")
        result = student_tools.get_exam_prep(db, stu, "CS202", count=2)
        assert result["provider"] == "llm"
        assert result["questions"][0]["question"] == "Q1?"
        assert result["questions"][0]["answer_index"] == 2
    finally:
        db.close()


def test_assignment_assist_kinds():
    stu = _make_student("TOOL03")
    db = SessionLocal()
    try:
        for kind in ("plan", "hints", "rubric"):
            result = student_tools.get_assignment_assist(db, stu, "CS203", "Write a report on databases.", kind)
            assert result["kind"] == kind
            assert result["points"]
            assert all(p["title"] and p["detail"] for p in result["points"])
    finally:
        db.close()


def test_mock_interview_question_fallback():
    stu = _make_student("TOOL04")
    db = SessionLocal()
    try:
        tech = student_tools.get_mock_interview_question(db, stu, "Machine Learning Engineer")
        soft = student_tools.get_mock_interview_question(db, stu, "Software Developer")
        assert tech["focus"] == "technical"
        assert tech["question"]
        assert soft["question"]
    finally:
        db.close()


def test_mock_interview_score_bounds_and_feedback():
    stu = _make_student("TOOL05")
    db = SessionLocal()
    try:
        result = student_tools.score_mock_interview(db, stu, "Data Analyst", "Tell me about yourself.", "I analyze data with Python and SQL.")
        assert 0 <= result["score"] <= 100
        assert result["improvement_tip"]
        assert isinstance(result["strengths"], list)
    finally:
        db.close()


def test_mock_interview_score_llm_path(monkeypatch):
    content = '{"score":82,"strengths":["Clear structure"],"weaknesses":["No example"],"improvement_tip":"Add an example."}'
    monkeypatch.setattr(student_tools, "get_llm_gateway", lambda: FakeGateway(content))
    stu = _make_student("TOOL06")
    db = SessionLocal()
    try:
        result = student_tools.score_mock_interview(db, stu, "Role", "Question?", "Some answer text.")
        assert result["provider"] == "llm"
        assert result["score"] == 82
        assert result["strengths"] == ["Clear structure"]
    finally:
        db.close()


def test_resume_ats_scores_and_suggests():
    stu = _make_student("TOOL07")
    db = SessionLocal()
    try:
        _enroll(db, stu, "CS207")
        result = student_tools.get_resume_ats(db, stu, "Education: B.Tech. Skills: Python, SQL. Projects: Data analysis.")
        assert 0 <= result["score"] <= 100
        assert set(result["section_scores"]) == {"format", "content", "skills"}
        assert isinstance(result["suggestions"], list)
        assert isinstance(result["matched_skills"], list)
    finally:
        db.close()


def test_project_mentor_returns_plan():
    stu = _make_student("TOOL08")
    db = SessionLocal()
    try:
        result = student_tools.get_project_mentor(db, stu, "Fraud Detection", "Detect fraud in transactions.", "Where do I start?")
        assert result["milestones"]
        assert result["next_action"]
        assert result["advice"]
    finally:
        db.close()
