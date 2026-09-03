"""
Coupon Sentinel - Authentication

JWT-based auth (register / login / refresh) plus the get_current_user
dependency used to gate tier-restricted endpoints.

JWT_SECRET must be set in production; a random per-process secret is used as
a local-dev fallback so tokens simply won't survive a restart.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models import User
from backend.engines.analytics_engine import track_event
from backend.engines.email_engine import send_email

JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
EMAIL_VERIFICATION_EXPIRE_HOURS = 24
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================================
# Password hashing
# ============================================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


# ============================================================================
# JWT tokens
# ============================================================================

def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def create_email_verification_token(user_id: int) -> str:
    return _create_token(
        str(user_id), timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS), "email_verification"
    )


def decode_token(token: str, expected_type: str) -> str:
    """Return the subject (user id as str), or raise HTTPException(401)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return subject


# ============================================================================
# Request/response schemas
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: str
    tier: str
    is_email_verified: bool

    model_config = {"from_attributes": True}


# ============================================================================
# Dependencies
# ============================================================================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    user_id = decode_token(credentials.credentials, expected_type="access")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Like get_current_user, but never raises — missing, expired, or invalid
    credentials just resolve to None. For endpoints that work both signed-out
    and signed-in (POST /api/optimize: always usable, but persists a plan +
    tracks an analytics event tied to the user when they're authenticated).
    """
    if credentials is None:
        return None
    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except HTTPException:
        return None
    return db.get(User, int(user_id))


def require_tier(*allowed_tiers: str):
    """Dependency factory gating an endpoint to specific subscription tiers."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.tier not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"This feature requires one of: {', '.join(allowed_tiers)}",
            )
        return user

    return _dependency


# ============================================================================
# Routes
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=request.email, password_hash=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    track_event("signup", db, user_id=user.id)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    track_event("login", db, user_id=user.id)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(request.refresh_token, expected_type="refresh")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/resend-verification")
async def resend_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Send (or resend) the email verification link.

    Not called automatically on register — a registration succeeding
    shouldn't depend on an email provider being configured. Returns 503
    if neither RESEND_API_KEY nor SENDGRID_API_KEY is set, same pattern as
    Stripe/Kroger, rather than silently pretending the email went out.
    """
    if user.is_email_verified:
        return {"status": "already_verified"}

    token = create_email_verification_token(user.id)
    verify_link = f"{FRONTEND_URL}/verify-email?token={token}"

    send_email(
        to=user.email,
        subject="Verify your Coupon Sentinel email",
        html=f'<p>Confirm your email for Coupon Sentinel:</p><p><a href="{verify_link}">{verify_link}</a></p>'
        f"<p>This link expires in {EMAIL_VERIFICATION_EXPIRE_HOURS} hours.</p>",
    )
    return {"status": "sent"}


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    user_id = decode_token(request.token, expected_type="email_verification")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_email_verified = True
    db.commit()
    return {"status": "verified", "email": user.email}
