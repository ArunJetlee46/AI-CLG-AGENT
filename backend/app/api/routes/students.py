from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import User
from app.schemas.faculty import (
    AssignmentAssistRequest,
    InterviewRequest,
    InterviewScoreRequest,
    ProjectMentorRequest,
    ResumeRequest,
)
from app.schemas.students import AdviseRequest
from app.services import student_growth, student_tools, students
from sqlalchemy.orm import Session

router = APIRouter(prefix="/students", tags=["students"])


def _current_student(db: Session, user: User):
    student = students.resolve_student(db, user)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No student profile is linked to this account.",
        )
    return student


@router.get("/me")
def my_profile(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return students.get_profile(db, _current_student(db, user))


@router.get("/me/success-score")
def my_success_score(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return students.get_success_score(db, _current_student(db, user))


@router.get("/me/alerts")
def my_alerts(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> list[dict]:
    return students.get_alerts(db, _current_student(db, user))


@router.get("/me/predictions")
def my_predictions(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return students.get_predictions(db, _current_student(db, user))


@router.post("/me/advise")
def my_advise(
    body: AdviseRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return students.advise(db, _current_student(db, user), body.course_code)


@router.get("/me/today")
def my_today(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return students.get_today(db, _current_student(db, user))


@router.get("/me/weaknesses")
def my_weaknesses(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_weaknesses(db, _current_student(db, user))


@router.get("/me/recommendations")
def my_recommendations(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_recommendations(db, _current_student(db, user))


@router.get("/me/career-readiness")
def my_career_readiness(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_career_readiness(db, _current_student(db, user))


@router.get("/me/study-groups")
def my_study_groups(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_study_groups(db, _current_student(db, user))


@router.get("/me/notifications")
def my_notifications(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_notifications(db, _current_student(db, user))


@router.get("/me/gamification")
def my_gamification(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_gamification(db, _current_student(db, user))


@router.get("/me/digital-twin")
def my_digital_twin(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_digital_twin(db, _current_student(db, user))


@router.get("/me/progress")
def my_progress(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_progress(db, _current_student(db, user))


@router.get("/me/exam-prep")
def my_exam_prep(
    course_code: str = Query(default="", max_length=16),
    count: int = Query(default=5, ge=1, le=10),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_exam_prep(db, _current_student(db, user), course_code or None, count)


@router.post("/me/assignment-assist")
def my_assignment_assist(
    body: AssignmentAssistRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_assignment_assist(
        db, _current_student(db, user), body.course_code or None, body.assignment_text, body.ask
    )


@router.post("/me/mock-interview")
def my_mock_interview(
    body: InterviewRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_mock_interview_question(db, _current_student(db, user), body.role)


@router.post("/me/mock-interview/score")
def my_mock_interview_score(
    body: InterviewScoreRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.score_mock_interview(db, _current_student(db, user), body.role, body.question, body.answer)


@router.post("/me/resume-ats")
def my_resume_ats(
    body: ResumeRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_resume_ats(db, _current_student(db, user), body.resume_text)


@router.post("/me/project-mentor")
def my_project_mentor(
    body: ProjectMentorRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_project_mentor(
        db, _current_student(db, user), body.project_title, body.project_description, body.question
    )
