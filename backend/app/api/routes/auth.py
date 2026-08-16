import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.ratelimit import limiter
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db import get_db
from app.models.entities import RefreshToken, User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)
settings = get_settings()


def _issue_token_pair(user: User, db: Session) -> TokenResponse:
    refresh_token, jti = create_refresh_token(user.id, user.role)
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    username = (body.username or "").strip()
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        user = (
            db.execute(select(func.lower(User.username) == username.lower()))
            .scalars()
            .first()
        )
    if user is None or not verify_password(body.password, user.password_hash):
        logger.warning("Login failed for username=%r", username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except ValueError as exc:
        raise AppError(status_code=401, code="invalid_refresh_token", detail=str(exc)) from exc
    if payload.get("type") != "refresh":
        raise AppError(status_code=401, code="invalid_refresh_token", detail="Not a refresh token")
    user = db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise AppError(status_code=401, code="invalid_refresh_token", detail="User not found or inactive")

    stored = db.execute(select(RefreshToken).where(RefreshToken.jti == payload.get("jti", ""))).scalar_one_or_none()
    if stored is None:
        raise AppError(status_code=401, code="invalid_refresh_token", detail="Refresh token is not known")
    if stored.revoked:
        # Replay of a rotated token: assume theft and revoke the whole chain.
        for sibling in db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id)).scalars():
            sibling.revoked = True
        db.commit()
        raise AppError(status_code=401, code="token_reuse_detected", detail="Refresh token has already been used")
    if stored.expires_at < datetime.utcnow():
        raise AppError(status_code=401, code="invalid_refresh_token", detail="Refresh token has expired")

    stored.revoked = True  # rotation: each refresh token can be used exactly once
    db.commit()
    return _issue_token_pair(user, db)


@router.post("/logout")
def logout(body: RefreshRequest | None = None, db: Session = Depends(get_db)) -> dict:
    if body is None or not body.refresh_token:
        return {"ok": True}
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        return {"ok": True}
    stored = db.execute(select(RefreshToken).where(RefreshToken.jti == payload.get("jti", ""))).scalar_one_or_none()
    if stored is not None:
        stored.revoked = True
        db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/roles")
def roles() -> dict:
    return {"roles": ["student", "lecturer", "placement", "admin"]}
