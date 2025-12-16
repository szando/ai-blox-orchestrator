from __future__ import annotations

from typing import Iterable, Protocol, Sequence

from aiblox_orchestrator.protocol.context import RequestContext
from aiblox_orchestrator.retriever.models import RetrievalBundle, RetrievalPrefs


class Retriever(Protocol):
    async def search(self, ctx: RequestContext, prefs: RetrievalPrefs) -> RetrievalBundle:
        ...


class Embedder(Protocol):
    """Embedding provider interface."""

    model_id: str

    async def embed_query(self, text: str) -> Sequence[float]:
        ...

    async def embed_texts(self, texts: Iterable[str]) -> list[Sequence[float]]:
        ...
