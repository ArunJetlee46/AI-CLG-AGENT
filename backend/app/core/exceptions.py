import logging
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Domain error with an HTTP status and a stable machine-readable code.

    Usage: raise AppError(status_code=409, code="enrollment_exists", detail="...")
    """

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": "http_error"})


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed", "code": "validation_error", "errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled error (request_id=%s): %s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error", "request_id": request_id},
    )


async def request_context_middleware(request: Request, call_next):
    """Assigns X-Request-ID and logs request/response timing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
    request.state.request_id = request_id

    import time

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # call_next re-raises into the exception handlers; log here then re-raise
        logger.warning("request %s %s %s failed after %.1fms", request_id, request.method, request.url.path,
                       (time.perf_counter() - started) * 1000)
        raise
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info("%s %s %s -> %s (%.1fms)", request_id, request.method, request.url.path,
                response.status_code, duration_ms)
    return response
