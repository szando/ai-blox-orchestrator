from __future__ import annotations

from typing import List

from aiblox_orchestrator.chunker.models import Chunk, ChunkingOptions
from aiblox_orchestrator.chunker.protocols import Chunker


class SimpleCharChunker(Chunker):
    """
    Deterministic char-based chunker with optional overlap.
    """

    chunker_id = "simple_char@v1"

    def chunk(self, text: str, options: ChunkingOptions) -> List[Chunk]:
        if not text:
            return []
        max_chars = options.max_chunk_chars or 500
        overlap = options.overlap_chars or 0
        chunks: List[Chunk] = []
        idx = 0
        chunk_index = 0
        while idx < len(text):
            end = min(len(text), idx + max_chars)
            chunk_text = text[idx:end]
            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_index=chunk_index,
                        text=chunk_text,
                        start_idx=idx,
                        end_idx=end,
                        token_count=None,
                    )
                )
                chunk_index += 1
            if end >= len(text):
                break
            idx = max(0, end - overlap)
        return chunks
