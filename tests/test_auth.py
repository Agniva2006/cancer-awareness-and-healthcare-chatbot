"""Phase 2 auth tests: register/login/refresh/logout cycle, token security,
RBAC gating, rate limiting and audit logging.

Uses an isolated SQLite DB via dependency overrides so the real app wiring
(including get_current_user) is exercised end-to-end.
"""

import os
import tempfile
import uuid

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdb.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.database import get_db as real_get_db  # noqa: E402
from app.core.deps import get_current_user, require_role  # noqa: F401, E402
from app.core.security import (  # noqa: E402
    TokenExpiredError,
    create_access_token,
    decode_access_token,
    hash_password,
)
from app.core.config import rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AuditLog, User  # noqa: E402

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


PASSWORD = "Sup3rSecret99"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _register(email: str) -> dict:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(email: str) -> dict:
    resp = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _mk_user(role: str = "patient"):
    db = SessionLocal()
    email = f"{role}-{_uid()}@example.com"
    db.add(
        User(
            email=email,
            password_hash=hash_password(PASSWORD),
            role=role,
            is_verified=True,
        )
    )
    db.commit()
    db.close()
    return email


# ── Unit-level: hashing & JWT ────────────────────────────────────
def test_password_hash_roundtrip():
    from app.core.security import verify_password

    h = hash_password(PASSWORD)
    assert h != PASSWORD
    assert verify_password(PASSWORD, h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip_and_expiry():
    token = create_access_token("user-123", "patient", expires_minutes=15)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "patient"
    from app.core.security import _jwt_secret  # noqa: F401

    expired = create_access_token("u", "patient", expires_minutes=-1)
    try:
        decode_access_token(expired)
        assert False, "expected expiry error"
    except TokenExpiredError:
        pass


def test_weak_password_rejected_by_policy():
    resp = client.post(
        "/auth/register",
        json={"email": f"weak-{_uid()}@example.com", "password": "short1A", "full_name": ""},
    )
    assert resp.status_code == 422


# ── Endpoint flow ────────────────────────────────────────────────
def test_register_login_me_cycle():
    email = f"cyc-{_uid()}@example.com"
    _register(email)
    tokens = _login(email)
    assert tokens["token_type"] == "bearer"
    assert len(tokens["refresh_token"]) >= 32

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "patient"


def test_duplicate_register_conflicts():
    email = f"dup-{_uid()}@example.com"
    _register(email)
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": ""},
    )
    assert resp.status_code == 409


def test_login_wrong_password_identical_error():
    email = _mk_user()
    resp_ok = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    resp_bad_pw = client.post(
        "/auth/login", json={"email": email, "password": "Nope123456x"}
    )
    resp_bad_email = client.post(
        "/auth/login", json={"email": f"ghost-{_uid()}@x.com", "password": PASSWORD}
    )
    assert resp_ok.status_code == 200
    assert resp_bad_pw.status_code == 401
    assert resp_bad_email.status_code == 401
    # Enumeration defense: identical detail for both failure modes.
    assert resp_bad_pw.json()["detail"] == resp_bad_email.json()["detail"]


def test_refresh_rotation_and_replay_rejection():
    email = _mk_user()
    tokens = _login(email)
    r1 = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r1.status_code == 200
    new_tokens = r1.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    # Replay of the OLD token must now fail (rotation revoked it).
    r2 = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401
    # And the NEW token still works.
    r3 = client.post("/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert r3.status_code == 200


def test_logout_revokes_refresh_token():
    email = _mk_user()
    tokens = _login(email)
    out = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 200
    replay = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401


def test_me_requires_token():
    assert client.get("/auth/me").status_code == 401
    assert client.get(
        "/auth/me", headers={"Authorization": "Bearer garbage.token.here"}
    ).status_code == 401


def test_ask_requires_auth():
    resp = client.post("/ask", json={"query": "what is lung cancer?"})
    assert resp.status_code == 401


def test_login_rate_limited():
    email = f"flood-{_uid()}@example.com"
    got_401 = 0
    for _ in range(20):
        resp = client.post(
            "/auth/login", json={"email": email, "password": "WrongPass123"}
        )
        if resp.status_code == 401:
            got_401 += 1
        elif resp.status_code == 429:
            break
    else:
        assert False, "never rate-limited after 20 attempts"
    assert got_401 < 20


def test_login_success_audited():
    db = SessionLocal()
    before = db.query(AuditLog).filter_by(action="login").count()
    db.close()
    _login(_mk_user())
    db = SessionLocal()
    after = db.query(AuditLog).filter_by(action="login").count()
    db.close()
    assert after > before


def test_forgot_password_no_enumeration():
    real_email = _mk_user()
    r1 = client.post("/auth/forgot-password", json={"email": real_email})
    r2 = client.post(
        "/auth/forgot-password", json={"email": f"ghost-{_uid()}@x.com"}
    )
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()


# ── RBAC ─────────────────────────────────────────────────────────
def test_require_role_factory_gates():
    from fastapi import HTTPException

    patient = User(email="p@x.com", password_hash="x", role="patient")
    admin = User(email="a@x.com", password_hash="x", role="admin")
    checker = require_role("admin")
    # Non-dependent call: inject the user directly.
    try:
        checker(admin)
    except HTTPException:
        assert False, "admin should pass"
    try:
        checker(patient)
        assert False, "patient should be rejected"
    except HTTPException as exc:
        assert exc.status_code == 403
