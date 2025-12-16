from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = os.getenv("AIBLOX_DB_SCHEMA", "kb")


class Base(DeclarativeBase):
    pass


class KbItem(Base):
    __tablename__ = "kb_items"
    __table_args__ = (
        Index("ix_kb_items_tsv", "tsv", postgresql_using="gin"),
        Index("ix_kb_items_owner_user_id", "owner_user_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)

    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    tsv: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class KbChunkCache(Base):
    __tablename__ = "kb_chunk_cache"
    __table_args__ = (
        Index("ix_kb_chunk_cache_item_id", "item_id"),
        Index("ix_kb_chunk_cache_owner_user_id", "owner_user_id"),
        Index(
            "uq_kb_chunk_cache_unique_entry",
            "item_id",
            "content_hash",
            "chunker_id",
            "embed_model_id",
            "chunk_index",
            unique=True,
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.kb_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    chunker_id: Mapped[str] = mapped_column(Text, nullable=False)
    embed_model_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_idx: Mapped[int | None] = mapped_column(nullable=True)
    end_idx: Mapped[int | None] = mapped_column(nullable=True)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
