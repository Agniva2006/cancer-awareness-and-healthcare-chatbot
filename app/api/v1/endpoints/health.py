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
