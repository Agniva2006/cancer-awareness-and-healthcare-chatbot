"""Chat question-answering endpoint."""

import logging
import time

from fastapi import APIRouter

from app.core.config import settings
from app.core.constants import (
    LLM_FAILURE_SENTINEL,
    MEDICAL_DISCLAIMER,
    NO_MATCH_ANSWER,
)
from app.schemas.chat import AskRequest, AskResponse
from app.services.model import generate
from app.services.prompts import build_prompt
from app.services.rag import retrieve
from app.services.safety import is_risky, safe_response
from app.services.triage import classify_triage
from app.utils.text import clean_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer a cancer-awareness question with RAG + LLM, guarded by safety and triage."""
    started = time.perf_counter()
    query = clean_query(request.query)

    triage = classify_triage(query)

    if is_risky(query):
        logger.info("Risky query blocked: %r", query[:80])
        return AskResponse(
            query=query,
            answer=safe_response(),
            sources=[],
            confidence=0.0,
            latency=round(time.perf_counter() - started, 3),
            triage=triage,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    contexts = retrieve(
        query, k=settings.RAG_TOP_K, threshold=settings.RAG_SCORE_THRESHOLD
    )
    if contexts:
        contexts = sorted(
            contexts, key=lambda item: item.get("score", 0), reverse=True
        )[: settings.RAG_FINAL_TOP_N]
        answer = generate(
            build_prompt(
                query, contexts, request.chat_history, mode=request.mode or "patient"
            )
        ).strip()
        # Fall back to raw context snippets if the LLM produced nothing usable.
        if not answer or LLM_FAILURE_SENTINEL in answer:
            answer = "\n\n".join(
                f"**{item.get('title', 'Cancer information')}**\n{item.get('content', '')}"
                for item in contexts[:2]
            )
    else:
        answer = NO_MATCH_ANSWER

    return AskResponse(
        query=query,
        answer=answer,
        sources=list(dict.fromkeys(item.get("title", "") for item in contexts)),
        confidence=round(contexts[0].get("score", 0), 3) if contexts else 0.0,
        latency=round(time.perf_counter() - started, 3),
        triage=triage,
        disclaimer=MEDICAL_DISCLAIMER,
    )
