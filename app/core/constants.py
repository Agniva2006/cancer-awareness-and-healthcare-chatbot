"""Shared constants and static text used across the application."""

MEDICAL_DISCLAIMER = (
    "For general information only. Consult a qualified healthcare professional "
    "for medical advice."
)

NO_MATCH_ANSWER = (
    "I couldn't find a matching answer in the cancer awareness information "
    "available. Please consult a qualified healthcare professional for personal "
    "medical advice."
)

LLM_FAILURE_SENTINEL = "I couldn't generate a response at the moment"

# Default surgical face for quick suggestions / docs
SUPPORTED_MODES = ("patient", "clinical")
