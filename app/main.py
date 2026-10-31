"""Cancer Awareness Chatbot — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging()

DESCRIPTION = """
Cancer awareness question-answering API.

Pipeline: safety check → triage classification → TF-IDF retrieval → LLM generation.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up singletons (RAG index, LLM client) at startup."""
    from app.services import rag  # noqa: F401  (builds TF-IDF index on import)
    from app.services.model import get_client

    try:
        get_client()
    except ValueError as exc:
        # Non-fatal: /ask will report a graceful failure if the key is missing.
        import logging

        logging.getLogger(__name__).warning("LLM client not ready at startup: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(api_router)

    # Serve the SPA frontend (best-effort; works when run from the repo root).
    try:
        app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    except Exception:
        pass

    return app


app = create_app()
