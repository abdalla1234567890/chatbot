from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from collections import defaultdict
from datetime import datetime

from app.db import crud, session, models
from app.core import security
from app.core.config import settings
from app.schemas import user as user_schema, token as token_schema

router = APIRouter()

# Brute Force Protection
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300

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

@router.post("/login", response_model=token_schema.Token)
def login(
    request: Request,
    db: Session = Depends(session.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    _check_rate_limit(request)
    user = crud.get_user_by_code(db, code=form_data.username)
    if not user:
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Incorrect code")
    
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
    user = crud.get_user_by_code(db, code=req.code)
    if not user:
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid code")
    
    access_token = security.create_access_token(subject=user.code)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
