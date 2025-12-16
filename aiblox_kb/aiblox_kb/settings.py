from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Env-driven settings for the KB contract."""

    def __init__(self) -> None:
        self.db_dsn = os.getenv("AIBLOX_DB_DSN", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
        self.db_schema = os.getenv("AIBLOX_DB_SCHEMA", "kb")


def load_settings() -> Settings:
    return Settings()
