from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

_engine_kwargs = {"connect_args": connect_args, "pool_pre_ping": True}
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_recycle"] = 3600

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


def _migrate_sqlite() -> None:
    """Lightweight SQLite migrations for columns added after the first boot.

    `create_all` never alters existing tables, so new columns on existing DBs
    are added here (audit approval_id) or the table is rebuilt when it is empty
    (intervention_plans gained student/course columns and a nullable FK).
    """
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("audit_logs"):
        return
    audit_cols = {c["name"] for c in insp.get_columns("audit_logs")}
    if "approval_id" not in audit_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN approval_id VARCHAR(36)"))

    if insp.has_table("enrollments"):
        enroll_cols = {c["name"] for c in insp.get_columns("enrollments")}
        if "approval_id" not in enroll_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE enrollments ADD COLUMN approval_id VARCHAR(36)"))

    if insp.has_table("intervention_plans"):
        plan_cols = {c["name"] for c in insp.get_columns("intervention_plans")}
        if "student_id" not in plan_cols or "course_code" not in plan_cols:
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM intervention_plans")).scalar_one()
            if count == 0:
                with engine.begin() as conn:
                    conn.execute(text("DROP TABLE intervention_plans"))
                Base.metadata.create_all(bind=engine)
            else:
                import logging

                logging.getLogger(__name__).warning(
                    "intervention_plans has rows and is missing new columns; "
                    "drop the table to apply the schema"
                )

    if insp.has_table("announcements"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE announcements SET audience = 'all' WHERE audience = 'everyone'"
                )
            )
            conn.execute(
                text(
                    "UPDATE announcements SET audience = 'student' WHERE audience = 'students'"
                )
            )
            conn.execute(
                text(
                    "UPDATE announcements SET audience = 'lecturer' WHERE audience = 'faculty'"
                )
            )
