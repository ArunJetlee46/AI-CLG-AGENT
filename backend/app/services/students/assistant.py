"""Student curriculum study assistant.

Grounded Q&A over the university's curriculum knowledge base using the
CurriculumRAG pipeline with an offline-safe deterministic fallback when
no LLM provider is available.
"""
from sqlalchemy.orm import Session

from app.models.entities import Student
from app.services.rag.curriculum import get_curriculum_rag


def ask(db: Session, student: Student, question: str) -> dict:
    result = get_curriculum_rag().answer(question)
    result["student_id"] = student.student_id
    return result
