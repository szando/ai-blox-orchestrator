from aiblox_orchestrator.retriever.hybrid_scorer import HybridScorer


def test_rrf_fusion_orders_candidates():
    scorer = HybridScorer(k=60)
    text_results = [("a", 0.9), ("b", 0.8)]
    vec_results = [("b", 0.95), ("c", 0.7)]
    fused = scorer.fuse(text_results=text_results, vec_results=vec_results, top_k=3)
    assert [f.item_id for f in fused] == ["b", "a", "c"]


def test_linear_blend_respects_weights():
    scorer = HybridScorer(blend="linear", w_text=0.8, w_vec=0.2, normalize="none")
    text_results = [("a", 0.2), ("b", 0.1)]
    vec_results = [("a", 0.1), ("b", 0.3)]
    fused = scorer.fuse(text_results=text_results, vec_results=vec_results, top_k=2)
    assert fused[0].item_id == "a"
