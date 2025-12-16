from __future__ import annotations

from aiblox_orchestrator.orchestrator.interfaces import Retriever
from aiblox_orchestrator.protocol.context import RequestContext
from aiblox_orchestrator.retriever.models import RetrievalBundle, RetrievalPrefs


class EmptyRetriever(Retriever):
    """Stub Retriever that returns no candidates or evidence."""

    async def search(
        self,
        ctx: RequestContext,
        prefs: RetrievalPrefs,
    ) -> RetrievalBundle:
        return RetrievalBundle()
