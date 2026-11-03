"""Quota service — server-side usage enforcement (roadmap §3.6).

Golden rule: quotas are counted from the usage_events table, never from
anything the client reports. Only SUCCESSFUL answers count.
"""

from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Plan, Subscription, UsageEvent

FREE_PLAN_CODE = "free"
DEFAULT_QUOTA = settings.FREE_PLAN_QUOTA


def get_active_subscription(db: Session, user_id: str) -> Subscription | None:
    """The user's active (or trialing/past_due-but-live) subscription, if any."""
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing", "past_due"]),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )


def get_effective_plan(db: Session, user_id: str) -> Tuple[Plan | None, int]:
    """Return (plan, quota_limit). Users without a paid plan fall to Free."""
    sub = get_active_subscription(db, user_id)
    if sub is not None and sub.plan is not None and sub.plan.is_active:
        return sub.plan, sub.plan.monthly_quota
    return None, DEFAULT_QUOTA


def quota_used_this_period(db: Session, user_id: str) -> int:
    """Count successful /ask calls in the CURRENT billing period.

    Billing period comes from the subscription; users without one are counted
    per calendar month (fair free-tier default).
    """
    sub = get_active_subscription(db, user_id)
    now = datetime.now(timezone.utc)
    if sub is not None and sub.current_period_start is not None:
        period_start = sub.current_period_start
    else:
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)

    count = (
        db.query(func.count(UsageEvent.id))
        .filter(
            UsageEvent.user_id == user_id,
            UsageEvent.endpoint == "/ask",
            UsageEvent.created_at >= period_start,
        )
        .scalar()
    )
    return int(count or 0)


def check_quota(db: Session, user_id: str) -> Tuple[bool, int, int]:
    """(allowed, used, limit) — call BEFORE answering."""
    _, limit = get_effective_plan(db, user_id)
    used = quota_used_this_period(db, user_id)
    return used < limit, used, limit


def record_usage(db: Session, user_id: str, tokens_used: int = 0,
                 cost_cents: int = 0) -> None:
    """Log a successful answer. Call AFTER the answer is produced."""
    db.add(UsageEvent(user_id=user_id, endpoint="/ask",
                      tokens_used=tokens_used, cost_cents=cost_cents))
    db.commit()
