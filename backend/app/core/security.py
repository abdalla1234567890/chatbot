from datetime import datetime, timedelta
from typing import Any, Union
import jwt
from passlib.context import CryptContext
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _ensure_jwt_secret():
    """
    Ensure JWT secret is configured.
    - In production: fail fast (do not generate random secrets).
    - In development: allow a transient secret but warn loudly.
    """
    if settings.JWT_SECRET_KEY:
        return
    if (settings.ENVIRONMENT or "").lower() in ("prod", "production"):
        raise RuntimeError("JWT_SECRET_KEY is required in production environment")
    # dev fallback (non-deterministic per process start)
    import secrets
    settings.JWT_SECRET_KEY = secrets.token_hex(32)
    logger.warning("⚠️ JWT_SECRET_KEY not set. Using random dev key for this session.")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    _ensure_jwt_secret()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
