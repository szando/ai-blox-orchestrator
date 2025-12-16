from __future__ import annotations

from typing import List, Protocol

from aiblox_orchestrator.chunker.models import Chunk, ChunkingOptions


class Chunker(Protocol):
    chunker_id: str

    def chunk(self, text: str, options: ChunkingOptions) -> List[Chunk]:
        ...


class ChunkerRegistry(Protocol):
    def get(self, chunker_id: str) -> Chunker: ...

    def has(self, chunker_id: str) -> bool: ...

    def list_ids(self) -> List[str]: ...
