from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Stable event envelope for UI consumption."""

    type: str
    protocol_version: str = "1.0"
    request_id: str
    seq: int
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Optional[Dict[str, Any]] = None
