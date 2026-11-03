"""Billing endpoints: checkout, portal, subscription status, Stripe webhook.

The webhook endpoint is intentionally UNAUTHENTICATED — its authenticity comes
from the verified Stripe signature, not from a user session (roadmap §3.4).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    SubscriptionOut,
    WebhookAck,
)
from app.services import billing as billing_service
from app.services import quota as quota_service
from app.services.quota import FREE_PLAN_CODE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session; the client redirects to `checkout_url`."""
    try:
        url = billing_service.create_checkout_session(db, user.id, user.email,
                                                      body.plan_code)
    except billing_service.BillingNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Billing not configured: {exc}")
    except billing_service.UnknownPlan:
        raise HTTPException(status_code=404, detail="Unknown plan")
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def portal(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stripe customer portal for card management / cancellation."""
    try:
        url = billing_service.create_portal_session(db, user.id)
    except billing_service.BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=f"Billing not configured: {exc}")
    except billing_service.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PortalResponse(portal_url=url)


@router.get("/subscription", response_model=SubscriptionOut)
def subscription(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Current plan and this period's usage — powers the frontend quota bar."""
    plan, limit = quota_service.get_effective_plan(db, user.id)
    used = quota_service.quota_used_this_period(db, user.id)
    sub = quota_service.get_active_subscription(db, user.id)
    return SubscriptionOut(
        plan_code=plan.code if plan else FREE_PLAN_CODE,
        plan_name=plan.name if plan else "Free",
        status=sub.status if sub else "active",
        quota_limit=limit,
        quota_used=used,
        current_period_end=(
            sub.current_period_end.isoformat() if sub and sub.current_period_end
            else None
        ),
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
    )


@router.post("/webhooks/stripe", response_model=WebhookAck)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Stripe events. Signature-verified; idempotent by event ID."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = billing_service.verify_and_parse_webhook(payload, signature)
    except billing_service.BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=f"Billing not configured: {exc}")
    except billing_service.WebhookError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    verdict = billing_service.handle_webhook(db, event)
    logger.info("Stripe webhook %s -> %s", event["type"], verdict)
    return WebhookAck(received=verdict)
