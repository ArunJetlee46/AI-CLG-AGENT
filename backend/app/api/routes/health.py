from fastapi import APIRouter, Response

from app.config import get_settings
from app.db import engine

router = APIRouter(tags=["health"])

settings = get_settings()


@router.get("/health")
def health() -> Response:
    db_ok = False
    llm_ok = False
    try:
        with engine.connect():
            db_ok = True
    except Exception:
        pass

    for provider in settings.llm_providers:
        if provider == "ollama":
            try:
                import urllib.request
                req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        llm_ok = True
                        break
            except Exception:
                pass
        elif provider in ("groq", "gemini"):
            llm_ok = True

    healthy = db_ok and (llm_ok or len(settings.llm_providers) == 0)
    status_code = 200 if healthy else 503

    return Response(
        content=__import__("json").dumps({
            "status": "ok" if healthy else "degraded",
            "app": settings.app_name,
            "env": settings.app_env,
            "db": "ok" if db_ok else "error",
            "llm_providers": settings.llm_providers,
            "llm_reachable": llm_ok,
        }),
        status_code=status_code,
        media_type="application/json",
    )
