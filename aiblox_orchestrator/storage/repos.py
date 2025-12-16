"""SQLAlchemy ORM repository stubs."""

from __future__ import annotations

from typing import Any


class ItemRepo:
    """Placeholder for document/item repository."""

    def __init__(self, session_factory: Any | None = None) -> None:
        self.session_factory = session_factory

    async def get_content(self, item_id: str) -> str | None:
        return None


class ChunkCacheRepo:
    """Placeholder for derived chunk cache repository."""

    def __init__(self, session_factory: Any | None = None) -> None:
        self.session_factory = session_factory

    async def get_cached_chunks(self, cache_key: str) -> list[Any]:
        return []

    async def set_cached_chunks(self, cache_key: str, chunks: list[Any]) -> None:
        return None
