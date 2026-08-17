"""Tests for the student curriculum study assistant endpoint."""
from unittest.mock import patch

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import Student, User
from app.services.students import assistant


def _make_student(student_id: str) -> Student:
    db = SessionLocal()
    try:
        user = User(username=student_id, password_hash=hash_password("x"), role="student",
                     email=f"{student_id.lower()}@test.edu")
        db.add(user)
        db.flush()
        stu = Student(user_id=user.id, student_id=student_id, year=2, program="CS", gpa=3.0)
        db.add(stu)
        db.commit()
        db.refresh(stu)
        return stu
    finally:
        db.close()


class FakeCurriculumRAG:
    def __init__(self, answer: dict):
        self._answer = answer

    def answer(self, question: str) -> dict:
        return dict(self._answer)


FAKE_GROUNDED = {
    "answer": "The OS syllabus covers process scheduling, memory management, and file systems.",
    "sources": [{"document": "os.pdf", "page_start": 1, "page_end": 5, "course_code": "CS301",
                  "course_title": "Operating Systems", "regulation": "R2020", "programme": "B.Tech",
                  "score": 0.92}],
    "retrieved": [],
    "grounded": True,
}

FAKE_UNAVAILABLE = {
    "answer": "I am unable to answer this question from the available context.",
    "sources": [],
    "retrieved": [],
    "grounded": False,
}


def test_ask_grounds_answer_with_student_id():
    stu = _make_student("ASK01")
    db = SessionLocal()
    try:
        fake = FakeCurriculumRAG(FAKE_GROUNDED)
        with patch.object(assistant, "get_curriculum_rag", return_value=fake):
            result = assistant.ask(db, db.get(Student, stu.id), "What is in the OS syllabus?")
        assert result["student_id"] == "ASK01"
        assert result["grounded"] is True
        assert "OS syllabus" in result["answer"]
        assert len(result["sources"]) == 1
    finally:
        db.close()


def test_ask_passes_through_unavailable():
    stu = _make_student("ASK02")
    db = SessionLocal()
    try:
        fake = FakeCurriculumRAG(FAKE_UNAVAILABLE)
        with patch.object(assistant, "get_curriculum_rag", return_value=fake):
            result = assistant.ask(db, db.get(Student, stu.id), "What is the secret key?")
        assert result["student_id"] == "ASK02"
        assert result["grounded"] is False
        assert result["sources"] == []
    finally:
        db.close()
