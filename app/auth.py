"""
app/auth.py — OncoGraph AI Authentication & Authorization
JWT-based auth with bcrypt password hashing and per-plan rate limiting.
"""

import os
import time
import json
import secrets
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

# SECRET_KEY priority:
#  1. ONCOGRAPH_SECRET_KEY / JWT_SECRET / SECRET_KEY environment variables
#  2. Persistent file on disk (local dev / data/.jwt_secret)
#  3. Stable default fallback key (prevents token invalidation across Render spin-down cycles)

# JWT configuration — fail closed if no secret is configured
SECRET_KEY = os.environ.get("ONCOGRAPH_SECRET_KEY", "").strip()

if not SECRET_KEY:
    if os.environ.get("APP_ENV", "").lower() == "production":
        raise RuntimeError(
            "ONCOGRAPH_SECRET_KEY must be configured in production"
        )

    # Local development only; do not use this for production.
    secret_file = (
        Path(__file__).resolve().parent.parent
        / "data"
        / ".jwt_secret"
    )
    if secret_file.exists():
        SECRET_KEY = secret_file.read_text().strip()

    if not SECRET_KEY:
        raise RuntimeError(
            "Configure ONCOGRAPH_SECRET_KEY or a local development secret"
        )

if len(SECRET_KEY) < 32:
    raise RuntimeError("JWT secret must be at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
# ──────────────────────────────────────────────
# Plan definitions
# ──────────────────────────────────────────────

PLANS: Dict[str, dict] = {
    "free": {
        "name": "Free",
        "price": 0,
        "price_label": "$0/month",
        "daily_quota": 10,
        "monthly_quota": 100,
        "features": {
            "chat": True,
            "graph": False,
            "tumor_board": False,
            "federated": False,
            "ml_prognosis": False,
            "image_upload": False,
            "export": True,
            "voice": True,
            "priority_support": False,
        },
        "badge_color": "#64748b",
        "description": "Basic cancer Q&A for patients and caregivers",
        "highlights": [
            "10 AI queries per day",
            "Basic cancer chatbot",
            "Chat history & export",
            "Voice input & TTS",
        ],
    },
    "clinical": {
        "name": "Clinical",
        "price": 49,
        "price_label": "$49/month",
        "daily_quota": 500,
        "monthly_quota": 10000,
        "features": {
            "chat": True,
            "graph": True,
            "tumor_board": False,
            "federated": False,
            "ml_prognosis": True,
            "image_upload": True,
            "export": True,
            "voice": True,
            "priority_support": False,
        },
        "badge_color": "#6366f1",
        "description": "For oncologists & clinical teams",
        "highlights": [
            "500 AI queries per day",
            "Knowledge Graph Explorer",
            "ML Prognosis Predictor",
            "DICOM image analysis",
            "Clinical mode & ICD-10 codes",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 199,
        "price_label": "$199/month",
        "daily_quota": 999999,
        "monthly_quota": 999999,
        "features": {
            "chat": True,
            "graph": True,
            "tumor_board": True,
            "federated": True,
            "ml_prognosis": True,
            "image_upload": True,
            "export": True,
            "voice": True,
            "priority_support": True,
        },
        "badge_color": "#f59e0b",
        "description": "Full platform for hospital networks",
        "highlights": [
            "Unlimited queries",
            "Virtual Tumor Board (4 AI agents)",
            "Federated Learning Network",
            "All Clinical features",
            "Priority support & SLA",
        ],
    },
}

# ──────────────────────────────────────────────
# Password hashing — Direct bcrypt with passlib fallback
# (Avoids passlib unmaintained bcrypt __about__ version bug)
# ──────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _truncate_password(password: str) -> bytes:
    # bcrypt allows max 72 bytes. Safely truncate or encode.
    return str(password).encode("utf-8")[:72]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8")[:72],
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = _truncate_password(plain_password)
        hash_bytes = str(hashed_password).strip().encode("utf-8")
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        elif hashed_password.startswith("sha256$"):
            parts = hashed_password.split("$")
            if len(parts) == 3:
                _, salt_hex, digest = parts
                test_digest = hashlib.sha256(f"{salt_hex}:{plain_password}".encode("utf-8")).hexdigest()
                return secrets.compare_digest(digest, test_digest)
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logging.warning(f"verify_password caught safe exception: {e}")
        return False

# ──────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ──────────────────────────────────────────────
# OAuth2 scheme
# ──────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-form", auto_error=False)

# ──────────────────────────────────────────────
# User DB helpers & Seed Data
# ──────────────────────────────────────────────

USER_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users_db.json"
try:
    USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Seed users available even if filesystem is read-only or empty
DEFAULT_USERS: Dict[str, dict] = {
    "demo": {
        "password": hash_password("demo123"),
        "email": "demo@oncograph.ai",
        "full_name": "Dr. Demo Oncologist",
        "specialty": "Medical Oncology",
        "institution": "OncoGraph Demo Hospital",
        "role": "clinician",
        "plan": "enterprise",
        "avatar_color": "#6366f1",
        "created_at": "2026-08-13T00:00:00Z",
        "last_login": "",
        "onboarding_done": True,
        "usage_daily": {},
        "usage_monthly": {},
        "activity": [],
        "sessions": []
    },
    "dr_smith": {
        "password": hash_password("clinical2026"),
        "email": "smith@oncograph.ai",
        "full_name": "Dr. Sarah Smith",
        "specialty": "Radiation Oncology",
        "institution": "Johns Hopkins Medicine",
        "role": "clinician",
        "plan": "clinical",
        "avatar_color": "#10b981",
        "created_at": "2026-08-13T00:00:00Z",
        "last_login": "",
        "onboarding_done": True,
        "usage_daily": {},
        "usage_monthly": {},
        "activity": [],
        "sessions": []
    }
}

_USERS_CACHE: Dict[str, dict] = {}

def load_users() -> dict:
    global _USERS_CACHE
    users = {}
    if USER_DB_PATH.exists():
        try:
            with open(USER_DB_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    users = loaded
        except Exception as e:
            logging.warning(f"Could not read users_db.json: {e}")

    # Merge with memory cache
    for k, v in _USERS_CACHE.items():
        if k not in users:
            users[k] = v

    # Ensure defaults exist
    if (
        os.environ.get("APP_ENV", "").lower() != "production"
        or os.environ.get("ENABLE_DEMO_USERS", "true").lower() == "true"
    ):
        for uname, udata in DEFAULT_USERS.items():
            if uname not in users:
                users[uname] = udata.copy()

    _USERS_CACHE = users
    return users

def save_users(users: dict):
    global _USERS_CACHE
    _USERS_CACHE = users.copy()
    try:
        USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logging.warning(f"Could not write users_db.json (filesystem may be ephemeral/read-only): {e}")

# ──────────────────────────────────────────────
# Usage tracking
# ──────────────────────────────────────────────

def _today_key() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def _month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")

def record_api_call(username: str, endpoint: str):
    """Increment usage counters and append to activity log."""
    users = load_users()
    if username not in users:
        return
    u = users[username]
    today = _today_key()
    month = _month_key()

    # Daily usage
    usage_daily = u.setdefault("usage_daily", {})
    usage_daily[today] = usage_daily.get(today, 0) + 1

    # Monthly usage
    usage_monthly = u.setdefault("usage_monthly", {})
    usage_monthly[month] = usage_monthly.get(month, 0) + 1

    # Activity log — keep last 20
    activity = u.setdefault("activity", [])
    activity.append({
        "endpoint": endpoint,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ts": time.time(),
    })
    u["activity"] = activity[-20:]

    save_users(users)

def get_usage(username: str) -> dict:
    users = load_users()
    u = users.get(username, {})
    today = _today_key()
    month = _month_key()
    plan_key = u.get("plan", "free")
    plan = PLANS.get(plan_key, PLANS["free"])
    queries_today = u.get("usage_daily", {}).get(today, 0)
    queries_month = u.get("usage_monthly", {}).get(month, 0)
    return {
        "queries_today": queries_today,
        "queries_month": queries_month,
        "daily_quota": plan["daily_quota"],
        "monthly_quota": plan["monthly_quota"],
        "daily_remaining": max(0, plan["daily_quota"] - queries_today),
        "monthly_remaining": max(0, plan["monthly_quota"] - queries_month),
        "quota_reset_utc": (datetime.utcnow() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat() + "Z",
        "plan": plan_key,
    }

def check_rate_limit(username: str) -> int:
    """Returns remaining daily quota. Raises 429 if exceeded."""
    usage = get_usage(username)
    remaining = usage["daily_remaining"]
    plan_key = usage["plan"]
    plan = PLANS.get(plan_key, PLANS["free"])
    if usage["queries_today"] >= plan["daily_quota"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily query limit reached ({plan['daily_quota']}/day on {plan['name']} plan). Please upgrade or wait until midnight UTC.",
            headers={"X-RateLimit-Remaining": "0"},
        )
    return remaining

# ──────────────────────────────────────────────
# get_current_user dependency
# ──────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    users = load_users()
    if username not in users:
        raise HTTPException(status_code=401, detail="User account not found.")
    return users[username] | {"username": username}

async def get_optional_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Non-blocking version — returns None if not authenticated."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            return None
        users = load_users()
        if username not in users:
            return None
        return users[username] | {"username": username}
    except Exception:
        return None
