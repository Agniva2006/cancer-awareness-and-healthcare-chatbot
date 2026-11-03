"""System health endpoints."""

import time

from fastapi import APIRouter

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


@router.get("/health/ready")
def ready():
    """Readiness probe — checks DB reachability."""
    try:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            db.exec_driver_sql("SELECT 1")
        finally:
            db.close()
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=f"not ready: {exc}")
