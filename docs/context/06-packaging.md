# AI Blox Orchestrator – Packaging & Workspace Layout

## Purpose

This document defines how the **KB contract** is packaged and shared across AI Blox blocks,
while keeping **ownership** inside the **aiblox-orchestrator** repository.

We use a **uv workspace** in a **root-is-runtime** configuration:

- the repository root remains the primary runnable project (the orchestrator runtime)
- additional packages (e.g. the KB contract) live alongside it
- all packages share a single environment and lockfile

This avoids unnecessary repository splits while still enabling clean modular boundaries.

---

## Core decision: package the contract, not the runtime

- The orchestrator owns the **KB contract** (`kb` schema, ORM models, repositories, migrations).
- Other blocks (e.g. ingestion/ETL) must not copy storage logic.
- Instead, they depend on a dedicated, installable contract package.

We therefore introduce:

> **`aiblox_kb`** – the KB contract package  
> (ORM models, repositories, DB helpers, Alembic migrations)

The orchestrator runtime imports and depends on `aiblox_kb`.
The contract package never imports from the orchestrator runtime.

---

## Workspace mode: root-is-runtime

### What this means

- The repository root `pyproject.toml` defines the **orchestrator runtime project**
- The root is also the **uv workspace root**
- `aiblox_kb` is added as a **workspace member**, not as a separate repo
- The runtime remains the default project when running `uv run ...`

This minimizes restructuring while still allowing shared packages.

---

## Repository structure

Actual layout inside the repository:

```

aiblox-orchestrator/
├── pyproject.toml          # orchestrator runtime + uv workspace root
├── uv.lock
├── aiblox_orchestrator/    # orchestrator runtime package
│   ├── router/
│   ├── orchestrator/
│   ├── retriever/
│   ├── chunker/
│   ├── evidence/
│   ├── protocol/
│   ├── observability/
│   ├── server.py
│   └── config/
│
├── aiblox_kb/              # KB contract package (workspace member)
│   ├── pyproject.toml
│   ├── aiblox_kb/
│   │   ├── **init**.py
│   │   ├── models.py
│   │   ├── db.py
│   │   └── repos/
│   │       ├── item_repo.py
│   │       └── chunk_cache_repo.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── alembic.ini
│
├── docs/
│   └── context/
└── tests/

```

Notes:
- `aiblox_kb` owns the **kb schema** and its migrations
- `aiblox_orchestrator` owns runtime behavior and orchestration logic
- both live in the same workspace and share dependencies

---

## Dependency rules (hard)

### 1) No reverse imports
- `aiblox_kb` **must not** import from `aiblox_orchestrator`
- `aiblox_orchestrator` **may** import from `aiblox_kb`

### 2) Public API of `aiblox_kb` is intentionally small
Only the following are considered public/stable:

- ORM models: `KbItem`, `KbChunkCache`
- repositories: `ItemRepo`, `ChunkCacheRepo`
- DB helpers: async engine / sessionmaker / session-factory builders
- minimal configuration surface:
  - database DSN
  - schema name (default: `kb`)

Everything else is internal and may change freely.

---

## Migrations ownership and execution

### Ownership
- `aiblox_kb` owns all Alembic migrations for the `kb` schema.

### Execution strategy (v0.1)
**Each service runs migrations for the schemas it depends on.**

Practically:
- the orchestrator runtime runs `aiblox_kb` migrations in dev and deployment
- ingestion/ETL services that write to `kb` also run `aiblox_kb` migrations

This avoids central migration services in early phases and keeps blocks self-contained.

---

## Versioning policy

Even though both packages live in one repository, treat `aiblox_kb` as a versioned contract:

- schema or semantic changes → bump `aiblox_kb` version
- runtime-only changes → bump orchestrator version

uv workspaces allow editable local development.
For CI or production, `aiblox_kb` may be published independently if needed.

---

## Why this design

- Keeps **contract ownership** with the orchestrator
- Avoids code drift and copy-paste across blocks
- Enables ingestion and other blocks to adapt to multiple downstream contracts
- Allows future extraction into a separate repo without redesign
- Keeps current repo structure simple and pragmatic


