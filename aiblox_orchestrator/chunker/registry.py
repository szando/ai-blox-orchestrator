from __future__ import annotations

from typing import Dict, List

from aiblox_orchestrator.chunker.protocols import Chunker, ChunkerRegistry
from aiblox_orchestrator.chunker.simple_char_chunker import SimpleCharChunker
from aiblox_orchestrator.chunker.simple_token_chunker import SimpleTokenLikeChunker


class InMemoryChunkerRegistry(ChunkerRegistry):
    """Registry that stores chunkers in memory."""

    def __init__(self, chunkers: Dict[str, Chunker] | None = None, aliases: Dict[str, str] | None = None) -> None:
        token_chunker = SimpleTokenLikeChunker()
        char_chunker = SimpleCharChunker()
        default_chunkers = {
            token_chunker.chunker_id: token_chunker,
            char_chunker.chunker_id: char_chunker,
        }
        self._chunkers = chunkers or default_chunkers
        default_aliases = {"default": token_chunker.chunker_id}
        self._aliases = aliases or default_aliases

    def get(self, chunker_id: str) -> Chunker:
        resolved = self._aliases.get(chunker_id, chunker_id)
        if resolved in self._chunkers:
            return self._chunkers[resolved]
        raise KeyError(f"chunker not found: {chunker_id}")

    def has(self, chunker_id: str) -> bool:
        resolved = self._aliases.get(chunker_id, chunker_id)
        return resolved in self._chunkers

    def list_ids(self) -> List[str]:
        return list(self._chunkers.keys()) + list(self._aliases.keys())
