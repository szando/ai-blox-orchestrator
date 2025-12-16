## Database setup (dev)

1) Set the database DSN (asyncpg) and schema (defaults shown):

```bash
export AIBLOX_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
export AIBLOX_DB_SCHEMA="kb"
```

2) Run migrations:

```bash
uv run alembic upgrade head
```

3) Start the dev server:

```bash
uv run uvicorn aiblox_orchestrator.server:app --reload
```

You can also create a `.env` file in the project root for local development (loaded automatically):

```
AIBLOX_DB_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
AIBLOX_DB_SCHEMA=kb
```
