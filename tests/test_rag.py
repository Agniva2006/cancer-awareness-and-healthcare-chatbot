"""Unit tests for the hybrid retrieval service."""

from app.services.rag import grounding_ok, retrieve


def test_retrieve_returns_results_for_known_topic():
    results = retrieve("lung cancer symptoms", k=5)
    assert len(results) > 0
    assert all("score" in r for r in results)


def test_retrieve_sorted_by_fused_score():
    results = retrieve("chemotherapy side effects", k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_lung_specialist_egfr_query():
    hits = {r["title"].lower() for r in retrieve("EGFR exon 19 deletion", k=3)}
    assert any("egfr" in t for t in hits)


def test_lung_specialist_screening_query():
    hits = {r["title"].lower() for r in retrieve("USPSTF lung screening criteria", k=3)}
    assert any("screen" in t for t in hits)


def test_gibberish_fails_grounding():
    """Nonsense queries must fail the grounding gate."""
    results = retrieve("zzzqqqxxx unrelated nothing", k=5)
    assert grounding_ok(results) is False


def test_good_query_passes_grounding():
    results = retrieve("fever after chemotherapy emergency", k=3)
    assert grounding_ok(results) is True
