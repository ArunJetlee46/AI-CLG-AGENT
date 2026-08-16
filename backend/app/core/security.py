from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, role: str, expires_delta: timedelta, token_type: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm), jti


def create_access_token(subject: str, role: str) -> str:
    token, _ = _create_token(subject, role, timedelta(minutes=settings.access_token_expire_minutes), "access")
    return token


def create_refresh_token(subject: str, role: str) -> tuple[str, str]:
    """Return (token, jti); callers persist the jti for rotation/reuse detection."""
    return _create_token(subject, role, timedelta(days=settings.refresh_token_expire_days), "refresh")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
