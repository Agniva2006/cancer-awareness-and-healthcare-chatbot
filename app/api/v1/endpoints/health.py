"""System health endpoints.

/health       — liveness (is the process up?)
/health/ready — readiness: DB + Redis + LLM provider reachability (Phase 5).
"""

import time

from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter()


@router.get("/")
def home():
    """Service landing payload."""
    return {
        "message": settings.APP_NAME,
        "modules": ["chatbot"],
        "version": settings.APP_VERSION,
    }


@router.get("/health")
def health():
    """Liveness probe."""
    return {"status": "healthy", "timestamp": time.time()}


def _check_db() -> str:
    from sqlalchemy import text

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
    return "ok"


def _check_redis() -> str:
    import redis

    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    return "ok" if client.ping() else "no response"


def _check_llm() -> str:
    # Config-level check: a key must be present for /ask to work. We do not
    # burn tokens/latency on a live completion in a readiness probe.
    if not settings.GROQ_API_KEY:
        return "no api key"
    return "configured"


@router.get("/health/ready")
def ready():
    """Readiness probe — DB (required) + Redis + LLM config (reported)."""
    checks: dict[str, str] = {}
    try:
        checks["database"] = _check_db()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"not ready: database: {exc}")

    for name, fn in (("redis", _check_redis), ("llm", _check_llm)):
        try:
            checks[name] = fn()
        except Exception as exc:  # degraded, but the API can still serve /health
            checks[name] = f"unavailable: {exc}"

    degraded = any(v.startswith(("unavailable", "no ")) for v in checks.values())
    return {"status": "degraded" if degraded else "ready", **checks}
