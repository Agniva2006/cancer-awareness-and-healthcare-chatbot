"""Phase 3 billing tests — quota enforcement and webhook processing.

Stripe SDK is NOT installed in the test environment by design: that exercises
the "billing not configured" degradation path AND proves the quota/idempotency
machinery works without any external service.
"""

import os
import tempfile
import uuid

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdb.name}"

from datetime import timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import rate_limiter  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.database import get_db as real_get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Plan, Subscription, UsageEvent, User  # noqa: E402
from app.services import billing as billing_service  # noqa: E402
from app.services import quota as quota_service  # noqa: E402

Base.metadata.create_all(bind=engine)


def _override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[real_get_db] = _override_db
client = TestClient(app)


def setup_function(function):
    rate_limiter.reset()


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _mk_user(email: str | None = None) -> User:
    db = SessionLocal()
    email = email or f"bill-{_uid()}@example.com"
    user = User(email=email, password_hash=hash_password("Sup3rSecret99"),
                is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth(user: User) -> dict:
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def _seed_plans() -> None:
    db = SessionLocal()
    for code, quota, cents in (
        ("free", 20, 0),
        (f"pro-{_uid()}", 1000, 900),
        ("clinic", 5000, 4900),
    ):
        if not db.query(Plan).filter(Plan.code == code).first():
            db.add(Plan(code=code, name=code, monthly_quota=quota,
                        price_cents=cents))
    db.commit()
    db.close()


_seed_plans()


# ── Unit-level: quota service ────────────────────────────────────
def test_free_quota_default():
    user = _mk_user()
    db = SessionLocal()
    plan, limit = quota_service.get_effective_plan(db, user.id)
    assert plan is None
    assert limit == 20
    assert quota_service.check_quota(db, user.id) == (True, 0, 20)
    db.close()


def test_quota_counts_usage_and_blocks():
    user = _mk_user()
    db = SessionLocal()
    for _ in range(20):
        quota_service.record_usage(db, user.id)
    allowed, used, limit = quota_service.check_quota(db, user.id)
    assert (allowed, used, limit) == (False, 20, 20)
    db.close()


def test_paid_plan_raises_limit():
    user = _mk_user()
    db = SessionLocal()
    pro = db.query(Plan).filter(Plan.code.like("pro-%")).first()
    db.add(Subscription(user_id=user.id, plan_id=pro.id, status="active"))
    db.commit()
    plan, limit = quota_service.get_effective_plan(db, user.id)
    assert plan is not None and limit == pro.monthly_quota
    db.close()


# ── Checkout behavior ────────────────────────────────────────────
def test_checkout_works_when_configured_or_503_when_not():
    """With real test keys in .env checkout succeeds (200 + URL); without
    keys it degrades cleanly with 503. Either way no 500 crashes."""
    user = _mk_user()
    resp = client.post("/billing/checkout", json={"plan_code": "pro"},
                       headers=_auth(user))
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        assert resp.json()["checkout_url"].startswith("https://")


def test_webhook_rejects_bad_signature_with_400():
    resp = client.post(
        "/billing/webhooks/stripe",
        content=b"not-a-real-stripe-event",
        headers={"stripe-signature": "t=1,v1=forged"},
    )
    # Without SDK configured -> 503; if SDK present but signature bad -> 400.
    assert resp.status_code in (400, 503)


def test_webhook_requires_authentication_is_false():
    """Webhook endpoint must NOT require a Bearer token (roadmap §3.5)."""
    resp = client.post("/billing/webhooks/stripe", content=b"{}")
    assert resp.status_code != 401


def test_subscription_endpoint_reports_free_defaults():
    user = _mk_user()
    resp = client.get("/billing/subscription", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan_code"] == "free"
    assert body["quota_limit"] == 20
    assert body["quota_used"] == 0


def test_me_includes_plan_and_quota():
    user = _mk_user()
    resp = client.get("/auth/me", headers=_auth(user))
    body = resp.json()
    assert body["plan_code"] == "free"
    assert body["quota_limit"] == 20


# ── Webhook idempotency machinery (no SDK needed) ────────────────
def test_mark_processed_is_idempotent():
    db = SessionLocal()
    event_id = f"evt_test_{_uid()}"
    first = billing_service._mark_processed(db, event_id, "test.event")
    second = billing_service._mark_processed(db, event_id, "test.event")
    assert first is False   # first delivery -> proceed
    assert second is True   # duplicate -> ignore
    db.close()


# ── End-to-end: /ask quota enforcement via API ───────────────────
def test_ask_blocks_when_quota_exhausted():
    user = _mk_user()
    db = SessionLocal()
    for _ in range(20):
        db.add(UsageEvent(user_id=user.id, endpoint="/ask"))
    db.commit()
    db.close()
    resp = client.post(
        "/ask", json={"query": "what is lung cancer?", "mode": "patient"},
        headers=_auth(user),
    )
    assert resp.status_code == 429
    assert "quota" in resp.json()["detail"].lower()
