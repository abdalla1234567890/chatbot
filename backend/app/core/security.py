from datetime import datetime, timedelta
from typing import Any, Union, Optional
import jwt
import secrets
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Fallback SECRET_KEY if not set in .env
if not settings.JWT_SECRET_KEY:
    settings.JWT_SECRET_KEY = secrets.token_hex(32)
    logger.warning("⚠️ JWT_SECRET_KEY not set in .env! Using random key for this session.")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
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
    # REVERTED: Using simple string comparison as requested by USER
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    # REVERTED: Just returns the password string
    return password
