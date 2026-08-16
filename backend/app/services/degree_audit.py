"""Degree Audit Service.

Computes student progress toward graduation requirements including:
- Total credits required vs earned
- Core course completion
- Elective requirements
- Prerequisite chains
- GPA requirements
"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.entities import (
    Student,
    Course,
    Enrollment,
    Result,
    User,
)


CREDITS_REQUIRED = {
    "B.Tech": 160,
    "M.Tech": 80,
    "MBA": 100,
    "MCA": 120,
    "B.Sc": 120,
    "default": 120,
}

CORE_COURSES_BY_PROGRAM = {
    "AI&DS": [
        "AD1001", "AD1002", "AD2001", "AD2002", "AD2003", "AD2004",
        "AD3001", "AD3002", "AD3003", "AD3004", "AD3005", "AD3006",
        "AD4001", "AD4002",
    ],
    "CSE": [
        "CS1001", "CS1002", "CS2001", "CS2002", "CS2003", "CS2004",
        "CS3001", "CS3002", "CS3003", "CS3004", "CS3005", "CS3006",
        "CS4001", "CS4002",
    ],
    "ECE": [
        "EC1001", "EC1002", "EC2001", "EC2002", "EC2003", "EC2004",
        "EC3001", "EC3002", "EC3003", "EC3004", "EC3005",
        "EC4001", "EC4002",
    ],
    "default": [],
}


def get_program_credits_required(program: str) -> int:
    """Get required credits for a program."""
    for key, value in CREDITS_REQUIRED.items():
        if key.lower() in program.lower():
            return value
    return CREDITS_REQUIRED["default"]


def get_core_courses_for_program(program: str) -> list[str]:
    """Get core course codes for a program."""
    for key, value in CORE_COURSES_BY_PROGRAM.items():
        if key.lower() in program.lower():
            return value
    return CORE_COURSES_BY_PROGRAM["default"]


def get_passed_course_codes(db: Session, student_id: str) -> set[str]:
    """Get set of course codes the student has passed (grade not F)."""
    return {
        code
        for (code,) in db.execute(
            select(Course.code)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .join(Result, Result.enrollment_id == Enrollment.id)
            .where(Enrollment.student_id == student_id, Result.grade != "F")
        ).all()
    }


def get_earned_credits(db: Session, student_id: str) -> int:
    """Get total credits earned by student."""
    result = db.execute(
        select(func.sum(Course.credits))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.student_id == student_id, Result.grade != "F")
    ).scalar()
    return int(result or 0)


def get_current_semester_courses(db: Session, student_id: str) -> list[dict]:
    """Get courses currently enrolled (ongoing)."""
    enrollments = db.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student_id, Enrollment.status == "approved")
    ).all()

    courses = []
    for enrollment, course in enrollments:
        result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        if not result or not result.grade:
            courses.append({
                "course_code": course.code,
                "title": course.title,
                "credits": course.credits,
                "status": "ongoing",
            })
    return courses


def get_failed_courses(db: Session, student_id: str) -> list[dict]:
    """Get courses with failing grades."""
    results = db.execute(
        select(Course, Result)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.student_id == student_id, Result.grade == "F")
    ).all()

    return [
        {
            "course_code": course.code,
            "title": course.title,
            "credits": course.credits,
            "marks": result.marks,
            "grade": result.grade,
        }
        for course, result in results
    ]


def compute_degree_audit(db: Session, student: Student) -> dict:
    """Compute complete degree audit for a student."""
    program = student.program or "Unknown"
    credits_required = get_program_credits_required(program)
    credits_earned = get_earned_credits(db, student.id)
    passed_codes = get_passed_course_codes(db, student.id)
    core_courses = get_core_courses_for_program(program)
    current_courses = get_current_semester_courses(db, student.id)
    failed_courses = get_failed_courses(db, student.id)

    # Core course completion
    core_completed = [c for c in core_courses if c in passed_codes]
    core_remaining = [c for c in core_courses if c not in passed_codes]
    core_in_progress = [c["course_code"] for c in current_courses if c["course_code"] in core_courses]
    core_remaining = [c for c in core_remaining if c not in core_in_progress]

    # Elective credits
    all_passed_courses = db.execute(
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .join(Result, Result.enrollment_id == Enrollment.id)
        .where(Enrollment.student_id == student.id, Result.grade != "F")
    ).scalars().all()

    core_credits = sum(c.credits for c in all_passed_courses if c.code in core_courses)
    elective_credits = sum(c.credits for c in all_passed_courses if c.code not in core_courses)

    # GPA check
    min_gpa = 2.0
    gpa_met = (student.gpa or 0.0) >= min_gpa

    # Overall progress
    total_credits_in_progress = sum(c["credits"] for c in current_courses)
    projected_credits = credits_earned + total_credits_in_progress
    progress_pct = min(100, round((credits_earned / credits_required) * 100, 1)) if credits_required > 0 else 0
    projected_pct = min(100, round((projected_credits / credits_required) * 100, 1)) if credits_required > 0 else 0

    # Core completion percentage
    core_completion_pct = round((len(core_completed) / len(core_courses)) * 100, 1) if core_courses else 100

    # Status determination
    if credits_earned >= credits_required and core_completion_pct >= 100 and gpa_met:
        status = "ready_to_graduate"
    elif projected_credits >= credits_required and core_completion_pct >= 100 and gpa_met:
        status = "on_track"
    elif projected_credits >= credits_required * 0.8 and core_completion_pct >= 80:
        status = "progressing"
    else:
        status = "at_risk"

    return {
        "student_id": student.student_id,
        "program": program,
        "credits_required": credits_required,
        "credits_earned": credits_earned,
        "credits_in_progress": total_credits_in_progress,
        "projected_credits": projected_credits,
        "progress_percentage": progress_pct,
        "projected_percentage": projected_pct,
        "gpa": round(student.gpa or 0.0, 2),
        "min_gpa_required": min_gpa,
        "gpa_met": gpa_met,
        "core_courses": {
            "required": core_courses,
            "completed": core_completed,
            "in_progress": core_in_progress,
            "remaining": core_remaining,
            "completion_percentage": core_completion_pct,
            "credits_earned": core_credits,
        },
        "elective_credits": elective_credits,
        "current_courses": current_courses,
        "failed_courses": failed_courses,
        "status": status,
        "can_graduate": status == "ready_to_graduate",
    }


def get_degree_audit(db: Session, student_id: str) -> Optional[dict]:
    """Get degree audit for a student by student_id (User or Student table)."""
    student = db.execute(select(Student).where(Student.id == student_id)).scalar_one_or_none()
    if not student:
        student = db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()
    if not student:
        return None
    return compute_degree_audit(db, student)