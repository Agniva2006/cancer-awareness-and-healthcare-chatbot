"""TF-IDF retrieval service over the local knowledge base."""

import json
import logging
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Load knowledge documents ──────────────────────────────
data: List[Dict[str, Any]] = []
for path in settings.KNOWLEDGE_FILES:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data.extend(json.load(f))
    else:
        logger.warning("Knowledge file missing: %s", path)

# Combine title + content + category + biomarker for comprehensive indexing
texts = [
    f"{item['title']} {item['content']} {item.get('category', '')} {item.get('biomarker', '')}".strip()
    for item in data
]

# TF-IDF with 1-2 grams to catch biomarker expressions like 'EGFR L858R'
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=settings.RAG_MAX_FEATURES,
)
X = vectorizer.fit_transform(texts)

logger.info("RAG index built: %d documents", len(data))


def retrieve(
    query: str,
    k: int = settings.RAG_TOP_K,
    threshold: float = settings.RAG_SCORE_THRESHOLD,
    category_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant clinical documents based on cosine similarity.

    Filters out documents below the similarity threshold and supports
    optional category filtering.
    """
    if not data:
        return []

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, X).flatten()
    top_indices = scores.argsort()[-k * 2 :][::-1]

    results = []
    for i in top_indices:
        score = float(scores[i])
        if score < threshold:
            continue
        item = data[i].copy()
        item["score"] = score
        if category_filter and item.get("category") != category_filter:
            continue
        results.append(item)
        if len(results) >= k:
            break

    return results
