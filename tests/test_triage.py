"""Unit tests for triage classification."""

from app.services.triage import classify_triage


def test_red_flag():
    result = classify_triage("I have fever after chemo, what do I do?")
    assert result["level"] == "RED"


def test_yellow_flag():
    result = classify_triage("I have severe diarrhea after treatment")
    assert result["level"] == "YELLOW"


def test_green_default():
    result = classify_triage("What is cancer staging?")
    assert result["level"] == "GREEN"
