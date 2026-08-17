from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status

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
from app.schemas.placement import ApplicationRequest, DecideRequest
from app.schemas.students import AdviseRequest, AskRequest
from app.services import student_assistant, student_growth, student_placements, student_tools, students
from app.services.students import applications as app_service
from app.services.students import resume as resume_service
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


@router.get("/me/timetable")
def my_timetable(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return student_growth.get_timetable(db, _current_student(db, user))


@router.get("/me/placements")
def my_placements(user: User = Depends(require_role("student")), db: Session = Depends(get_db)) -> dict:
    return app_service.get_placements(db, _current_student(db, user))


@router.post("/me/applications")
def my_apply(
    body: ApplicationRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return app_service.apply_to_drive(db, _current_student(db, user), body.drive_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/me/applications/{drive_id}")
def my_withdraw(
    drive_id: str,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return app_service.withdraw_application(db, _current_student(db, user), drive_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/me/selections/{selection_id}/decide")
def my_decide_offer(
    selection_id: str,
    body: DecideRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return app_service.decide_offer(db, _current_student(db, user), selection_id, body.decision)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/me/resume")
async def my_upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {ext} not supported. Upload PDF, DOCX, or TXT.")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")
    try:
        return resume_service.upload_resume(db, _current_student(db, user), content, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/me/resume")
def my_get_resume(
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    result = resume_service.get_resume(db, _current_student(db, user))
    return result or {"message": "No resume uploaded"}


@router.delete("/me/resume")
def my_delete_resume(
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return resume_service.delete_resume(db, _current_student(db, user))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/me/ask")
def my_ask(
    body: AskRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_assistant.ask(db, _current_student(db, user), body.question)


@router.post("/me/project-mentor")
def my_project_mentor(
    body: ProjectMentorRequest,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    return student_tools.get_project_mentor(
        db, _current_student(db, user), body.project_title, body.project_description, body.question
    )
