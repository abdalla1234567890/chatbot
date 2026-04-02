from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from collections import defaultdict
from datetime import datetime
import random
import logging

from app.db import crud, session, models
from app.core import security
from app.core.config import settings
from app.schemas import user as user_schema, token as token_schema
from app.services.email_service import send_admin_otp_email

router = APIRouter()
logger = logging.getLogger(__name__)

# Brute Force Protection
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300
OTP_EXPIRE_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
_admin_otp_store = {}

def _check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    _login_attempts[client_ip] = [
        t for t in _login_attempts[client_ip]
        if (now - t).total_seconds() < LOGIN_WINDOW_SECONDS
    ]
    if len(_login_attempts[client_ip]) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="محاولات دخول كثيرة. يرجى الانتظار 5 دقائق.")

def _record_failed_attempt(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _login_attempts[client_ip].append(datetime.utcnow())

def _create_otp() -> str:
    return f"{random.randint(0, 999999):06d}"

@router.post("/login", response_model=token_schema.Token)
def login(
    request: Request,
    db: Session = Depends(session.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    _check_rate_limit(request)
    login_code = form_data.username.strip()
    user = crud.get_user_by_code(db, code=login_code)
    if not user:
        logger.warning(f"Login failed: User not found for code {login_code}")
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Incorrect code")
    
    # Verify secret
    if getattr(user, "secret_hash", None):
        is_valid = security.verify_password(login_code, user.secret_hash)
        if not is_valid:
            logger.warning(f"Login failed: Invalid password/code for user {login_code}")
            _record_failed_attempt(request)
            raise HTTPException(status_code=401, detail="Incorrect code")
    else:
        logger.info(f"Upgrading legacy user {user.code} to secret_hash")
        user.secret_hash = security.get_password_hash(user.code)
        db.commit()
    
    access_token = security.create_access_token(subject=user.code)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login_json", response_model=token_schema.Token)
def login_json(
    request: Request,
    req: user_schema.LoginRequest,
    db: Session = Depends(session.get_db)
):
    _check_rate_limit(request)
    login_code = req.code.strip()
    user = crud.get_user_by_code(db, code=login_code)
    if not user:
        logger.warning(f"LoginJSON failed: User not found for code {login_code}")
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid code")
    
    # Verify secret
    if getattr(user, "secret_hash", None):
        is_valid = security.verify_password(login_code, user.secret_hash)
        if not is_valid:
            logger.warning(f"LoginJSON failed: Invalid password/code for user {login_code}")
            _record_failed_attempt(request)
            raise HTTPException(status_code=401, detail="Invalid code")
    else:
        logger.info(f"Upgrading legacy user {user.code} in login_json")
        user.secret_hash = security.get_password_hash(user.code)
        db.commit()

    if user.is_admin:
        raise HTTPException(status_code=403, detail="Admin OTP required")
    
    access_token = security.create_access_token(subject=user.code)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/admin/login/start")
def admin_login_start(
    request: Request,
    req: user_schema.AdminOTPStartRequest,
    db: Session = Depends(session.get_db)
):
    _check_rate_limit(request)
    login_code = req.code.strip()
    user = crud.get_user_by_code(db, code=login_code)
    if not user:
        logger.warning(f"AdminLoginStart failed: User not found for code {login_code}")
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid code")

    if getattr(user, "secret_hash", None):
        is_valid = security.verify_password(login_code, user.secret_hash)
        if not is_valid:
            logger.warning(f"AdminLoginStart failed: Invalid password/code for user {login_code}")
            _record_failed_attempt(request)
            raise HTTPException(status_code=401, detail="Invalid code")
    else:
        logger.info(f"Upgrading legacy user {user.code} in admin_login_start")
        user.secret_hash = security.get_password_hash(user.code)
        db.commit()

    if not user.is_admin:
        logger.warning("admin_login_start_non_admin code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=403, detail="Not an admin account")

    to_email = settings.ADMIN_OTP_EMAIL
    if not to_email:
        logger.error("admin_login_start_missing_admin_email code=%s", user.code)
        raise HTTPException(status_code=500, detail="ADMIN_OTP_EMAIL is not configured")

    otp = _create_otp()
    _admin_otp_store[user.code] = {
        "otp_hash": security.get_password_hash(otp),
        "expires_at": datetime.utcnow(),
        "attempts": 0,
    }
    _admin_otp_store[user.code]["expires_at"] = _admin_otp_store[user.code]["expires_at"] + timedelta(seconds=OTP_EXPIRE_SECONDS)

    try:
        send_admin_otp_email(to_email, otp)
        logger.info("admin_login_start_otp_sent code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
    except Exception:
        _admin_otp_store.pop(user.code, None)
        logger.exception("admin_login_start_otp_send_failed code=%s", user.code)
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"otp_required": True, "msg": "OTP sent to admin email"}

@router.post("/admin/login/verify", response_model=token_schema.Token)
def admin_login_verify(
    req: user_schema.AdminOTPVerifyRequest,
    request: Request,
    db: Session = Depends(session.get_db)
):
    user = crud.get_user_by_code(db, code=req.code)
    if not user or not user.is_admin:
        logger.warning("admin_login_verify_invalid_admin code=%s ip=%s", req.code, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    record = _admin_otp_store.get(user.code)
    if not record:
        logger.warning("admin_login_verify_missing_or_expired code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="OTP not found or expired")

    if datetime.utcnow() > record["expires_at"]:
        _admin_otp_store.pop(user.code, None)
        logger.warning("admin_login_verify_expired code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="OTP expired")

    if record["attempts"] >= OTP_MAX_ATTEMPTS:
        _admin_otp_store.pop(user.code, None)
        logger.warning("admin_login_verify_too_many_attempts code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=429, detail="Too many OTP attempts")

    if not security.verify_password(req.otp, record["otp_hash"]):
        record["attempts"] += 1
        logger.warning("admin_login_verify_invalid_otp code=%s attempts=%s ip=%s", user.code, record["attempts"], request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid OTP")

    _admin_otp_store.pop(user.code, None)
    access_token = security.create_access_token(subject=user.code)
    logger.info("admin_login_verify_success code=%s ip=%s", user.code, request.client.host if request.client else "unknown")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
