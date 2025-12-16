from __future__ import annotations

import hashlib
from typing import Iterable, Sequence

from aiblox_orchestrator.retriever.protocols import Embedder


class DeterministicEmbedder(Embedder):
    """Deterministic, low-fidelity embedder stub."""

    def __init__(self, dim: int = 16, model_id: str = "stub-embedder@v1") -> None:
        self.dim = dim
        self.model_id = model_id

    async def embed_query(self, text: str) -> Sequence[float]:
        return self._hash_to_vector(text)

    async def embed_texts(self, texts: Iterable[str]) -> list[Sequence[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def _hash_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(self.dim):
            chunk = digest[i % len(digest)]
            vector.append((chunk / 255.0))
        return vector
