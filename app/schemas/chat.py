"""Pydantic models for the chat API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Inbound question from the frontend."""

    query: str = Field(..., min_length=1, max_length=1000, description="User question")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Recent turns as {role, content} for conversational context"
    )
    mode: Optional[str] = Field(
        "patient",
        pattern="^(patient|clinical)$",
        description="Response tone: patient-friendly or clinical",
    )


class TriageInfo(BaseModel):
    """Triage classification attached to every answer."""

    level: str
    title: str
    action: str
    reason: str


class AskResponse(BaseModel):
    """Outbound chatbot answer."""

    query: str
    answer: str
    sources: List[str] = []
    confidence: float = 0.0
    latency: float = 0.0
    triage: TriageInfo
    disclaimer: str
