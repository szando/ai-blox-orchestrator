# AI Blox – Retriever Design (v0.1)

## Role of the Retriever

The Retriever is a **capability**, not the brain.

It performs **grounded evidence acquisition** when invoked by the Orchestrator,
based on an ExecutionPlan produced by the Decision Router.

The Retriever:
- performs **hybrid search** (vector + full-text)
- supports **late chunking**
- returns **document-level candidates** and **chunk-level evidence**
- is fully **product-agnostic**
- does **not** emit UI events itself

The Orchestrator decides *whether* to call the Retriever.
The Retriever decides *how* to retrieve.

---

## Core Principles

1. **Hybrid search is mandatory**
   - vector similarity alone is insufficient
   - full-text search alone is insufficient
   - both signals are combined deliberately

2. **Late chunking is the default**
   - chunk boundaries are derived, not canonical
   - chunk cache is optional and always derived data

3. **Documents are sources, chunks are evidence**
   - UI sources are documents/items
   - DSPy context is chunk-level

4. **SQLAlchemy ORM 2.0+ only**
   - no raw SQL except in narrowly scoped query builders
   - Postgres + pgvector + tsvector is the reference backend

---

## Public Interface

### Retriever Protocol

```python
class Retriever(Protocol):
    async def search(
        self,
        ctx: RequestContext,
        prefs: RetrievalPrefs,
    ) -> RetrievalBundle:
        """
        Perform hybrid retrieval and return ranked candidates and evidence chunks.
        Must be cancellable via ctx.cancellation.
        """
```

The Retriever must:

* respect cancellation
* return deterministic output for the same inputs
* never stream tokens or emit events directly

---

## Input Contract

### RetrievalPrefs

```python
class RetrievalPrefs(BaseModel):
    query_text: str
    filters: dict = {}

    # Candidate sizes
    top_k_items: int = 20
    top_k_chunks: int = 12
    per_item_chunk_cap: int = 3

    # Full-text search
    fts: dict = {
        "mode": "web",          # web | plain | strict | phrase
        "config": None,         # Postgres regconfig, e.g. "english"
        "rank_func": "ts_rank_cd",
        "min_rank": None,
    }

    # Vector search
    vector: dict = {
        "embed_query": True,
        "distance": "cosine",   # cosine | l2 | ip
        "min_score": None,
    }

    # Hybrid scoring
    scoring: dict = {
        "blend": "rrf",         # rrf | linear
        "w_text": 0.35,
        "w_vec": 0.65,
        "normalize": "sigmoid", # minmax | zscore | sigmoid | none
    }

    # Late chunking
    chunking: dict = {
        "strategy": "late",     # late | precomputed | mixed
        "chunker_id": str,
        "include_headers": True,
        "max_chunk_tokens": None,
        "overlap_tokens": None,
    }

    # Chunk cache
    cache: dict = {
        "use_chunk_cache": True,
        "write_chunk_cache": True,
        "ttl_seconds": None,
    }

    # Snippet generation
    snippet: dict = {
        "max_chars": 360,
        "prefer_chunk_snippet": True,
    }

    debug: bool = False
```

---

## Output Contract

### CandidateItem (document-level)

```python
class CandidateItem(BaseModel):
    item_id: str
    kind: str
    source: str
    source_ref: str | None

    title: str | None
    summary: str | None
    metadata: dict = {}

    score: float
    score_text: float | None
    score_vec: float | None
    rank_text: int | None
    rank_vec: int | None

    snippet: str | None
    snippet_from: str           # doc | chunk | unknown
```

These map directly to `rag.sources`.

---

### EvidenceChunk (chunk-level)

```python
class EvidenceChunk(BaseModel):
    item_id: str
    chunk_id: str | None

    text: str
    start_idx: int | None
    end_idx: int | None
    token_count: int | None

    score: float
    score_text: float | None
    score_vec: float | None

    heading_path: list[str] | None
    anchors: dict | None
```

These are fed into DSPy synthesis only.
They are **not** UI artifacts.

---

### RetrievalStats

```python
class RetrievalStats(BaseModel):
    timing_ms: dict
    counts: dict
    params: dict
```

Stats are optional and surfaced via `rag.debug` only when enabled.

---

### RetrievalBundle

```python
class RetrievalBundle(BaseModel):
    candidates: list[CandidateItem]
    evidence: list[EvidenceChunk]
    stats: RetrievalStats
```

---

## Hybrid Retrieval Strategy

### tsquery generation

The Retriever converts `query_text` to a Postgres `tsquery`:

| fts.mode | Function             |
| -------- | -------------------- |
| web      | websearch_to_tsquery |
| plain    | plainto_tsquery      |
| phrase   | phraseto_tsquery     |
| strict   | to_tsquery           |

`websearch_to_tsquery` is the default and recommended mode.

---

### Candidate recall (document-level)

Two supported strategies:

#### Strategy A (preferred v0.1): Dual query + fusion

1. FTS query → top K by `ts_rank_cd`
2. Vector query → top K by similarity
3. Fuse rankings using:

   * Reciprocal Rank Fusion (default), or
   * Linear weighted blend

#### Strategy B (optional optimization)

Single SQL query computing both scores and blending inline.

---

### Ranking fusion

**RRF (default)**

```
score = 1 / (k + rank_text) + 1 / (k + rank_vec)
```

Advantages:

* robust to score scale differences
* predictable behavior

Linear blending remains available for experimentation.

---

## Late Chunking Pipeline

For each candidate document:

1. Obtain full document text
2. Retrieve or generate chunks using ChunkerRegistry
3. Embed chunks (cache if enabled)
4. Score chunks (vector similarity dominant)
5. Select top N chunks per document
6. Pool and globally rank chunks
7. Return top `top_k_chunks`

Chunks are **derived data** and may be cached, but are never canonical.

---

## Chunk Cache Rules

Chunk cache keys must include:

* item_id
* content_hash or version
* chunker_id
* embedding_model_id

Cache:

* is optional
* must be invalidated on content change
* must never be trusted as authoritative

---

## Repository Boundaries

The Retriever coordinates but does not own:

* ItemRepo (SQLAlchemy ORM)
* ChunkCacheRepo (SQLAlchemy ORM)
* Embedder (provider adapter)
* Chunker (pure Python)
* HybridScorer (pure Python)

This prevents monolithic retrieval logic.

---

## Event Mapping (via Orchestrator)

| Retriever output | UI event          |
| ---------------- | ----------------- |
| candidates       | rag.sources       |
| stats (debug)    | rag.debug         |
| evidence         | DSPy context only |

The Retriever never emits events directly.

---

## Design Invariants

* Hybrid search is always used when retrieval is invoked
* Late chunking is default
* Documents are UI sources; chunks are synthesis evidence
* SQLAlchemy ORM 2.0+ only
* No DSPy logic inside the Retriever
* No UI concerns inside the Retriever

---

## Implementation Note for Codex

Implement:

* data models
* Protocol
* stub HybridScorer
* stub ChunkerRegistry
* empty retrieval returning no candidates

Leave TODOs for:

* SQLAlchemy hybrid query
* tsquery construction
* chunk embedding
* cache wiring

---




