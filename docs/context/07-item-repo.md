# ItemRepo – Minimal KB Write/Read Contract (v0)

## Status

**v0 – intentionally minimal**

This document defines the first stable persistence contract for KB items
stored in the `kb.kb_items` table and accessed via `ItemRepo`.

The scope is deliberately narrow. The contract is expected to evolve, but
backward-incompatible changes must be explicit and coordinated across
dependent AI Blox blocks.

---

## Purpose

`ItemRepo` defines the canonical write/read boundary for **knowledge base items**.

It exists to:
- allow ingestion pipelines to write normalized KB records
- allow the orchestrator and retriever to read and search KB records
- provide a stable contract independent of ingestion or orchestration logic

`ItemRepo` is part of the **KB contract**, owned by the orchestrator block and
packaged via `aiblox_kb`.

---

## Responsibilities (v0)

In this version, `ItemRepo` is responsible for:

- inserting KB items
- idempotent upserts using `(owner_user_id, source, source_ref)`
- owner-scoped reads
- owner-scoped full-text search using PostgreSQL FTS (`tsvector` + `tsquery`)
- deterministic computation of:
  - `content_hash`
  - `tsvector` columns
- schema-aware operation (`kb` schema)

---

## Explicit Non-Responsibilities

`ItemRepo` does **not**:

- manage embeddings or vectors
- manage chunking or chunk cache
- perform hybrid ranking or scoring
- call DSPy or LLMs
- enforce domain-specific semantics beyond storage
- allow cross-owner access

These concerns belong to other blocks (retriever, chunker, orchestrator).

---

## Identity & Ownership Rules

- Every KB item has a UUID primary key (`id`)
- Every operation is scoped by `owner_user_id`
- `(owner_user_id, source, source_ref)` defines an **idempotency boundary**
- Ownership is enforced at the repository level, not the caller level

---

## Write Semantics

On insert or update:

- `content_hash` is computed deterministically from `content_text`
- `tsvector` is computed using:
  ```sql
  to_tsvector('simple', title || ' ' || summary || ' ' || content_text)
  ```

* Updates must refresh:

  * `content_text`
  * `content_hash`
  * `tsvector`
  * `updated_at`
* Timestamps are DB-managed (`created_at`, `updated_at`)

---

## Read Semantics

### `get_item`

* Returns a single item by `(owner_user_id, id)`
* Returns `None` if not found or not owned

### `list_items`

* Convenience API for inspection and tests
* Not a paging or cursor contract
* Always owner-scoped

### `search_fts`

* Uses PostgreSQL full-text search only
* Ranking is based on `ts_rank_cd`
* No vector or hybrid scoring in v0

---

## Evolution Notes

Future versions may introduce:

* hybrid scoring hooks
* embedding references
* richer metadata constraints
* write-time validation layers

Such changes must not silently alter the semantics defined in this document.