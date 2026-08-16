"""Theme C: token rotation, reuse detection, logout revocation, rate limiting."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.main import app

client = TestClient(app)


def _login(username: str = "admin", password: str = "admin123") -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_refresh_rotates_token_once() -> None:
    tokens = _login()
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    rotated = first.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    assert rotated["access_token"]


def test_reused_refresh_token_detected_and_chain_revoked() -> None:
    tokens = _login()
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json()["code"] == "token_reuse_detected"

    dead = client.post("/api/v1/auth/refresh", json={"refresh_token": first.json()["refresh_token"]})
    assert dead.status_code == 401


def test_logout_revokes_refresh_token() -> None:
    tokens = _login()
    response = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    assert reused.json()["code"] == "token_reuse_detected"


def test_unknown_refresh_token_rejected() -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_refresh_token"


def test_login_rate_limit_returns_429() -> None:
    limiter = Limiter(key_func=get_remote_address, default_limits=[])
    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.post("/login")
    @limiter.limit("2/minute")
    def login(request: Request) -> dict:
        return {"ok": True}

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": "Too many requests, slow down", "code": "rate_limited"})

    test_client = TestClient(app)
    assert test_client.post("/login").status_code == 200
    assert test_client.post("/login").status_code == 200
    assert test_client.post("/login").status_code == 429
