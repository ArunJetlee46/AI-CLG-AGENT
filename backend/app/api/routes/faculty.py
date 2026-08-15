from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_role
from app.db import get_db
from app.models.entities import User
from app.schemas.common import (
    AssignmentEvalRequest,
    CodeReviewRequest,
    InterventionRequest,
    LabAssistantRequest,
    LessonPlanRequest,
    SimilarityRequest,
    TeachingMaterialRequest,
)
from app.services import faculty, faculty_intelligence, faculty_tools
from sqlalchemy.orm import Session

router = APIRouter(prefix="/faculty", tags=["faculty"])


def _current_lecturer(db: Session, user: User):
    lecturer = faculty.resolve_lecturer(db, user)
    if lecturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No faculty profile is linked to this account.",
        )
    return lecturer


@router.get("/me")
def me(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty.get_profile(db, _current_lecturer(db, user))


@router.get("/copilot-status")
def copilot_status(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty.get_copilot_status(db, _current_lecturer(db, user), user)


@router.get("/me/audit")
def my_audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty.get_my_audit_log(db, _current_lecturer(db, user), user, limit=limit, offset=offset)


@router.get("/overview")
def my_overview(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty.get_overview(db, _current_lecturer(db, user))


@router.get("/at-risk")
def my_at_risk(
    limit: int = 50,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return faculty.get_at_risk(db, _current_lecturer(db, user), limit=limit)


@router.get("/courses/{course_code}/health")
def course_health(
    course_code: str,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty.get_course_health(db, _current_lecturer(db, user), course_code)


@router.get("/courses/{course_code}/attendance")
def course_attendance(
    course_code: str,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty.get_course_attendance(db, _current_lecturer(db, user), course_code)


@router.post("/interventions")
def propose_intervention(
    body: InterventionRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return faculty.propose_intervention(
            db,
            _current_lecturer(db, user),
            student_id=body.student_id,
            course_code=body.course_code,
            plan_text=body.plan_text,
            actor_user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/interventions")
def my_interventions(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    return faculty.list_interventions(db, _current_lecturer(db, user), actor_user_id=user.id)


@router.get("/me/learning-outcomes")
def my_learning_outcomes(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty_intelligence.get_learning_outcomes(db, _current_lecturer(db, user))


@router.get("/me/high-performers")
def my_high_performers(
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return faculty_intelligence.get_high_performers(db, _current_lecturer(db, user), limit=limit)


@router.get("/me/research-recommendations")
def my_research_recommendations(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty_intelligence.get_research_recommendations(db, _current_lecturer(db, user))


@router.get("/me/schedule")
def my_schedule(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty_intelligence.get_schedule(db, _current_lecturer(db, user))


@router.get("/me/digital-twin")
def my_faculty_digital_twin(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> dict:
    return faculty_intelligence.get_faculty_digital_twin(db, _current_lecturer(db, user))


@router.get("/me/intervention-recommendations")
def my_intervention_recommendations(user: User = Depends(require_role("lecturer", "admin")), db: Session = Depends(get_db)) -> list[dict]:
    return faculty_intelligence.get_intervention_recommendations(db, _current_lecturer(db, user))


@router.get("/courses/{course_code}/report")
def course_report(
    course_code: str,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_intelligence.get_course_report(db, _current_lecturer(db, user), course_code)


@router.get("/courses/{course_code}/remedial")
def course_remedial(
    course_code: str,
    student_id: str = Query(min_length=1, max_length=16),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_intelligence.get_remedial_plan(db, _current_lecturer(db, user), course_code, student_id)


@router.post("/similarity")
def similarity_check(
    body: SimilarityRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_intelligence.get_similarity(
        db, _current_lecturer(db, user), [s.model_dump() for s in body.submissions], body.threshold
    )


# ---------------------------------------------------------------------------
# Faculty LLM tools (question paper, lesson plan, material, eval, code review,
# lab assistant, viva) — LLM-first with deterministic fallbacks.
# ---------------------------------------------------------------------------


@router.get("/tools/question-paper")
def tool_question_paper(
    course_code: str = Query(default="", max_length=32),
    topic: str = Query(default="", max_length=200),
    difficulty: str = Query(default="medium", max_length=16),
    count: int = Query(default=5, ge=1, le=20),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.get_question_paper(db, _current_lecturer(db, user), course_code, topic, difficulty, count)


@router.post("/tools/lesson-plan")
def tool_lesson_plan(
    body: LessonPlanRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.get_lesson_plan(db, _current_lecturer(db, user), body.course_code, body.topic, body.duration_minutes)


@router.post("/tools/teaching-material")
def tool_teaching_material(
    body: TeachingMaterialRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.get_teaching_material(db, _current_lecturer(db, user), body.course_code, body.topic, body.format)


@router.post("/tools/assignment-eval")
def tool_assignment_eval(
    body: AssignmentEvalRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.evaluate_assignment(
        db, _current_lecturer(db, user), body.course_code, body.assignment_brief, body.rubric, body.submission
    )


@router.post("/tools/code-review")
def tool_code_review(
    body: CodeReviewRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.review_code(db, _current_lecturer(db, user), body.code, body.language)


@router.post("/tools/lab-assistant")
def tool_lab_assistant(
    body: LabAssistantRequest,
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.lab_assistant(db, _current_lecturer(db, user), body.question)


@router.get("/tools/viva-questions")
def tool_viva_questions(
    course_code: str = Query(default="", max_length=32),
    topic: str = Query(default="", max_length=200),
    count: int = Query(default=5, ge=1, le=20),
    user: User = Depends(require_role("lecturer", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    return faculty_tools.get_viva_questions(db, _current_lecturer(db, user), course_code, topic, count)
