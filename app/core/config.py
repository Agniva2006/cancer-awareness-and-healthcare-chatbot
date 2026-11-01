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


settings = Settings()
