from __future__ import annotations

from typing import Protocol

from aiblox_orchestrator.protocol.events import EventEnvelope


class EventSink(Protocol):
    async def emit(self, event: EventEnvelope) -> None:
        ...
