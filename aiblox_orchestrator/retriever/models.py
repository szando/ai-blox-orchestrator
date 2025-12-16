from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalPrefs(BaseModel):
    query_text: str
    filters: Dict[str, object] = Field(default_factory=dict)

    top_k_items: int = 20
    top_k_chunks: int = 12
    per_item_chunk_cap: int = 3

    fts: Dict[str, object] = Field(
        default_factory=lambda: {
            "mode": "web",
            "config": None,
            "rank_func": "ts_rank_cd",
            "min_rank": None,
        }
    )
    vector: Dict[str, object] = Field(
        default_factory=lambda: {
            "embed_query": True,
            "distance": "cosine",
            "min_score": None,
        }
    )
    scoring: Dict[str, object] = Field(
        default_factory=lambda: {
            "blend": "rrf",
            "w_text": 0.35,
            "w_vec": 0.65,
            "normalize": "sigmoid",
        }
    )
    chunking: Dict[str, object] = Field(
        default_factory=lambda: {
            "strategy": "late",
            "chunker_id": "default",
            "include_headers": True,
            "max_chunk_tokens": None,
            "overlap_tokens": None,
        }
    )
    cache: Dict[str, object] = Field(
        default_factory=lambda: {
            "use_chunk_cache": True,
            "write_chunk_cache": True,
            "ttl_seconds": None,
        }
    )
    snippet: Dict[str, object] = Field(
        default_factory=lambda: {"max_chars": 360, "prefer_chunk_snippet": True}
    )
    debug: bool = False


class CandidateItem(BaseModel):
    item_id: str
    kind: str
    source: str
    source_ref: Optional[str] = None

    title: Optional[str] = None
    summary: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)

    score: float = 0.0
    score_text: Optional[float] = None
    score_vec: Optional[float] = None
    rank_text: Optional[int] = None
    rank_vec: Optional[int] = None

    snippet: Optional[str] = None
    snippet_from: str = "unknown"


class EvidenceChunk(BaseModel):
    item_id: str
    chunk_id: Optional[str] = None

    text: str
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    token_count: Optional[int] = None

    score: float = 0.0
    score_text: Optional[float] = None
    score_vec: Optional[float] = None

    heading_path: Optional[List[str]] = None
    anchors: Optional[Dict[str, object]] = None


class RetrievalStats(BaseModel):
    timing_ms: Dict[str, float] = Field(default_factory=dict)
    counts: Dict[str, int] = Field(default_factory=dict)
    params: Dict[str, object] = Field(default_factory=dict)


class RetrievalBundle(BaseModel):
    candidates: List[CandidateItem] = Field(default_factory=list)
    evidence: List[EvidenceChunk] = Field(default_factory=list)
    stats: RetrievalStats = Field(default_factory=RetrievalStats)
