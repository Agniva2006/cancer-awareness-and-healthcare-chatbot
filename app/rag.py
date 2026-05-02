import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Load data
with open("data/cancer_data.json", "r") as f:
    data = json.load(f)

# Combine title + content for better retrieval
texts = [f"{item['title']} {item['content']}" for item in data]

# TF-IDF Vectorizer (improved)
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=5000
)

X = vectorizer.fit_transform(texts)


def retrieve(query, k=7):
    """
    Retrieve top-k relevant documents based on cosine similarity
    """

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, X).flatten()

    # Get top-k indices
    top_indices = scores.argsort()[-k:][::-1]

    results = []
    for i in top_indices:
        item = data[i].copy()
        item["score"] = float(scores[i])  # attach score for re-ranking
        results.append(item)

    return results