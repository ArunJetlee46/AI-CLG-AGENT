from datetime import date

from pydantic import BaseModel, Field


class ShortlistRequest(BaseModel):
    role: str = Field(min_length=1, max_length=128)
    min_gpa: float = Field(default=0.0, ge=0.0, le=4.0)
    max_backlogs: int = Field(default=0, ge=0)
    required_skills: list[str] = []
    limit: int = Field(default=50, ge=1, le=500)


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


class DecideRequest(BaseModel):
    decision: str = Field(pattern=r"^(accepted|rejected)$")


class ApplicationRequest(BaseModel):
    drive_id: str = Field(min_length=1)


class CsvImportType(BaseModel):
    import_type: str = Field(pattern=r"^(companies|jds|drives|selections)$")
