from __future__ import annotations

from typing import Callable, Iterable
from uuid import UUID

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aiblox_orchestrator.retriever.tsquery import build_tsquery
from aiblox_orchestrator.storage.models import KbItem


class ItemRepo:
    """SQLAlchemy ORM repository for KB items."""

    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None) -> None:
        self.session_factory = session_factory

    async def search_fts(
        self,
        query_text: str,
        prefs,
    ) -> list[tuple[str, float]]:
        if not self.session_factory:
            return []
        tsquery = build_tsquery(
            query_text=query_text,
            mode=prefs.fts.get("mode", "web"),
            config=prefs.fts.get("config"),
            allow_strict=prefs.fts.get("allow_strict", False),
        )
        rank_func_name = prefs.fts.get("rank_func", "ts_rank_cd")
        rank_func = getattr(func, rank_func_name, func.ts_rank_cd)
        rank_expr = rank_func(KbItem.tsv, tsquery).label("rank_text")
        stmt: Select = select(KbItem.id, rank_expr).where(KbItem.tsv.op("@@")(tsquery))
        for key, value in (prefs.filters or {}).items():
            col = getattr(KbItem, key, None)
            if col is not None:
                stmt = stmt.where(col == value)
        stmt = stmt.order_by(desc(rank_expr)).limit(prefs.top_k_items)
        if prefs.fts.get("min_rank") is not None:
            stmt = stmt.where(rank_expr >= prefs.fts["min_rank"])
        async with self.session_factory() as session:
            result = await session.execute(stmt)
            rows = result.all()
            return [(row.id, float(row.rank_text)) for row in rows]

    async def search_vec(
        self,
        query_vector,
        prefs,
    ) -> list[tuple[str, float]]:
        # v0.1: embeddings/pgvector not yet included (Option B)
        return []

    async def fetch_items_by_ids(self, item_ids: Iterable[UUID]) -> list[KbItem]:
        if not self.session_factory:
            return []
        stmt = select(KbItem).where(KbItem.id.in_(list(item_ids)))
        async with self.session_factory() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())
