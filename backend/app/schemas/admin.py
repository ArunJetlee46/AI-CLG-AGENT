from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


class ScenarioRequest(BaseModel):
    attendance_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    pass_rate_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    placement_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    readiness_delta: float = Field(default=0.0, ge=-50.0, le=50.0)
    interventions: int = Field(default=0, ge=0, le=100000)


class ModelRegister(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    path: str = Field(default="", max_length=255)
    metrics: dict[str, Any] = Field(default_factory=dict)


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


class TimetableOptimizeRequest(BaseModel):
    commit: bool = False
    start_hour: int = Field(default=9, ge=6, le=20)
    end_hour: int = Field(default=17, ge=7, le=23)
    slot_minutes: int = Field(default=60, ge=30, le=120)


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    body: str = Field(min_length=1, max_length=4000)
    audience: Literal["all", "student", "lecturer", "placement", "admin"] = "all"
    pinned: bool = False


class IndustryPartnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    sector: str = Field(default="", max_length=64)
    contact_person: str = Field(default="", max_length=64)
    mous: int = Field(default=0, ge=0)
    active: bool = True
    placement_hires: int = Field(default=0, ge=0)


class ResearchProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    lead_name: str = Field(default="", max_length=64)
    department: str = Field(default="", max_length=128)
    status: str = Field(default="active", max_length=16)
    funding_amount: float = Field(default=0.0, ge=0.0)
    publications: int = Field(default=0, ge=0)
    start_year: int = Field(default=2025, ge=2000, le=2100)


class EvaluationRequest(BaseModel):
    course_code: str = Field(default="", max_length=32)
    question: str = Field(min_length=1, max_length=1000)
    rubric: str = Field(default="", max_length=2000)
    answer: str = Field(min_length=1, max_length=12000)
    max_marks: int = Field(default=100, ge=1, le=500)
