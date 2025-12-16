from aiblox_orchestrator.evidence.models import EvidencePackOptions
from aiblox_orchestrator.evidence.packer import DefaultEvidencePacker
from aiblox_orchestrator.retriever.models import CandidateItem, EvidenceChunk


def make_candidate(idx: int, score: float | None = None, rank_text: int | None = None):
    return CandidateItem(
        item_id=f"id{idx}",
        kind="doc",
        source="kb",
        score=score if score is not None else 0.0,
        rank_text=rank_text,
        title=f"title {idx}",
        summary=f"summary {idx}",
        metadata={"keep": idx, "drop": idx},
    )


def make_chunk(item_id: str, score: float, text: str):
    return EvidenceChunk(
        item_id=item_id,
        text=text,
        score=score,
    )


def test_deterministic_output():
    packer = DefaultEvidencePacker()
    candidates = [make_candidate(1, score=0.5), make_candidate(2, score=0.4)]
    opts = EvidencePackOptions()
    first = packer.pack(candidates, [], opts)
    second = packer.pack(candidates, [], opts)
    assert first == second


def test_chunk_snippet_preference():
    packer = DefaultEvidencePacker()
    candidates = [make_candidate(1, score=0.5)]
    chunks = [make_chunk("id1", score=0.9, text="chunk text")]
    opts = EvidencePackOptions(prefer_chunk_snippets=True)
    out = packer.pack(candidates, chunks, opts)
    assert out[0].snippet == "chunk text"
    assert out[0].snippet_from == "chunk"


def test_doc_fallback_when_no_chunks():
    packer = DefaultEvidencePacker()
    candidates = [make_candidate(1, score=0.5)]
    opts = EvidencePackOptions(prefer_chunk_snippets=True)
    out = packer.pack(candidates, None, opts)
    assert out[0].snippet.startswith("summary")
    assert out[0].snippet_from == "doc"


def test_order_by_score_and_max_sources():
    packer = DefaultEvidencePacker()
    candidates = [
        make_candidate(1, score=0.2),
        make_candidate(2, score=0.9),
        make_candidate(3, score=0.5),
    ]
    opts = EvidencePackOptions(max_sources=2, order_by="score")
    out = packer.pack(candidates, None, opts)
    assert [s.source_id for s in out] == ["id2", "id3"]


def test_order_by_input():
    packer = DefaultEvidencePacker()
    candidates = [make_candidate(1, score=0.1), make_candidate(2, score=0.9)]
    opts = EvidencePackOptions(order_by="input")
    out = packer.pack(candidates, None, opts)
    assert [s.source_id for s in out] == ["id1", "id2"]


def test_metadata_include_exclude():
    packer = DefaultEvidencePacker()
    candidates = [make_candidate(1, score=0.5)]
    opts = EvidencePackOptions(include_metadata_keys=["keep"], exclude_metadata_keys=["drop"])
    out = packer.pack(candidates, None, opts)
    assert "keep" in out[0].metadata
    assert "drop" not in out[0].metadata


def test_missing_fields_do_not_crash():
    packer = DefaultEvidencePacker()
    candidate = CandidateItem(item_id="id1", kind="doc", source="kb", score=0.1)
    out = packer.pack([candidate], None, EvidencePackOptions())
    assert out[0].title is None
    assert out[0].url is None
    assert out[0].snippet is None or isinstance(out[0].snippet, str)
