"""Authentication service: registration, sessions, token lifecycle.

All DB writes and token issuance live here so endpoints stay thin (Single
Responsibility) and the logic is unit-testable without HTTP.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.user import User, UserSession

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Base class — endpoints map subclasses to HTTP statuses."""


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class InvalidOrExpiredToken(AuthError):
    pass


def audit(db: Session, user_id: Optional[str], action: str, ip: Optional[str] = None,
          **details) -> None:
    """Append an audit row. Failure to log must never break the request."""
    try:
        db.add(AuditLog(user_id=user_id, action=action, ip_address=ip,
                        details=details or None))
        db.commit()
    except Exception:  # pragma: no cover — audit is best-effort
        db.rollback()
        logger.exception("audit write failed for action=%s", action)


def register_user(db: Session, email: str, password: str, full_name: str) -> User:
    """Create an unverified user. Raises EmailAlreadyRegistered on duplicates."""
    email_norm = email.strip().lower()
    if db.query(User).filter(User.email == email_norm).first():
        raise EmailAlreadyRegistered(email_norm)
    user = User(
        email=email_norm,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials. Identical error for unknown email / bad password."""
    email_norm = email.strip().lower()
    user = db.query(User).filter(User.email == email_norm).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials()
    return user


def issue_session(db: Session, user: User) -> Tuple[str, datetime]:
    """Create a refresh-token session row; return (opaque_token, expires_at)."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_refresh_token(token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return token, expires_at


def rotate_session(
    db: Session, presented_token: str
) -> Tuple[User, str, datetime]:
    """Validate + revoke the old refresh session, issue a fresh one.

    Raises InvalidOrExpiredToken when the token is unknown, expired or revoked.
    """
    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_refresh_token(presented_token)
    ).first()
    # SQLite (tests) returns naive datetimes; Postgres returns aware ones.
    # Normalize to aware-UTC so comparison is driver-independent.
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at if session else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        session is None
        or session.revoked_at is not None
        or expires_at is None
        or expires_at < now
    ):
        raise InvalidOrExpiredToken()
    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None or not user.is_active:
        raise InvalidOrExpiredToken()
    # Rotation: the presented token can never be reused.
    session.revoked_at = now
    db.commit()
    new_token, new_expiry = issue_session(db, user)
    return user, new_token, new_expiry


def revoke_session(db: Session, presented_token: str) -> bool:
    """Mark the session revoked. Returns True if a live session was revoked."""
    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_refresh_token(presented_token)
    ).first()
    if session is None or session.revoked_at is not None:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
