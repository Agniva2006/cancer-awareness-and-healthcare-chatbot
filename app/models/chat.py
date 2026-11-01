"""Conversation and message models — chat history persisted in DB."""

from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid

# JSONB is Postgres-native; fall back to generic JSON on SQLite (tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")

    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", order_by="Message.created_at"
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Titles + scores of the chunks the LLM used (provenance for auditing)
    retrieved_context: Mapped[Optional[list]] = mapped_column(
        JSONVariant, nullable=True
    )
    triage_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
