import uuid
from datetime import date, datetime, time
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    email: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    lecturer: Mapped["Lecturer | None"] = relationship(back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[str] = mapped_column(String(16), unique=True)
    year: Mapped[int] = mapped_column(Integer, default=1)
    program: Mapped[str] = mapped_column(String(128), default="")
    gpa: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped[User] = relationship(back_populates="student")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Lecturer(Base):
    __tablename__ = "lecturers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    staff_id: Mapped[str] = mapped_column(String(16), unique=True)
    department: Mapped[str] = mapped_column(String(128), default="")
    max_hours: Mapped[int] = mapped_column(Integer, default=20)

    user: Mapped[User] = relationship(back_populates="lecturer")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    credits: Mapped[int] = mapped_column(Integer, default=3)
    capacity: Mapped[int] = mapped_column(Integer, default=60)
    department: Mapped[str] = mapped_column(String(128), default="")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("approval_requests.id"), nullable=True, index=True)

    student: Mapped[Student] = relationship(back_populates="enrollments")
    course: Mapped[Course] = relationship(back_populates="enrollments")
    result: Mapped["Result | None"] = relationship(back_populates="enrollment", uselist=False)


class Result(Base):
    __tablename__ = "results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id"), unique=True)
    marks: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(2), default="")
    semester: Mapped[str] = mapped_column(String(16), default="")

    enrollment: Mapped[Enrollment] = relationship(back_populates="result")


class AttendanceRecord(Base):
    __tablename__ = "attendance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(8), default="present")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    room_no: Mapped[str] = mapped_column(String(16), unique=True)
    capacity: Mapped[int] = mapped_column(Integer, default=50)
    kind: Mapped[str] = mapped_column(String(32), default="classroom")


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"))
    lecturer_id: Mapped[str] = mapped_column(ForeignKey("lecturers.id"))
    day: Mapped[str] = mapped_column(String(12))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    term: Mapped[str] = mapped_column(String(16), default="")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    shap_values: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterventionPlan(Base):
    __tablename__ = "intervention_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    prediction_id: Mapped[str | None] = mapped_column(ForeignKey("predictions.id"), nullable=True)
    course_code: Mapped[str] = mapped_column(String(16), default="")
    plan_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="drafted")
    notified_lecturer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class InterventionEffectiveness(Base):
    __tablename__ = "intervention_effectiveness"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    intervention_id: Mapped[str] = mapped_column(ForeignKey("intervention_plans.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    course_code: Mapped[str] = mapped_column(String(16), index=True)
    intervention_type: Mapped[str] = mapped_column(String(32))
    baseline_score: Mapped[float] = mapped_column(Float, default=0.0)
    followup_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    improvement: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    intent: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("approval_requests.id"), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class DecisionCard(Base):
    __tablename__ = "decision_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_log_id: Mapped[str] = mapped_column(ForeignKey("audit_logs.id"))
    decision_type: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    reasoning: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(64), default="")
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelRecord(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(255), default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    sector: Mapped[str] = mapped_column(String(64), default="")
    location: Mapped[str] = mapped_column(String(128), default="")
    contact_email: Mapped[str] = mapped_column(String(128), default="")
    contact_phone: Mapped[str] = mapped_column(String(32), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    jds: Mapped[list["JobDescription"]] = relationship(back_populates="company")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    role_type: Mapped[str] = mapped_column(String(32), default="software")
    min_gpa: Mapped[float] = mapped_column(Float, default=2.5)
    max_backlogs: Mapped[int] = mapped_column(Integer, default=0)
    year_required: Mapped[int] = mapped_column(Integer, default=0)
    ctc_min: Mapped[float] = mapped_column(Float, default=0.0)
    ctc_max: Mapped[float] = mapped_column(Float, default=0.0)
    openings: Mapped[int] = mapped_column(Integer, default=1)
    location: Mapped[str] = mapped_column(String(128), default="")
    mode: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship(back_populates="jds")
    drives: Mapped[list["PlacementDrive"]] = relationship(back_populates="jd")


class PlacementDrive(Base):
    __tablename__ = "placement_drives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(128))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    jd_id: Mapped[str | None] = mapped_column(ForeignKey("job_descriptions.id"), nullable=True, index=True)
    drive_date: Mapped[date] = mapped_column(Date)
    mode: Mapped[str] = mapped_column(String(16), default="online")
    location: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship()
    jd: Mapped[JobDescription | None] = relationship(back_populates="drives")
    rounds: Mapped[list["RecruitmentRound"]] = relationship(back_populates="drive", order_by="RecruitmentRound.round_order")
    selections: Mapped[list["PlacementSelection"]] = relationship(back_populates="drive")


class RecruitmentRound(Base):
    __tablename__ = "recruitment_rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    drive_id: Mapped[str] = mapped_column(ForeignKey("placement_drives.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    round_order: Mapped[int] = mapped_column(Integer, default=1)
    round_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    note: Mapped[str] = mapped_column(String(255), default="")

    drive: Mapped[PlacementDrive] = relationship(back_populates="rounds")


class PlacementSelection(Base):
    __tablename__ = "placement_selections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    drive_id: Mapped[str] = mapped_column(ForeignKey("placement_drives.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    round_reached: Mapped[str] = mapped_column(String(64), default="")
    offered_ctc: Mapped[float] = mapped_column(Float, default=0.0)
    offer_status: Mapped[str] = mapped_column(String(16), default="offered")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    drive: Mapped[PlacementDrive] = relationship(back_populates="selections")


class PlacementNotification(Base):
    __tablename__ = "placement_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    drive_id: Mapped[str | None] = mapped_column(ForeignKey("placement_drives.id"), nullable=True, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(16), default="all")
    created_by: Mapped[str] = mapped_column(String(64), default="")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CampusResource(Base):
    __tablename__ = "campus_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(32), default="classroom")
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(24), default="active")
    utilization: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(2000), default="")


class BackupRecord(Base):
    __tablename__ = "backups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="completed")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    lead_name: Mapped[str] = mapped_column(String(64), default="")
    department: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    funding_amount: Mapped[float] = mapped_column(Float, default=0.0)
    publications: Mapped[int] = mapped_column(Integer, default=0)
    start_year: Mapped[int] = mapped_column(Integer, default=2025)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IndustryPartner(Base):
    __tablename__ = "industry_partners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    sector: Mapped[str] = mapped_column(String(64), default="")
    contact_person: Mapped[str] = mapped_column(String(64), default="")
    mous: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    placement_hires: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_notifications_user_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(160))
    type: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(8), default="low")
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(160), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentMemory(Base):
    """Persistent multi-turn agent memory: one row per turn, per actor.

    Backs the supervisor's shared memory so conversations survive restarts
    (Tier 1.4). Kept tiny on purpose - trimmed to the newest N turns per actor
    on every write by `app.agents.memory`.
    """

    __tablename__ = "agent_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
