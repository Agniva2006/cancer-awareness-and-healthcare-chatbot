"""Password hashing, JWT issuing and password-policy enforcement.

Design decisions (documented, not accidental):
- bcrypt for passwords (industry standard, memory-hard-ish, timing-safe check
  via passlib-free direct ``bcrypt`` usage).
- JWT access tokens are SHORT-LIVED and stateless (15 min default).
- Refresh tokens are OPAQUE random strings, stored only as SHA-256 hashes in
  the ``sessions`` table — a DB leak must never expose usable tokens.
- All failures raise typed exceptions so endpoints can map them to precise
  HTTP statuses without string matching.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.core.config import settings


# ── Typed errors ─────────────────────────────────────────────────
class TokenError(Exception):
    """Base class for all token verification failures."""


class TokenExpiredError(TokenError):
    pass


class TokenInvalidError(TokenError):
    pass


class PasswordPolicyError(ValueError):
    """Raised when a candidate password violates the policy."""


# ── Password policy ──────────────────────────────────────────────
_MIN_PASSWORD_LEN = 10
_UPPER_RE = re.compile(r"[A-Z]")
_LOWER_RE = re.compile(r"[a-z]")
_DIGIT_RE = re.compile(r"\d")


def validate_password_strength(password: str) -> None:
    """Raise :class:`PasswordPolicyError` if the password is too weak."""
    errors = []
    if len(password) < _MIN_PASSWORD_LEN:
        errors.append(f"must be at least {_MIN_PASSWORD_LEN} characters")
    if not _UPPER_RE.search(password):
        errors.append("must contain an uppercase letter")
    if not _LOWER_RE.search(password):
        errors.append("must contain a lowercase letter")
    if not _DIGIT_RE.search(password):
        errors.append("must contain a digit")
    if errors:
        raise PasswordPolicyError("Password " + "; ".join(errors))


# ── Hashing ──────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password with bcrypt. bcrypt truncates at 72 bytes — enforce it."""
    if len(password.encode("utf-8")) > 72:
        raise PasswordPolicyError("Password must be at most 72 bytes")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time password check. Never raises on malformed hashes."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ── JWT access tokens ────────────────────────────────────────────
_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    secret = settings.JWT_SECRET
    if len(secret) < 32 and not settings.DEBUG:
        raise RuntimeError("JWT_SECRET must be >= 32 chars in production")
    return secret


def create_access_token(
    user_id: str, role: str, expires_minutes: Optional[int] = None
) -> str:
    """Signed JWT carrying the minimum identity claims needed per request."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now
        + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify signature + expiry; raise typed errors, never return None."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Token invalid") from exc
    if payload.get("type") != "access":
        raise TokenInvalidError("Wrong token type")
    if "sub" not in payload:
        raise TokenInvalidError("Token missing subject")
    return payload


# ── Opaque refresh tokens ────────────────────────────────────────
def create_refresh_token() -> str:
    """Return an opaque token. Callers store ONLY hash_refresh_token(token)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest — what goes in the DB, never the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_tokens_match(token: str, token_hash: str) -> bool:
    """Timing-safe comparison of a presented token against a stored hash."""
    return hmac.compare_digest(hash_refresh_token(token), token_hash)
