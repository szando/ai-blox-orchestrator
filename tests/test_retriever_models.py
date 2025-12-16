from aiblox_orchestrator.retriever.models import CandidateItem, EvidenceChunk, RetrievalBundle, RetrievalPrefs


def test_retrieval_prefs_defaults():
    prefs = RetrievalPrefs(query_text="hello world")
    assert prefs.top_k_items == 20
    assert prefs.top_k_chunks == 12
    assert prefs.fts["mode"] == "web"
    assert prefs.vector["distance"] == "cosine"
    assert prefs.scoring["blend"] == "rrf"
    assert prefs.chunking["strategy"] == "late"
    assert prefs.cache["use_chunk_cache"] is True


def test_candidate_item_defaults():
    candidate = CandidateItem(item_id="1", kind="doc", source="kb", score=0.5)
    assert candidate.snippet is None
    assert candidate.snippet_from == "unknown"


def test_retrieval_bundle_defaults():
    bundle = RetrievalBundle()
    assert bundle.candidates == []
    assert bundle.evidence == []
    assert bundle.stats.counts == {}
