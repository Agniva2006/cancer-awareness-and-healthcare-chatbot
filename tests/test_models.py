"""Model + database tests (Phase 1)."""

import os
import tempfile
import uuid

# Use a throwaway SQLite DB for this test module.
_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdb.name}"

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Conversation,
    KnowledgeDocument,
    Message,
    Plan,
    Subscription,
    UsageEvent,
    User,
)

TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def _db():
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


def _uid() -> str:
    """Unique suffix so tests never collide regardless of run order."""
    return uuid.uuid4().hex[:10]


def test_user_crud_roundtrip():
    db = next(_db())
    email = f"t1-{_uid()}@example.com"
    u = User(email=email, password_hash="x", role="patient")
    db.add(u)
    db.commit()
    found = db.query(User).filter_by(email=email).one()
    assert found.id and found.created_at is not None


def test_duplicate_email_rejected():
    from sqlalchemy.exc import IntegrityError

    db = next(_db())
    email = f"dup-{_uid()}@example.com"
    db.add(User(email=email, password_hash="x"))
    db.commit()
    db.add(User(email=email, password_hash="y"))
    try:
        db.commit()
        assert False, "expected IntegrityError"
    except IntegrityError:
        db.rollback()


def test_conversation_message_relationship():
    db = next(_db())
    u = User(email=f"t2-{_uid()}@example.com", password_hash="x")
    db.add(u)
    db.commit()
    conv = Conversation(user_id=u.id, title="Test chat")
    db.add(conv)
    db.commit()
    db.add_all(
        [
            Message(
                conversation_id=conv.id, role="user", content="What is lung cancer?"
            ),
            Message(conversation_id=conv.id, role="assistant", content="It is..."),
        ]
    )
    db.commit()
    assert len(conv.messages) == 2


def test_knowledge_document_fields():
    db = next(_db())
    kd = KnowledgeDocument(
        title="EGFR mutations",
        content="EGFR mutations occur in NSCLC...",
        source="NCCN",
        category="biomarker",
        cancer_type="lung",
        external_key=f"test-egfr-{_uid()}",
    )
    db.add(kd)
    db.commit()
    assert kd.cancer_type == "lung"


def test_plan_and_subscription():
    db = next(_db())
    u = User(email=f"t3-{_uid()}@example.com", password_hash="x")
    plan = Plan(code=f"pro-{_uid()}", name="Pro", monthly_quota=1000, price_cents=900)
    db.add_all([u, plan])
    db.commit()
    sub = Subscription(user_id=u.id, plan_id=plan.id, status="active")
    db.add(sub)
    db.commit()
    assert sub.plan.code.startswith("pro-")


def test_usage_event_and_audit():
    db = next(_db())
    u = User(email=f"t4-{_uid()}@example.com", password_hash="x")
    db.add(u)
    db.commit()
    db.add(UsageEvent(user_id=u.id, endpoint="/ask", tokens_used=320))
    db.add(AuditLog(user_id=u.id, action="login", details={"ip": "1.2.3.4"}))
    db.commit()
    assert db.query(UsageEvent).filter_by(user_id=u.id).count() == 1
