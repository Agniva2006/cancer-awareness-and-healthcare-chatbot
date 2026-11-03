"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, chat, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(chat.router, tags=["chatbot"])
