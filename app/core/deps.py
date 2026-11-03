"""FastAPI dependencies for authentication and RBAC.

``get_current_user``   — hard requirement (401 when absent/invalid).
``get_optional_user``  — None when unauthenticated (guest-capable endpoints).
``require_role(...)``  — factory producing role-gated dependencies (403).
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    TokenError,
    decode_access_token,
)
from app.models.user import User

# auto_error=False lets us produce a consistent 401 body ourselves.
_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials is None or not credentials.credentials:
        return None
    return credentials.credentials


def _load_active_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )
    return user


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from a Bearer JWT. 401 on any failure."""
    token = _extract_token(credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _load_active_user(db, payload["sub"])


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Same as get_current_user but returns None instead of raising."""
    token = _extract_token(credentials)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except TokenError:
        return None
    try:
        return _load_active_user(db, payload["sub"])
    except HTTPException:
        return None


def require_role(*roles: str):
    """Dependency factory: allow only the listed roles (403 otherwise)."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker
