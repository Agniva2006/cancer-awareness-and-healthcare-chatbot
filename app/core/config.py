"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above app/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


class Settings:
    """Central, typed access point for all runtime configuration."""

    # ── App ────────────────────────────────────────────────
    APP_NAME: str = "Cancer Awareness Chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cancer_chatbot_dev.db")
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    # ── LLM provider ──────────────────────────────────────
    GROQ_API_KEY: str = (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'")
    # Models tried in order; first success wins.
    LLM_FALLBACK_MODELS: list = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-safeguard-20b",
        "qwen/qwen3.8-27b",
    ]
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # ── Retrieval (RAG) ───────────────────────────────────────
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "7"))
    RAG_SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.04"))
    RAG_FINAL_TOP_N: int = int(os.getenv("RAG_FINAL_TOP_N", "3"))
    RAG_MAX_FEATURES: int = int(os.getenv("RAG_MAX_FEATURES", "10000"))
    # Hybrid retrieval: weight of dense/semantic score vs sparse keyword score.
    # RRF (Reciprocal Rank Fusion) merges both ranked lists.
    RAG_RRF_K: int = int(os.getenv("RAG_RRF_K", "60"))
    # Below this fused score the bot honestly says it doesn't know.
    # RRF scores cluster ~0.02-0.05 for 3 ranked lists with k=60; a good match
    # (appears high in all lists) lands above ~0.038.
    RAG_GROUNDING_THRESHOLD: float = float(
        os.getenv("RAG_GROUNDING_THRESHOLD", "0.038")
    )

    # ── Auth / JWT ────────────────────────────────────────
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        # DEV-ONLY fallback so a fresh checkout boots. Override in production.
        "dev-insecure-jwt-secret-change-me-0123456789abcdef",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # ── Rate limiting (Redis backend, in-memory fallback) ──
    AUTH_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5"))
    AUTH_RATE_LIMIT_WINDOW_MINUTES: int = int(
        os.getenv("AUTH_RATE_LIMIT_WINDOW_MINUTES", "15")
    )
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # ── Observability (Phase 5) ───────────────────────────
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "dev")  # dev | json
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")  # local|staging|production

    # ── Email ─────────────────────────────────────────────
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "console")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@cancerchat.local")
    EMAIL_TOKEN_EXPIRE_HOURS: int = int(os.getenv("EMAIL_TOKEN_EXPIRE_HOURS", "24"))
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

    # ── Billing / Payments (Phase 3) ─────────────────────
    # Stripe test keys by default; swap to live keys only in production env.
    STRIPE_SECRET_KEY: str = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    STRIPE_WEBHOOK_SECRET: str = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    # plan_code -> Stripe Price ID (price_...). Server-side only: the frontend
    # NEVER sets prices (golden rule #2).
    STRIPE_PRICE_PRO: str = (os.getenv("STRIPE_PRICE_PRO") or "").strip()
    STRIPE_PRICE_CLINIC: str = (os.getenv("STRIPE_PRICE_CLINIC") or "").strip()
    BILLING_PROVIDER: str = os.getenv("BILLING_PROVIDER", "stripe")
    FREE_PLAN_QUOTA: int = int(os.getenv("FREE_PLAN_QUOTA", "20"))

    # ── HTTP / CORS ───────────────────────────────────────
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5501,http://127.0.0.1:5501,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")

    # ── Paths ─────────────────────────────────────────────
    DATA_DIR: Path = BASE_DIR / "data"
    KNOWLEDGE_FILES: list = [
        DATA_DIR / "lung_cancer_kb.json",
        DATA_DIR / "clinical_oncology_kb.json",
        DATA_DIR / "cancer_data.json",
    ]


class _InMemoryRateLimiter:
    """Fixed-window per-key rate limiter (per process, no external store).

    Good enough for single-instance dev/small deploys. Phase 5 replaces the
    storage with Redis counters via the same interface.
    """

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, max_attempts: int, window_minutes: int) -> bool:
        """Return True if the action is allowed, False if rate-limited."""
        import time

        now = time.monotonic()
        cutoff = now - window_minutes * 60
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= max_attempts:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def reset(self) -> None:
        """Clear all counters (used by tests and by Redis-swap plumbing)."""
        self._hits.clear()


# Phase 5: resilient limiter — Redis counters with in-memory fallback.
# Exposes .reset() so tests clear state the same way as before.
from app.core.rate_limit import get_rate_limiter  # noqa: E402

rate_limiter = get_rate_limiter()

settings = Settings()
