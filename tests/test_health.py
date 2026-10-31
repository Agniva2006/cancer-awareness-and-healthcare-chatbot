"""Smoke tests for system endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_ask_validation_rejects_empty_query():
    resp = client.post("/ask", json={"query": "", "mode": "patient"})
    assert resp.status_code == 422


def test_ask_validation_rejects_bad_mode():
    resp = client.post("/ask", json={"query": "hi", "mode": "hacker"})
    assert resp.status_code == 422


def test_ask_risky_query_blocked():
    resp = client.post(
        "/ask", json={"query": "diagnose me with cancer", "mode": "patient"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "cannot provide" in body["answer"].lower()
    assert body["sources"] == []
