"""Groq LLM service with a multi-model fallback chain."""

import logging
import threading

from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a safe, clear, and reliable cancer information assistant. "
        "Answer using the provided context only. Avoid hallucination. "
        "Keep answers structured and easy to understand."
    ),
}

_client: Groq | None = None
_client_lock = threading.Lock()


def get_client() -> Groq:
    """Thread-safe lazy initialization of the Groq client."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError(
                    "GROQ_API_KEY not found or empty. Check your .env file."
                )
            _client = Groq(
                api_key=settings.GROQ_API_KEY, timeout=settings.LLM_TIMEOUT_SECONDS
            )
    return _client


def generate(prompt: str) -> str:
    """Generate a response using the first available model in the fallback chain."""
    try:
        client = get_client()
    except ValueError as exc:
        logger.error("LLM client unavailable: %s", exc)
        return settings_failures_response()

    for idx, model_name in enumerate(settings.LLM_FALLBACK_MODELS):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[SYSTEM_MESSAGE, {"role": "user", "content": prompt}],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            content = completion.choices[0].message.content
            if content:
                return content.strip()
        except Exception as exc:
            logger.warning("Model attempt %d (%s) failed: %s", idx + 1, model_name, exc)
            continue

    logger.error("All model fallback attempts failed.")
    return settings_failures_response()


def settings_failures_response() -> str:
    """Sentinel answer returned when no LLM could produce a response."""
    return "I couldn't generate a response at the moment. Please try again."
