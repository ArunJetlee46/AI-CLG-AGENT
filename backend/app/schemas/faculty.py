from pydantic import BaseModel, Field


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
