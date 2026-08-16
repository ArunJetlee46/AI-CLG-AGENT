import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["LLM_PROVIDER_ORDER"] = "ollama"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:9"  # unreachable -> forces local-fallback path
os.environ["GROQ_API_KEY"] = ""  # hermetic: a dev key in .env must never leak into tests
os.environ["GEMINI_API_KEY"] = ""  # hermetic: same for Gemini
os.environ["AGENT_LLM_REASONING_STAGES"] = "router,planner,reflect,critic"  # exercise every stage in tests
os.environ["CURRICULUM_RAG_ENABLED"] = "false"  # tests must not depend on the curriculum RAG
os.environ["EMBEDDING_BACKEND"] = "local"  # tests never download ONNX artifacts -> hash embeddings

import pytest

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.models.entities import User


@pytest.fixture(autouse=True, scope="session")
def _prepare_db():
    init_db()
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin", email="admin@beru.edu"))
            db.commit()
    finally:
        db.close()
    yield
