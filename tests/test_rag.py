"""Unit tests for the retrieval service."""

from app.services.rag import retrieve


def test_retrieve_returns_results_for_known_topic():
    results = retrieve("lung cancer symptoms", k=5)
    assert len(results) > 0
    assert all("score" in r for r in results)
    assert all(r["score"] >= 0.04 for r in results)


def test_retrieve_returns_sorted_by_score():
    results = retrieve("chemotherapy overview", k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_gibberish_returns_empty():
    assert retrieve("zzzqqqxxx unrelated nothing", k=5) == []
