from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class EvidencePackOptions(BaseModel):
    max_sources: int = 6
    prefer_chunk_snippets: bool = True
    max_snippet_chars: int = 360
    include_metadata_keys: list[str] | None = None
    exclude_metadata_keys: list[str] | None = None
    order_by: Literal["score", "rank", "input"] = "score"
    debug: bool = False


class SourceItem(BaseModel):
    source_id: str
    kind: str
    title: Optional[str]
    url: Optional[str]
    snippet: Optional[str]
    snippet_from: str
    score: Optional[float] = None
    rank: Optional[int] = None
    metadata: Dict[str, object] = Field(default_factory=dict)
