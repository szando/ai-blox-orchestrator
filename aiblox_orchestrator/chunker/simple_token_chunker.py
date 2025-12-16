from __future__ import annotations

from typing import List

from aiblox_orchestrator.chunker.models import Chunk, ChunkingOptions
from aiblox_orchestrator.chunker.protocols import Chunker


class SimpleTokenLikeChunker(Chunker):
    """
    Whitespace-based token-like chunker.

    TODO: replace with real tokenizer integration (tiktoken/HF) when available.
    """

    chunker_id = "simple_token_like@v1"

    def chunk(self, text: str, options: ChunkingOptions) -> List[Chunk]:
        if not text:
            return []
        max_tokens = options.max_chunk_tokens or 200
        overlap_tokens = options.overlap_tokens or 0
        tokens = text.split()
        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0
        while start < len(tokens):
            end = min(len(tokens), start + max_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = " ".join(chunk_tokens)
            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_index=chunk_index,
                        text=chunk_text,
                        start_idx=None,
                        end_idx=None,
                        token_count=len(chunk_tokens),
                    )
                )
                chunk_index += 1
            if end >= len(tokens):
                break
            start = max(0, end - overlap_tokens)
        return chunks
