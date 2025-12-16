from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_index: int
    text: str
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    token_count: Optional[int] = None
    heading_path: Optional[List[str]] = None
    anchors: Optional[dict] = None


class ChunkingOptions(BaseModel):
    include_headers: bool = True
    max_chunk_tokens: Optional[int] = None
    overlap_tokens: Optional[int] = None
    max_chunk_chars: Optional[int] = None
    overlap_chars: Optional[int] = None
    strategy: Optional[str] = None
