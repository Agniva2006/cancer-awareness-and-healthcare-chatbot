"""Billing service — Stripe checkout, portal and webhook processing.

Design (roadmap §3.2 golden rules, enforced in code):
1. Card data NEVER touches this server — Stripe Checkout hosts the payment page.
2. Prices come from server config/env only (`STRIPE_PRICE_*`), never the client.
3. Webhooks are the ONLY path that activates a subscription, and only after
   signature verification. Duplicate deliveries are absorbed by the
   billing_events idempotency table.

Stripe is imported lazily so the app boots (and tests run) without the SDK or
keys configured — endpoints degrade with a clear 503 instead of crashing.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import BillingEvent, Plan, Subscription
from app.services.quota import FREE_PLAN_CODE

logger = logging.getLogger(__name__)


class BillingError(Exception):
    """Base class for billing failures endpoints can map to HTTP."""


class BillingNotConfigured(BillingError):
    """Stripe keys/prices missing — feature is cleanly disabled."""


class UnknownPlan(BillingError):
    pass


class WebhookError(BillingError):
    pass


PLAN_TO_PRICE = {
    "pro": lambda: settings.STRIPE_PRICE_PRO,
    "clinic": lambda: settings.STRIPE_PRICE_CLINIC,
}


def _stripe():
    """Lazy Stripe SDK import; raises a typed error when not configured."""
    try:
        import stripe  # noqa: PLC0415 — deliberate lazy import
    except ImportError as exc:
        raise BillingNotConfigured("stripe SDK not installed") from exc
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.startswith(
        ("sk_test_", "sk_live_", "rk_")
    ):
        raise BillingNotConfigured("STRIPE_SECRET_KEY not set")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def billing_configured() -> bool:
    """True when checkout/webhooks can actually run in this environment."""
    try:
        _stripe()
    except BillingNotConfigured:
        return False
    return any(getter() for getter in PLAN_TO_PRICE.values())


def get_plan(db: Session, code: str) -> Plan:
    plan = db.query(Plan).filter(Plan.code == code, Plan.is_active.is_(True)).first()
    if plan is None:
        raise UnknownPlan(code)
    return plan


def create_checkout_session(db: Session, user_id: str, email: str,
                            plan_code: str) -> str:
    """Create a Stripe Checkout session and return its hosted URL.

    Prices are resolved SERVER-side from env; the client only names a plan.
    """
    stripe = _stripe()
    if plan_code == FREE_PLAN_CODE:
        raise UnknownPlan("free plan does not require checkout")
    price_getter = PLAN_TO_PRICE.get(plan_code)
    if price_getter is None:
        raise UnknownPlan(plan_code)
    price_id = price_getter()
    if not price_id:
        raise BillingNotConfigured(f"No Stripe price configured for '{plan_code}'")

    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).first()
    )
    customer_id = subscription.provider_customer_id if subscription else None
    if customer_id is None:
        customer = stripe.Customer.create(email=email, metadata={"user_id": user_id})
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.APP_BASE_URL}/billing/success",
        cancel_url=f"{settings.APP_BASE_URL}/billing/pricing",
        metadata={"user_id": user_id, "plan_code": plan_code},
        subscription_data={"metadata": {"user_id": user_id, "plan_code": plan_code}},
    )
    return session.url


def create_portal_session(db: Session, user_id: str) -> str:
    """Stripe customer portal: users manage cards/cancellation without our UI."""
    stripe = _stripe()
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).first()
    )
    customer_id = subscription.provider_customer_id if subscription else None
    if not customer_id:
        raise BillingError("No billing profile yet — subscribe to a plan first")
    portal = stripe.billing_portal.Session.create(customer=customer_id)
    return portal.url


# ── Webhook processing ───────────────────────────────────────────
def verify_and_parse_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
    """Verify the Stripe signature; raise WebhookError on forgery/failure."""
    stripe = _stripe()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise BillingNotConfigured("STRIPE_WEBHOOK_SECRET not set")
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as exc:  # stripe.SignatureVerificationError / ValueError
        logger.warning("Webhook signature verification failed: %s", exc)
        raise WebhookError("Invalid webhook signature") from exc
    return {"id": event["id"], "type": event["type"], "data": event["data"]["object"]}


def _mark_processed(db: Session, event_id: str, event_type: str) -> bool:
    """Idempotency gate: True if this event was ALREADY processed.

    Insert-first: the unique constraint on provider_event_id is the lock.
    """
    import sqlalchemy.exc  # noqa: PLC0415

    db.add(BillingEvent(provider=settings.BILLING_PROVIDER,
                        provider_event_id=event_id, event_type=event_type))
    try:
        db.commit()
        return False  # first delivery — proceed with side effects
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        return True  # duplicate delivery — skip


def _upsert_subscription(db: Session, user_id: str, plan_code: str | None,
                         sub_obj: Dict[str, Any], customer_id: str | None) -> None:
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).first()
    )
    if subscription is None:
        plan = (
            db.query(Plan)
            .filter(Plan.code.in_([plan_code or FREE_PLAN_CODE, FREE_PLAN_CODE]))
            .order_by(Plan.price_cents.desc())
            .first()
        )
        if plan is None:
            logger.error("No plan row for plan_code=%r; cannot activate", plan_code)
            return
        subscription = Subscription(user_id=user_id, plan_id=plan.id)
        db.add(subscription)

    if plan_code:
        plan = db.query(Plan).filter(Plan.code == plan_code).first()
        if plan is not None:
            subscription.plan_id = plan.id

    period_start, period_end = _period_from_stripe(sub_obj)
    subscription.status = sub_obj.get("status") or subscription.status
    if period_start:
        subscription.current_period_start = period_start
    if period_end:
        subscription.current_period_end = period_end
    if customer_id:
        subscription.provider_customer_id = customer_id
    subscription.provider = settings.BILLING_PROVIDER
    subscription.provider_subscription_id = sub_obj.get("id")
    subscription.cancel_at_period_end = bool(sub_obj.get("cancel_at_period_end"))
    db.commit()


def _period_from_stripe(sub_obj: Dict[str, Any]):
    start = sub_obj.get("current_period_start")
    end = sub_obj.get("current_period_end")

    def _ts(value):
        if value is None:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)

    return _ts(start), _ts(end)


def handle_webhook(db: Session, event: Dict[str, Any]) -> str:
    """Apply a verified webhook event. Returns a short processing verdict.

    Events handled (roadmap §3.4):
      checkout.session.completed     -> activate subscription
      customer.subscription.updated  -> plan change / renewal / cancel_at_end
      customer.subscription.deleted  -> end subscription
      invoice.payment_failed         -> mark past_due (dunning starts)
      invoice.paid                   -> renewal confirmed
    """
    event_id, event_type, obj = event["id"], event["type"], event["data"]

    if _mark_processed(db, event_id, event_type):
        logger.info("Duplicate webhook %s (%s) ignored", event_id, event_type)
        return "duplicate_ignored"

    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_code = metadata.get("plan_code")

    if event_type == "checkout.session.completed":
        if not user_id:
            logger.error("checkout.session.completed without user metadata")
            return "missing_metadata"
        # Retrieve the subscription object for authoritative period data.
        sub_obj = obj.get("subscription_details") or obj.get("subscription") or {}
        if isinstance(sub_obj, str):
            sub_obj = {"id": sub_obj}
        _upsert_subscription(db, user_id, plan_code, sub_obj,
                             obj.get("customer"))
        return "subscription_activated"

    if event_type in ("customer.subscription.updated",
                      "customer.subscription.deleted"):
        if not user_id:
            user_id = _user_from_local_subscription(db, obj.get("id"))
        if not user_id:
            return "unknown_subscription"
        if event_type == "customer.subscription.deleted":
            sub_obj = dict(obj)
            sub_obj["status"] = "canceled"
        else:
            sub_obj = obj
        _upsert_subscription(db, user_id, plan_code, sub_obj, obj.get("customer"))
        return ("subscription_ended"
                if event_type.endswith("deleted") else "subscription_updated")

    if event_type == "invoice.payment_failed":
        if user_id:
            _set_status(db, user_id, "past_due")
            return "marked_past_due"
        return "missing_metadata"

    if event_type == "invoice.paid":
        return "renewal_recorded"

    logger.info("Unhandled webhook type: %s", event_type)
    return "unhandled"


def _user_from_local_subscription(db: Session, provider_sub_id: str | None) -> Optional[str]:
    if not provider_sub_id:
        return None
    sub = (
        db.query(Subscription)
        .filter(Subscription.provider_subscription_id == provider_sub_id)
        .first()
    )
    return sub.user_id if sub else None


def _set_status(db: Session, user_id: str, status: str) -> None:
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).first()
    )
    if subscription is not None:
        subscription.status = status
        db.commit()
