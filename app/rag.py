import json
from pathlib import Path
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
