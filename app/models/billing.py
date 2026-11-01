"""Billing models: plans, subscriptions, orders, usage events."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid, utcnow

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(
        Integer, default=0
    )  # integer cents, NEVER float
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    features: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    provider: Mapped[str] = mapped_column(
        String(20), default="none"
    )  # none|stripe|razorpay
    provider_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    plan: Mapped[Plan] = relationship(back_populates="subscriptions")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("plans.id"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
