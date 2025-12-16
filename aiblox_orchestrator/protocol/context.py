from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RequestContext(BaseModel):
    """Per-request context propagated across components."""

    request_id: str
    trace_id: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    cancellation_event: asyncio.Event = Field(
        default_factory=asyncio.Event, exclude=True
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def cancelled(self) -> bool:
        return self.cancellation_event.is_set()

    def cancel(self) -> None:
        self.cancellation_event.set()


class UserInput(BaseModel):
    """UI-provided user input."""

    text: str
    mode: str = "chat"  # chat | rag | tool | hybrid
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retrieval_prefs: Dict[str, Any] | None = None
    debug: bool = False


class ConversationWindow(BaseModel):
    """Lightweight conversation history, if provided."""

    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ProductProfile(BaseModel):
    """Product or surface profile hints."""

    name: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)
