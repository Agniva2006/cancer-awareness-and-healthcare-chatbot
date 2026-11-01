"""Hybrid retrieval service: BM25 (sparse) + TF-IDF (sparse) + optional dense
embeddings, fused with Reciprocal Rank Fusion (RRF).

Why hybrid? Keyword search nails exact clinical terms ("EGFR exon 19 deletion")
but misses synonyms ("my scan" vs "imaging results"). Dense embeddings handle
synonyms but can miss exact codes. Fusing both ranked lists (RRF) gets the
best of both worlds.
"""

import json
import logging
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokenizer shared by BM25 scoring."""
    return _TOKEN_RE.findall(text.lower())


# ── Document loading ──────────────────────────────────────────────
def _load_documents() -> List[Dict[str, Any]]:
    """Load knowledge docs from JSON corpus first, then DB, merging results.

    The JSON lung-cancer corpus is the primary source (checked into git);
    DB documents add admin-managed entries on top.
    """
    rows: List[Dict[str, Any]] = []
    seen_keys = set()

    # 1) Primary: checked-in JSON corpus
    for path in settings.KNOWLEDGE_FILES:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    key = item.get("id") or item.get("title", "")
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    rows.append(item)
        else:
            logger.warning("Knowledge file missing: %s", path)

    # 2) Secondary: DB-managed documents (skip JSON duplicates)
    try:
        from app.core.database import SessionLocal
        from app.models.knowledge import KnowledgeDocument

        db = SessionLocal()
        try:
            docs = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.is_active.is_(True))
                .all()
            )
            for d in docs:
                key = d.external_key or d.title
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                rows.append(
                    {
                        "title": d.title,
                        "content": d.content,
                        "source": d.source,
                        "category": d.category,
                        "cancer_type": getattr(d, "cancer_type", ""),
                        "difficulty": getattr(d, "difficulty", ""),
                    }
                )
            if docs:
                logger.info("Knowledge merged from DB: +%d documents", len(docs))
        finally:
            db.close()
    except Exception as exc:  # DB not reachable (e.g. fresh checkout)
        logger.warning("DB knowledge load skipped (%s)", exc)

    return rows


data: List[Dict[str, Any]] = _load_documents()

# ── Sparse index 1: TF-IDF (1-2 grams catch 'EGFR L858R') ────────
_texts = [
    f"{item['title']} {item['content']} {item.get('category', '')}".strip()
    for item in data
]
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=settings.RAG_MAX_FEATURES,
)
_X = vectorizer.fit_transform(_texts)

# ── Sparse index 2: BM25 ─────────────────────────────────────────
_K1 = 1.5  # term-frequency saturation
_B = 0.75  # length normalization


class _BM25:
    """Standard Okapi BM25 over tokenized documents."""

    def __init__(self, corpus_tokens: List[List[str]]):
        self.doc_count = len(corpus_tokens)
        self.doc_lens = [len(t) for t in corpus_tokens]
        self.avg_len = sum(self.doc_lens) / max(1, self.doc_count)
        self.tf = [Counter(t) for t in corpus_tokens]
        df: Counter = Counter()
        for t in self.tf:
            df.update(t.keys())
        # IDF: BM25+ variant avoids negative scores for very common terms
        self.idf = {
            term: math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query_tokens: List[str], index: int) -> float:
        tf = self.tf[index]
        doc_len = self.doc_lens[index]
        norm = doc_len / self.avg_len if self.avg_len else 0
        score = 0.0
        for term in query_tokens:
            if term not in tf:
                continue
            freq = tf[term]
            idf = self.idf.get(term, 0.0)
            score += idf * (freq * (_K1 + 1)) / (freq + _K1 * (1 - _B + _B * norm))
        return score

    def search(self, query: str, top_n: int) -> List[tuple]:
        q_tokens = _tokenize(query)
        scored = [(self.score(q_tokens, i), i) for i in range(self.doc_count)]
        scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(reverse=True)
        return scored[:top_n]


_bm25 = _BM25([_tokenize(t) for t in _texts])

# ── Dense index (optional): sentence-transformers if installed ────
_dense = {"model": None, "matrix": None}
try:
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _dense["model"] = _model
    _dense["matrix"] = _model.encode(
        _texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True
    )
    logger.info("Dense embeddings ready (%d docs)", len(data))
except Exception as exc:  # pragma: no cover
    logger.info("Dense embeddings unavailable (%s); hybrid = BM25+TFIDF only", exc)


# ── Reciprocal Rank Fusion ───────────────────────────────────────
def _rrf_fuse(
    *ranked_lists: List[int], k: int = settings.RAG_RRF_K, top_n: int = 10
) -> List[tuple]:
    """Fuse ranked index lists into one ranking. score = sum(1/(k + rank))."""
    fused: Dict[int, float] = {}
    for lst in ranked_lists:
        for rank, idx in enumerate(lst):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_n]


def retrieve(
    query: str,
    k: int = settings.RAG_TOP_K,
    threshold: float = 0.0,  # fused RRF scores are small; grounding gate handles cutoffs
    category_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: BM25 + TF-IDF + (optional) dense embeddings, merged
    with Reciprocal Rank Fusion. Returns up to k documents sorted by fused score.
    """
    if not data:
        return []

    # 1) BM25 ranking
    bm25_ranking = [i for _, i in _bm25.search(query, k * 3)]

    # 2) TF-IDF cosine ranking
    q_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(q_vec, _X).flatten()
    tfidf_ranking = tfidf_scores.argsort()[::-1][: k * 3].tolist()
    tfidf_ranking = [i for i in tfidf_ranking if tfidf_scores[i] > 0]

    # 3) Dense ranking (if model loaded)
    dense_ranking: List[int] = []
    if _dense["model"] is not None and _dense["matrix"] is not None:
        import numpy as np

        q_emb = _dense["model"].encode([query], normalize_embeddings=True)[0]
        sims = _dense["matrix"] @ q_emb
        dense_ranking = np.argsort(sims)[::-1][: k * 3].tolist()
        dense_ranking = [i for i in dense_ranking if sims[i] > 0.1]

    fused = _rrf_fuse(bm25_ranking, tfidf_ranking, dense_ranking, top_n=k)

    results: List[Dict[str, Any]] = []
    for idx, score in fused:
        item = data[idx].copy()
        item["score"] = round(score, 4)
        if category_filter and item.get("category") != category_filter:
            continue
        results.append(item)
    return results


def grounding_ok(results: List[Dict[str, Any]]) -> bool:
    """True if the fused scores suggest we actually know the answer."""
    if not results:
        return False
    return results[0].get("score", 0.0) >= settings.RAG_GROUNDING_THRESHOLD
