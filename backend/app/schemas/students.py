from pydantic import BaseModel, Field


class AdviseRequest(BaseModel):
    course_code: str = Field(min_length=1, max_length=16)


class InterventionRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=16)
    course_code: str = Field(min_length=1, max_length=16)
    plan_text: str = Field(min_length=5, max_length=2000)
