"""Pydantic schemas for the billing API."""

from typing import Optional

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    plan_code: str = Field(..., pattern="^(pro|clinic)$",
                           description="Paid plan to purchase (free needs no checkout)")


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionOut(BaseModel):
    plan_code: str
    plan_name: str
    status: str
    quota_limit: int
    quota_used: int
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


class WebhookAck(BaseModel):
    received: str
