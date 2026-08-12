"""
app/auth.py — OncoGraph AI Authentication & Authorization
JWT-based auth with bcrypt password hashing and per-plan rate limiting.
"""

import os
import time
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

# SECRET_KEY priority:
#  1. ONCOGRAPH_SECRET_KEY environment variable  (set this on Render for stable tokens)
#  2. Persistent file on disk (local dev)
#  3. Auto-generated random (fallback — tokens won't survive restarts)
_SECRET_ENV = os.environ.get("ONCOGRAPH_SECRET_KEY", "").strip()
_SECRET_FILE = Path(__file__).resolve().parent.parent / "data" / ".jwt_secret"
_SECRET_FILE.parent.mkdir(exist_ok=True)

if _SECRET_ENV:
    SECRET_KEY = _SECRET_ENV
elif _SECRET_FILE.exists():
    SECRET_KEY = _SECRET_FILE.read_text().strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    try:
        _SECRET_FILE.write_text(SECRET_KEY)
    except Exception:
        pass  # read-only filesystem (some Render tiers)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days (remember-me style)

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
# Password hashing
# ──────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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
# User DB helpers
# ──────────────────────────────────────────────

USER_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users_db.json"
USER_DB_PATH.parent.mkdir(exist_ok=True)

def load_users() -> dict:
    try:
        with open(USER_DB_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users: dict):
    with open(USER_DB_PATH, "w") as f:
        json.dump(users, f, indent=2)

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
