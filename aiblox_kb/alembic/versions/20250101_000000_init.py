"""Initial schema for kb items and chunk cache."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250101_000000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = op.get_context().config.attributes.get("schema", None) or "kb"

    op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    op.create_table(
        "kb_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=schema,
    )
    op.create_index("ix_kb_items_tsv", "kb_items", ["tsv"], unique=False, postgresql_using="gin", schema=schema)
    op.create_index("ix_kb_items_owner_user_id", "kb_items", ["owner_user_id"], unique=False, schema=schema)

    op.create_table(
        "kb_chunk_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("chunker_id", sa.Text(), nullable=False),
        sa.Column("embed_model_id", sa.Text(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("start_idx", sa.Integer(), nullable=True),
        sa.Column("end_idx", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], [f"{schema}.kb_items.id"], ondelete="CASCADE"),
        schema=schema,
    )
    op.create_index("ix_kb_chunk_cache_item_id", "kb_chunk_cache", ["item_id"], unique=False, schema=schema)
    op.create_index("ix_kb_chunk_cache_owner_user_id", "kb_chunk_cache", ["owner_user_id"], unique=False, schema=schema)
    op.create_index(
        "uq_kb_chunk_cache_unique_entry",
        "kb_chunk_cache",
        ["item_id", "content_hash", "chunker_id", "embed_model_id", "chunk_index"],
        unique=True,
        schema=schema,
    )


def downgrade() -> None:
    schema = op.get_context().config.attributes.get("schema", None) or "kb"
    op.drop_index("uq_kb_chunk_cache_unique_entry", table_name="kb_chunk_cache", schema=schema)
    op.drop_index("ix_kb_chunk_cache_owner_user_id", table_name="kb_chunk_cache", schema=schema)
    op.drop_index("ix_kb_chunk_cache_item_id", table_name="kb_chunk_cache", schema=schema)
    op.drop_table("kb_chunk_cache", schema=schema)

    op.drop_index("ix_kb_items_owner_user_id", table_name="kb_items", schema=schema)
    op.drop_index("ix_kb_items_tsv", table_name="kb_items", schema=schema)
    op.drop_table("kb_items", schema=schema)
