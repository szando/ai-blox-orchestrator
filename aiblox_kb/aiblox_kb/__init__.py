"""KB contract package: models, repos, db helpers."""

from aiblox_kb.db import make_engine, make_session_factory, make_sessionmaker
from aiblox_kb.models import Base, KbChunkCache, KbItem, SCHEMA
from aiblox_kb.repos.item_repo import ItemRepo
from aiblox_kb.repos.chunk_cache_repo import ChunkCacheRepo

__all__ = [
    "Base",
    "KbItem",
    "KbChunkCache",
    "SCHEMA",
    "ItemRepo",
    "ChunkCacheRepo",
    "make_engine",
    "make_sessionmaker",
    "make_session_factory",
]
