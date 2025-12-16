from __future__ import annotations

import os

from dotenv import load_dotenv

# Load local overrides from .env during development (no-op if missing)
load_dotenv()

class Settings:
    """Simple env-driven settings."""

    db_dsn: str
    db_schema: str

    def __init__(self) -> None:
        self.db_dsn = os.getenv("AIBLOX_DB_DSN", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
        self.db_schema = os.getenv("AIBLOX_DB_SCHEMA", "kb")


def load_settings() -> Settings:
    return Settings()
