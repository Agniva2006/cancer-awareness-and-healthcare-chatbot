"""Unit tests for the safety guardrail."""

from app.services.safety import is_risky, safe_response


def test_risky_phrases_blocked():
    for q in ["diagnose me", "what dosage should I take", "prescribe me something"]:
        assert is_risky(q) is True, q


def test_educational_queries_allowed():
    for q in ["What is chemotherapy?", "What are the symptoms of lung cancer?"]:
        assert is_risky(q) is False, q


def test_safe_response_mentions_professional():
    assert "oncologist" in safe_response().lower()
