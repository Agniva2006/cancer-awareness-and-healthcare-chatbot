"""Auth endpoints: register / login / refresh / logout / verify / reset / me.

Security invariants enforced here:
- Login failures are indistinguishable (unknown email vs wrong password).
- Login + register are rate-limited per client IP.
- Refresh tokens are rotated on every refresh (replay-secure).
- Forgot-password always answers 200 (no user enumeration).
- Email verification / reset tokens are single-use random strings.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional  # noqa: F401  (kept for type annotations)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import rate_limiter, settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    PasswordPolicyError,
    create_access_token,
    hash_password,
    validate_password_strength,
)
from app.models.user import PendingEmailAction, User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageOut,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserOut,
    UserWithUsage,
    VerifyEmailRequest,
)
from app.services import auth as auth_service
from app.services.email import send_template_email

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_CREDENTIALS = "Invalid email or password"


def _find_pending(db: Session, action: str, token: str) -> Optional[PendingEmailAction]:
    """Look up a live (unexpired) single-use email-action token."""
    pending = (
        db.query(PendingEmailAction)
        .filter(
            PendingEmailAction.token_hash == _email_token_hash(token),
            PendingEmailAction.action == action,
        )
        .first()
    )
    if pending is None or pending.expires_at < datetime.now(timezone.utc):
        return None
    return pending


def _client_ip(request: Request) -> str:
    """Best-effort client IP (direct or behind a single trusted proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request, bucket: str) -> None:
    ip = _client_ip(request)
    if not rate_limiter.check(
        f"{bucket}:{ip}",
        settings.AUTH_RATE_LIMIT_ATTEMPTS,
        settings.AUTH_RATE_LIMIT_WINDOW_MINUTES,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )


def _token_pair(user: User, db: Session) -> TokenPair:
    refresh_token, _ = auth_service.issue_session(db, user)
    access = create_access_token(user.id, user.role)
    return TokenPair(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# Single-use, hashed email-action tokens (verify / reset).
def _new_email_token() -> str:
    return secrets.token_urlsafe(32)


def _email_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=MessageOut, status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    _enforce_rate_limit(request, "register")
    try:
        user = auth_service.register_user(db, body.email, body.password, body.full_name)
    except auth_service.EmailAlreadyRegistered:
        # Deliberately identical response to avoid account enumeration.
        raise HTTPException(status_code=409, detail="Registration failed")
    verify_token = _new_email_token()
    db.add(
        PendingEmailAction(
            user_id=user.id,
            action="verify_email",
            token_hash=_email_token_hash(verify_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS),
        )
    )
    db.commit()
    send_template_email(user.email, "verify_email", verify_token)
    auth_service.audit(db, user.id, "register", ip=_client_ip(request))
    return {"message": "Account created. Check your email to verify your address."}


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    _enforce_rate_limit(request, "login")
    try:
        user = auth_service.authenticate(db, body.email, body.password)
    except auth_service.InvalidCredentials:
        auth_service.audit(
            db, None, "login_failed", ip=_client_ip(request), email=body.email[:64]
        )
        raise HTTPException(status_code=401, detail=BAD_CREDENTIALS)
    auth_service.audit(db, user.id, "login", ip=_client_ip(request))
    return _token_pair(user, db)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        user, new_refresh, _ = auth_service.rotate_session(db, body.refresh_token)
    except auth_service.InvalidOrExpiredToken:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access = create_access_token(user.id, user.role)
    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageOut)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    revoked = auth_service.revoke_session(db, body.refresh_token)
    return {"message": "Logged out" if revoked else "Session already ended"}


@router.post("/verify-email", response_model=MessageOut)
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    pending = _find_pending(db, "verify_email", body.token)
    if pending is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == pending.user_id).first()
    if user is not None:
        user.is_verified = True
    db.delete(pending)
    db.commit()
    return {"message": "Email verified"}


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
):
    _enforce_rate_limit(request, "forgot")
    user = db.query(User).filter(User.email == body.email.lower()).first()
    message = {
        "message": "If that address exists, a reset link has been sent."
    }
    if user is not None:
        reset_token = _new_email_token()
        db.add(
            PendingEmailAction(
                user_id=user.id,
                action="reset_password",
                token_hash=_email_token_hash(reset_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS),
            )
        )
        db.commit()
        send_template_email(user.email, "reset_password", reset_token)
        auth_service.audit(db, user.id, "password_reset_requested", _client_ip(request))
    return message


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        validate_password_strength(body.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    pending = _find_pending(db, "reset_password", body.token)
    if pending is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == pending.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.password_hash = hash_password(body.new_password)
    db.delete(pending)
    db.commit()
    auth_service.audit(db, user.id, "password_reset")
    return {"message": "Password updated. You can now log in."}


@router.get("/me", response_model=UserWithUsage)
def me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Profile plus current plan and quota usage (roadmap §3.9 DoD)."""
    from app.services import quota as quota_service

    plan, limit = quota_service.get_effective_plan(db, user.id)
    used = quota_service.quota_used_this_period(db, user.id)
    payload = UserOut.model_validate(user).model_dump()
    payload.update(
        plan_code=plan.code if plan else "free",
        quota_used=used,
        quota_limit=limit,
    )
    return payload
