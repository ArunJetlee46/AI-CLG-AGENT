import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, multiprocess
from prometheus_client import Counter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import (
    admin_module,
    agent_plugins,
    agents,
    approvals,
    audit,
    auth,
    degree_audit,
    faculty,
    health,
    interventions,
    notifications,
    placement,
    predictions,
    students,
    synthetic,
)
from app.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    request_context_middleware,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.ratelimit import limiter
from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.models.entities import User

logger = logging.getLogger(__name__)
settings = get_settings()

REQUESTS = Counter("beru_http_requests_total", "HTTP requests", ["method", "path", "status"])

_DEFAULT_SECRET = "dev-secret-change-me"
_DEFAULT_ADMIN_PASSWORD = "admin123"


def assert_secure_boot(settings) -> None:
    """Refuse to boot in production with default credentials.

    A warning is easy to miss; a failed boot is not. Call this before any
    database seeding so nothing with default credentials can start in prod.
    """
    if settings.app_env != "production":
        return
    problems = []
    if settings.secret_key == _DEFAULT_SECRET:
        problems.append("SECRET_KEY is still the documented default 'dev-secret-change-me'")
    if settings.default_admin_password == _DEFAULT_ADMIN_PASSWORD:
        problems.append("DEFAULT_ADMIN_PASSWORD is still the documented default 'admin123'")
    if "*" in settings.cors_origin_list:
        problems.append("CORS_ORIGINS is wide open ('*')")
    if problems:
        raise RuntimeError(
            "Refusing to start in production: " + "; ".join(problems)
            + ". Set SECRET_KEY and DEFAULT_ADMIN_PASSWORD (or a JWT_SECRET) before deploying."
        )


def seed_default_admin() -> None:
    db = SessionLocal()
    try:
        exists = db.execute(select(User).where(User.username == settings.default_admin_user)).scalar_one_or_none()
        if exists is None:
            db.add(
                User(
                    username=settings.default_admin_user,
                    password_hash=hash_password(settings.default_admin_password),
                    role="admin",
                    email="admin@beru.edu",
                )
            )
            db.commit()
            logger.info("Seeded default admin user '%s'", settings.default_admin_user)
    finally:
        db.close()


DEMO_USERS = [
    ("student", "student123", "student", "student@beru.edu"),
    ("lecturer", "lecturer123", "lecturer", "lecturer@beru.edu"),
    ("placement", "placement123", "placement", "placement@beru.edu"),
]

# Built-in knowledge corpus so grounded RAG answers work out of the box.
KNOWLEDGE_CORPUS = [
    {
        "source": "about",
        "title": "Beru Campus AI",
        "text": (
            "Beru Campus AI is the digital assistant of Beru University. It answers questions about "
            "courses, registration, fees, library services, and student risk. It is built on a hybrid "
            "retrieval pipeline with keyword search, vector embeddings, and an LLM gateway that prefers "
            "the local Ollama model (llama3.2:3b) and falls back to Groq or Gemini when configured."
        ),
    },
    {
        "source": "library",
        "title": "Library",
        "text": (
            "The Beru University central library is open Monday to Friday from 08:00 to 22:00, and on "
            "weekends from 10:00 to 18:00. Quiet study floors require a valid student card. Borrowing "
            "rules: 4 books for 21 days, renewable twice unless another reader has reserved the item."
        ),
    },
    {
        "source": "finance",
        "title": "Tuition and Fees",
        "text": (
            "Undergraduate tuition for the current session is 480,000 FCFA per year. Payment is due in "
            "full by 31 October, or in two installments: 50% at registration and 50% by 28 February. "
            "Students with a GPA above 3.5 can apply for a merit scholarship covering 50% of tuition."
        ),
    },
    {
        "source": "academics",
        "title": "Course Registration",
        "text": (
            "Students register for courses during the first two weeks of each semester. Minimum load is "
            "12 credits, maximum 21. A course with fewer than 10 enrolled students may be cancelled. "
            "Students at risk of failing a course can request tutoring through the faculty office."
        ),
    },
    {
        "source": "academics",
        "title": "Academic Calendar",
        "text": (
            "The academic year has two semesters. Semester one runs from mid-September to mid-January "
            "with exams in January. Semester two runs from early February to mid-June with exams in "
            "June. Results are published within three weeks of the last exam and can be checked on the "
            "student portal and at the faculty office."
        ),
    },
    {
        "source": "student-life",
        "title": "Accommodation and Transport",
        "text": (
            "On-campus accommodation is available in the two student residences, with room allocation "
            "handled at registration. Shuttle buses run between the campus and the city centre every "
            "30 minutes from 06:30 to 20:30 on weekdays and until 18:00 on weekends. A student travel "
            "card gives a 40% discount on the shuttle service."
        ),
    },
    {
        "source": "student-life",
        "title": "Student Services",
        "text": (
            "The student health centre is open Monday to Friday from 08:00 to 17:00 for consultations "
            "and emergency first aid. The careers office organises placement interviews twice a year "
            "and maintains a list of partner companies. Psychological support sessions are available "
            "by appointment through the faculty office."
        ),
    },
    {
        "source": "academics",
        "title": "Exams and Grading",
        "text": (
            "Exams take place at the end of each semester. The grading scale runs from A (excellent) "
            "to F (fail); a grade below C in a core course requires a retake. Attendance below 75% in "
            "any course makes a student ineligible to sit the final exam for that course. Results and "
            "grade appeals are handled by the faculty examination committee within two weeks."
        ),
    },
    {
        "source": "finance",
        "title": "Scholarships and Financial Aid",
        "text": (
            "Merit scholarships cover 50% of tuition for students with a GPA above 3.5. Need-based aid "
            "is available through the financial aid office; applications open in August for the next "
            "academic year. Work-study positions on campus are posted at the finance office notice board."
        ),
    },
]


def _load_kb_docs_from_disk() -> list[dict]:
    """Load pre-chunked KB docs from the data directory (if present):
    - */*_rag.jsonl          pre-chunked RAG corpus  [{id, source, document, content}]
    - course_index.json      241-course catalog      -> ingested as one catalog doc
    Returns [] when no data files exist (caller falls back to the built-in corpus).
    """
    import json
    from pathlib import Path

    data_dir = Path(settings.knowledge_data_dir)
    if not data_dir.is_dir():
        logger.info("Knowledge data dir '%s' not found; skipping disk load", data_dir)
        return []

    docs: list[dict] = []
    source_label = settings.knowledge_source_label
    for jsonl_path in sorted(data_dir.glob("*_rag.jsonl")):
        file_docs: list[dict] = []
        try:
            with jsonl_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    file_docs.append(
                        {
                            "id": item.get("id") or f"{jsonl_path.stem}:{len(docs)}",
                            "source": source_label,
                            "title": item.get("document") or jsonl_path.stem,
                            "text": item.get("content", ""),
                        }
                    )
            docs.extend(file_docs)
            logger.info("Loaded %d chunks from %s", len(file_docs), jsonl_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load %s: %s", jsonl_path, exc)

    index_path = data_dir / "course_index.json"
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            catalog = [
                f"{c['course_code']} - {c['course_title']}" for c in index.get("courses", [])
            ]
            if catalog:
                docs.append(
                    {
                        "source": source_label,
                        "title": "Course Catalog",
                        "text": "Full course catalog:\n" + "\n".join(catalog),
                    }
                )
                logger.info("Loaded course catalog with %d courses", len(catalog))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load %s: %s", index_path, exc)
    return docs


def seed_knowledge_base() -> None:
    from app.services.pipeline import get_keyword_index, ingest_documents

    index = get_keyword_index()
    if index.count():
        return
    docs = _load_kb_docs_from_disk() or KNOWLEDGE_CORPUS
    stats = ingest_documents(docs)
    logger.info("Seeded knowledge base: %s", stats)


def seed_db_rag_backfill() -> None:
    """Render real database rows (courses, lecturers, placements, ...) into the
    RAG corpus so answers can be grounded on the institution's actual data."""
    if not settings.db_rag_backfill_enabled:
        logger.info("Database RAG backfill disabled (DB_RAG_BACKFILL_ENABLED=false)")
        return
    try:
        from app.services.rag.backfill import backfill_from_db

        stats = backfill_from_db()
        logger.info("Database RAG backfill complete: %s", stats)
    except Exception as exc:  # noqa: BLE001 - a failing backfill must not stop boot
        logger.warning("Database RAG backfill failed: %s", exc)


def seed_curriculum_knowledge_base() -> None:
    from app.services.pipeline import ingest_curriculum

    stats = ingest_curriculum()
    logger.info("Seeded curriculum knowledge base: %s", stats)


def seed_demo_users() -> None:
    db = SessionLocal()
    try:
        for username, password, role, email in DEMO_USERS:
            exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if exists is None:
                db.add(User(username=username, password_hash=hash_password(password), role=role, email=email))
        db.commit()
        logger.info("Seeded demo users: %s", [u[0] for u in DEMO_USERS])
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_secure_boot(settings)
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sentry init skipped: %s", exc)
    init_db()
    seed_default_admin()
    seed_demo_users()
    seed_knowledge_base()
    seed_db_rag_backfill()
    seed_curriculum_knowledge_base()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in cors_origins else cors_origins,
    allow_credentials="*" in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.middleware("http")(request_context_middleware)


@app.middleware("http")
async def count_requests(request, call_next):
    response = await call_next(request)
    REQUESTS.labels(method=request.method, path=request.url.path, status=response.status_code).inc()
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests, slow down", "code": "rate_limited"},
        headers={"Retry-After": "60"},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(faculty.router, prefix="/api/v1")
app.include_router(placement.router, prefix="/api/v1")
app.include_router(admin_module.router, prefix="/api/v1")
app.include_router(interventions.router, prefix="/api/v1")
app.include_router(degree_audit.router, prefix="/api/v1")
app.include_router(agent_plugins.router, prefix="/api/v1")
app.include_router(synthetic.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")


@app.middleware("http")
async def count_requests(request, call_next):
    response = await call_next(request)
    REQUESTS.labels(method=request.method, path=request.url.path, status=response.status_code).inc()
    return response


@app.get("/metrics")
def metrics() -> Response:
    registry = CollectorRegistry()
    registry.register(REQUESTS)
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
