from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    email: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    intent: str
    agent: str
    answer: str
    citations: list[str] = []
    requires_approval: bool = False
    approval_id: str | None = None
    decision_card_id: str | None = None
    provider: str = ""
    model: str = ""


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    comment: str = ""


class AuditRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    approval_id: str | None = None
    payload: dict[str, Any] = {}
    hash: str
    created_at: datetime


class AuditQuery(BaseModel):
    actor: str | None = None
    action: str | None = None
    entity_type: str | None = None
    limit: int = 50
    offset: int = 0


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    course_id: str
    probability: float
    risk_level: str
    shap_values: dict[str, Any] = {}
    model_version: str = ""
    created_at: datetime


class GenerateRequest(BaseModel):
    students: int = 500
    courses: int = 40
    seed: int = 42
    persist: bool = True


class AdviseRequest(BaseModel):
    course_code: str = Field(min_length=1, max_length=16)


class InterventionRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=16)
    course_code: str = Field(min_length=1, max_length=16)
    plan_text: str = Field(min_length=5, max_length=2000)


class ShortlistRequest(BaseModel):
    role: str = Field(min_length=1, max_length=128)
    min_gpa: float = Field(default=0.0, ge=0.0, le=4.0)
    max_backlogs: int = Field(default=0, ge=0)
    required_skills: list[str] = []
    limit: int = Field(default=50, ge=1, le=500)


class AssignmentAssistRequest(BaseModel):
    course_code: str = Field(default="", max_length=16)
    assignment_text: str = Field(min_length=3, max_length=6000)
    ask: str = Field(default="plan", pattern="^(plan|hints|rubric)$")


class InterviewRequest(BaseModel):
    role: str = Field(min_length=1, max_length=128)


class InterviewScoreRequest(BaseModel):
    role: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)


class ResumeRequest(BaseModel):
    resume_text: str = Field(min_length=20, max_length=10000)


class ProjectMentorRequest(BaseModel):
    project_title: str = Field(default="", max_length=128)
    project_description: str = Field(default="", max_length=4000)
    question: str = Field(min_length=1, max_length=1000)


class SimilaritySubmission(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=3, max_length=20000)


class SimilarityRequest(BaseModel):
    submissions: list[SimilaritySubmission] = Field(min_length=2, max_length=200)
    threshold: float = Field(default=0.35, ge=0.0, le=1.0)


class LessonPlanRequest(BaseModel):
    course_code: str = Field(default="", max_length=32)
    topic: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(default=50, ge=10, le=180)


class TeachingMaterialRequest(BaseModel):
    course_code: str = Field(default="", max_length=32)
    topic: str = Field(min_length=1, max_length=200)
    format: str = Field(default="notes", max_length=16)


class AssignmentEvalRequest(BaseModel):
    course_code: str = Field(default="", max_length=32)
    assignment_brief: str = Field(default="", max_length=2000)
    rubric: str = Field(default="", max_length=2000)
    submission: str = Field(min_length=1, max_length=8000)


class CodeReviewRequest(BaseModel):
    language: str = Field(default="", max_length=32)
    code: str = Field(min_length=1, max_length=12000)


class LabAssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    sector: str = Field(default="", max_length=64)
    location: str = Field(default="", max_length=128)
    contact_email: str = Field(default="", max_length=128)
    contact_phone: str = Field(default="", max_length=32)
    notes: str = Field(default="", max_length=2000)


class JDAnalyzeRequest(BaseModel):
    text: str = Field(min_length=20, max_length=20000)


class JobDescriptionCreate(BaseModel):
    company_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=128)
    raw_text: str = Field(min_length=20, max_length=20000)
    min_gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    max_backlogs: int | None = Field(default=None, ge=0, le=20)
    ctc_min: float | None = Field(default=None, ge=0.0)
    ctc_max: float | None = Field(default=None, ge=0.0)
    openings: int | None = Field(default=None, ge=1, le=1000)


class DriveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    company_id: str = Field(min_length=1)
    jd_id: str | None = None
    drive_date: date = Field(...)
    mode: str = Field(default="online", max_length=16)
    location: str = Field(default="", max_length=128)


class RoundCreate(BaseModel):
    drive_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=64)
    round_order: int = Field(default=1, ge=1, le=20)
    round_date: date = Field(...)


class SelectionCreate(BaseModel):
    drive_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    round_reached: str = Field(default="final", max_length=64)
    offered_ctc: float = Field(default=0.0, ge=0.0)
    offer_status: str = Field(default="offered", max_length=16)


class NotifyRequest(BaseModel):
    drive_id: str = Field(min_length=1)
    student_ids: list[str] = Field(default_factory=list, max_length=500)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(student|lecturer|placement|admin)$")
    email: str = Field(default="", max_length=128)


class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(student|lecturer|placement|admin)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    body: str = Field(min_length=1, max_length=4000)
    audience: Literal["all", "student", "lecturer", "placement", "admin"] = "all"
    pinned: bool = False


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    resource_type: str = Field(default="classroom", max_length=32)
    capacity: int = Field(default=0, ge=0)
    location: str = Field(default="", max_length=128)
    status: str = Field(default="active", max_length=24)
    utilization: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = Field(default="", max_length=2000)


class ResourceUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=24)
    utilization: float | None = Field(default=None, ge=0.0, le=100.0)


class ModelRegister(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    path: str = Field(default="", max_length=255)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ResearchProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    lead_name: str = Field(default="", max_length=64)
    department: str = Field(default="", max_length=128)
    status: str = Field(default="active", max_length=16)
    funding_amount: float = Field(default=0.0, ge=0.0)
    publications: int = Field(default=0, ge=0)
    start_year: int = Field(default=2025, ge=2000, le=2100)


class IndustryPartnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    sector: str = Field(default="", max_length=64)
    contact_person: str = Field(default="", max_length=64)
    mous: int = Field(default=0, ge=0)
    active: bool = True
    placement_hires: int = Field(default=0, ge=0)


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class ScenarioRequest(BaseModel):
    attendance_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    pass_rate_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    placement_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    readiness_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    interventions: int = Field(default=0, ge=0, le=100000)


class TimetableOptimizeRequest(BaseModel):
    commit: bool = False
    start_hour: int = Field(default=9, ge=6, le=20)
    end_hour: int = Field(default=17, ge=7, le=23)
    slot_minutes: int = Field(default=60, ge=30, le=120)


class EvaluationRequest(BaseModel):
    course_code: str = Field(default="", max_length=32)
    question: str = Field(min_length=1, max_length=1000)
    rubric: str = Field(default="", max_length=2000)
    answer: str = Field(min_length=1, max_length=12000)
    max_marks: int = Field(default=100, ge=1, le=500)
