"""Student resume upload, parsing, and skill extraction."""
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Student, StudentResume

# Skill taxonomy reused from placement intelligence
_SKILL_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
    "java": ["java", "spring", "hibernate", "j2ee"],
    "javascript": ["javascript", "typescript", "react", "angular", "vue", "node", "express", "nextjs"],
    "sql": ["sql", "mysql", "postgresql", "oracle", "database"],
    "machine_learning": ["machine learning", "ml", "deep learning", "neural network", "tensorflow", "pytorch"],
    "data_science": ["data science", "data analysis", "pandas", "numpy", "scikit", "statistics"],
    "cloud": ["aws", "azure", "gcp", "cloud", "docker", "kubernetes"],
    "web": ["html", "css", "bootstrap", "tailwind", "responsive design"],
    "mobile": ["android", "ios", "flutter", "react native"],
    "devops": ["git", "ci/cd", "jenkins", "linux", "bash", "ansible"],
    "cybersecurity": ["cybersecurity", "network security", "encryption", "firewall"],
    "iot": ["iot", "embedded", "raspberry pi", "arduino"],
    "blockchain": ["blockchain", "ethereum", "solidity"],
    "ai": ["artificial intelligence", "nlp", "natural language processing", "computer vision", "opencv"],
    "cpp": ["c++", "c language", "data structures", "algorithms"],
    "r": ["r programming", "ggplot2", "tidyverse"],
    "excel": ["excel", "spreadsheet", "vba"],
}


def _extract_text(file_path: str, filename: str) -> str:
    """Extract plain text from PDF or DOCX."""
    ext = Path(filename).suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            from pdfminer.high_level import extract_text
            text = extract_text(file_path)
        elif ext in (".docx", ".doc"):
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        elif ext == ".txt":
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception:
        pass
    return text


def _extract_skills(text: str) -> list[str]:
    """Extract skills from resume text using the skill taxonomy."""
    lower = text.lower()
    found = set()
    for category, keywords in _SKILL_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                found.add(category)
                break
    return sorted(found)


def upload_resume(db: Session, student: Student, file_content: bytes, filename: str) -> dict:
    """Upload and parse a student resume."""
    settings = get_settings()
    upload_dir = Path(settings.resume_upload_dir) / student.id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Delete existing resume
    existing = db.execute(
        select(StudentResume).where(StudentResume.student_id == student.id)
    ).scalar_one_or_none()
    if existing:
        old_path = Path(existing.file_path)
        if old_path.exists():
            old_path.unlink()
        db.delete(existing)
        db.flush()

    # Save file
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    file_path = upload_dir / safe_name
    file_path.write_bytes(file_content)

    # Parse
    parsed_text = _extract_text(str(file_path), filename)
    skills = _extract_skills(parsed_text)

    resume = StudentResume(
        student_id=student.id,
        file_path=str(file_path),
        original_filename=filename,
        parsed_text=parsed_text[:10000],  # cap stored text
        skills=skills,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "id": resume.id,
        "filename": resume.original_filename,
        "skills": resume.skills,
        "uploaded_at": resume.uploaded_at.isoformat() if resume.uploaded_at else None,
        "message": "Resume uploaded and parsed successfully",
    }


def get_resume(db: Session, student: Student) -> dict | None:
    """Get the student's current resume info."""
    resume = db.execute(
        select(StudentResume).where(StudentResume.student_id == student.id)
    ).scalar_one_or_none()
    if resume is None:
        return None
    return {
        "id": resume.id,
        "filename": resume.original_filename,
        "skills": resume.skills,
        "uploaded_at": resume.uploaded_at.isoformat() if resume.uploaded_at else None,
    }


def delete_resume(db: Session, student: Student) -> dict:
    """Delete the student's resume."""
    resume = db.execute(
        select(StudentResume).where(StudentResume.student_id == student.id)
    ).scalar_one_or_none()
    if resume is None:
        raise ValueError("No resume found")

    file_path = Path(resume.file_path)
    if file_path.exists():
        file_path.unlink()
    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted"}
