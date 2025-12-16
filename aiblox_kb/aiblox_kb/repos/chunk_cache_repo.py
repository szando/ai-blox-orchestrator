from __future__ import annotations

from typing import Callable, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aiblox_kb.models import KbChunkCache


class ChunkCacheRepo:
    """Derived chunk cache repository."""

    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None) -> None:
        self.session_factory = session_factory

    async def get_cached_chunks(
        self,
        item_id: UUID,
        content_hash: str,
        chunker_id: str,
        embed_model_id: str | None,
    ) -> list[dict]:
        if not self.session_factory:
            return []
        stmt = select(KbChunkCache).where(
            KbChunkCache.item_id == item_id,
            KbChunkCache.content_hash == content_hash,
            KbChunkCache.chunker_id == chunker_id,
            KbChunkCache.embed_model_id == embed_model_id,
        )
        async with self.session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [row_to_dict(row) for row in rows]

    async def write_cached_chunks(
        self,
        item_id: UUID,
        owner_user_id: UUID,
        content_hash: str,
        chunker_id: str,
        embed_model_id: str | None,
        chunks: Iterable[dict],
    ) -> None:
        if not self.session_factory:
            return None
        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "id": chunk.get("id"),
                    "item_id": item_id,
                    "owner_user_id": owner_user_id,
                    "content_hash": content_hash,
                    "chunker_id": chunker_id,
                    "embed_model_id": embed_model_id,
                    "chunk_index": chunk.get("chunk_index"),
                    "chunk_text": chunk.get("text") or chunk.get("chunk_text"),
                    "start_idx": chunk.get("start_idx"),
                    "end_idx": chunk.get("end_idx"),
                    "token_count": chunk.get("token_count"),
                }
            )
        if not rows:
            return None
        stmt = insert(KbChunkCache).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                KbChunkCache.item_id,
                KbChunkCache.content_hash,
                KbChunkCache.chunker_id,
                KbChunkCache.embed_model_id,
                KbChunkCache.chunk_index,
            ]
        )
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(stmt)
        return None


def row_to_dict(row: KbChunkCache) -> dict:
    return {
        "id": str(row.id),
        "item_id": str(row.item_id),
        "content_hash": row.content_hash,
        "chunker_id": row.chunker_id,
        "embed_model_id": row.embed_model_id,
        "chunk_index": row.chunk_index,
        "text": row.chunk_text,
        "start_idx": row.start_idx,
        "end_idx": row.end_idx,
        "token_count": row.token_count,
    }
