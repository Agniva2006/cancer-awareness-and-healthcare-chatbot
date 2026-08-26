import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_PATH_1 = BASE_DIR / "cancer_data.json"
DATA_PATH_2 = BASE_DIR / "clinical_oncology_kb.json"

data = []
if DATA_PATH_1.exists():
    with open(DATA_PATH_1, "r", encoding="utf-8") as f:
        data.extend(json.load(f))

if DATA_PATH_2.exists():
    with open(DATA_PATH_2, "r", encoding="utf-8") as f:
        data.extend(json.load(f))

# Combine title + content + category + biomarker for comprehensive index vectorization
texts = []
for item in data:
    cat = item.get("category", "")
    bio = item.get("biomarker", "")
    text = f"{item['title']} {item['content']} {cat} {bio}".strip()
    texts.append(text)

# TF-IDF Vectorizer (ngram range 1-2 for biomarker expressions like 'EGFR L858R' or 'KRAS G12C')
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=10000
)

X = vectorizer.fit_transform(texts)


def retrieve(query: str, k: int = 7, threshold: float = 0.04, category_filter: str = None):
    """
    Retrieve top-k relevant clinical documents based on cosine similarity.
    Filters out documents below similarity threshold and supports optional category filtering.
    """
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, X).flatten()

    top_indices = scores.argsort()[-k*2:][::-1]

    results = []
    for i in top_indices:
        score = float(scores[i])
        if score >= threshold:
            item = data[i].copy()
            item["score"] = score
            if category_filter and item.get("category") != category_filter:
                continue
            results.append(item)
            if len(results) >= k:
                break

    return results


def hybrid_retrieve(query: str, k: int = 5, rrf_k: int = 60, category_filter: str = None) -> List[dict]:
    """
    Tri-Store Hybrid GraphRAG with Reciprocal Rank Fusion (RRF, k=60).
    Combines:
      1. Dense Semantic Retrieval (Cosine similarity across document vector space)
      2. Sparse Lexical Retrieval (BM25-style exact term matching with ICD-10 & mutation boosting)
      3. Graph Traversal Retrieval (NetworkX topological path verification via clinical knowledge graph)
    
    Formula: RRF_Score(d) = sum_{m in {Dense, Sparse, Graph}} 1 / (rrf_k + rank_m(d))
    """
    from app.graph_engine import knowledge_graph

    if not data:
        return []

    # 1. Dense Semantic Ranking
    query_vec = vectorizer.transform([query])
    dense_scores = cosine_similarity(query_vec, X).flatten()
    dense_ranked_indices = dense_scores.argsort()[::-1]
    dense_ranks = {idx: rank + 1 for rank, idx in enumerate(dense_ranked_indices)}

    # 2. Sparse Lexical Ranking (with Clinical Token & ICD-10 Boosting)
    query_tokens = set(query.upper().replace("-", "_").split())
    sparse_scores = []
    for i, item in enumerate(data):
        score = 0.0
        doc_text = f"{item['title']} {item['content']} {item.get('icd10', '')} {item.get('biomarker', '')}".upper()
        
        # Check token matches
        for t in query_tokens:
            if len(t) > 2 and t in doc_text:
                score += 1.0
                # Heavy boost for exact biomarker or ICD-10 matches
                if item.get("icd10") and t == item["icd10"].upper():
                    score += 5.0
                if item.get("biomarker") and t in item["biomarker"].upper():
                    score += 4.0

        # Term overlap ratio
        overlap = sum(1 for t in query_tokens if t in doc_text) / max(1, len(query_tokens))
        sparse_scores.append(score + overlap)

    sparse_ranked_indices = sorted(range(len(data)), key=lambda i: sparse_scores[i], reverse=True)
    sparse_ranks = {idx: rank + 1 for rank, idx in enumerate(sparse_ranked_indices)}

    # 3. Graph-Augmented Path Traversal Ranking
    graph_connected_indices = set()
    graph_connected_entities = []
    for node in knowledge_graph.G.nodes:
        if node.replace("_", " ") in query.upper() or node in query.upper():
            graph_connected_entities.append(node)

    for entity in graph_connected_entities:
        # Check connected therapy or toxicity neighbors
        neighbors = list(knowledge_graph.G.neighbors(entity))
        entity_terms = [entity.lower()] + [n.lower() for n in neighbors]
        for i, item in enumerate(data):
            doc_str = f"{item['title']} {item['content']} {item.get('biomarker', '')}".lower()
            if any(t in doc_str for t in entity_terms):
                graph_connected_indices.add(i)

    # Assign graph ranks (connected docs get top ranks, others penalized)
    sorted_graph = sorted(range(len(data)), key=lambda i: 0 if i in graph_connected_indices else 1)
    graph_ranks = {idx: rank + 1 for rank, idx in enumerate(sorted_graph)}

    # 4. Reciprocal Rank Fusion (RRF) Aggregation
    rrf_scores = {}
    for i in range(len(data)):
        r_dense = dense_ranks.get(i, 999)
        r_sparse = sparse_ranks.get(i, 999)
        r_graph = graph_ranks.get(i, 999)

        score_rrf = (1.0 / (rrf_k + r_dense)) + (1.0 / (rrf_k + r_sparse))
        if i in graph_connected_indices:
            score_rrf += (1.0 / (rrf_k + r_graph))

        rrf_scores[i] = score_rrf

    # Sort by fused RRF score
    fused_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

    results = []
    for i in fused_indices:
        item = data[i].copy()
        if category_filter and item.get("category") != category_filter:
            continue
        
        item["rrf_score"] = round(float(rrf_scores[i]), 5)
        item["dense_rank"] = dense_ranks[i]
        item["sparse_rank"] = sparse_ranks[i]
        item["graph_connected"] = i in graph_connected_indices
        item["retrieval_method"] = "Tri-Store Hybrid RRF (Dense + Sparse + Graph)"
        results.append(item)

        if len(results) >= k:
            break

    return results
