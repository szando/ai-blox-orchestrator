from __future__ import annotations

from typing import Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def make_engine(db_dsn: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(db_dsn, future=True, echo=echo)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def make_session_factory(sessionmaker: async_sessionmaker[AsyncSession]) -> Callable[[], AsyncSession]:
    return sessionmaker
