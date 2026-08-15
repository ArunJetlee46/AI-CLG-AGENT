from fastapi import APIRouter

from app.config import get_settings
from app.db import engine

router = APIRouter(tags=["health"])

settings = get_settings()


@router.get("/health")
def health() -> dict:
    with engine.connect():
        db_ok = True
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "db": "ok" if db_ok else "error",
        "llm_providers": settings.llm_providers,
    }
