"""Smoke tests for system endpoints."""

import os
import tempfile
import uuid

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdb.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.database import get_db as real_get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

from app.core.database import Base  # noqa: E402

Base.metadata.create_all(bind=engine)


def _override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[real_get_db] = _override_db
client = TestClient(app)

PASSWORD = "Sup3rSecret99"


def _auth_headers() -> dict:
    """Create a fresh user and return valid Bearer headers."""
    from app.core.security import create_access_token

    db = SessionLocal()
    email = f"ask-{uuid.uuid4().hex[:8]}@example.com"
    db.add(User(email=email, password_hash=hash_password(PASSWORD), is_verified=True))
    db.commit()
    user = db.query(User).filter_by(email=email).one()
    token = create_access_token(user.id, user.role)
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_home():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_ask_validation_rejects_empty_query():
    resp = client.post(
        "/ask", json={"query": "", "mode": "patient"}, headers=_auth_headers()
    )
    assert resp.status_code == 422


def test_ask_validation_rejects_bad_mode():
    resp = client.post(
        "/ask", json={"query": "hi", "mode": "hacker"}, headers=_auth_headers()
    )
    assert resp.status_code == 422


def test_ask_risky_query_blocked():
    resp = client.post(
        "/ask",
        json={"query": "diagnose me with cancer", "mode": "patient"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "cannot provide" in body["answer"].lower()
    assert body["sources"] == []
