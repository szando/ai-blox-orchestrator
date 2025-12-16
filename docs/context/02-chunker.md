# AI Blox – Chunker & ChunkerRegistry Design (v0.1)

## Role of Chunking in AI Blox

Chunking is a **retrieval primitive** used by the Retriever (and optionally ingestion),
not a UI or DSPy concern.

AI Blox defaults to **late chunking**:
- documents/items are stored as canonical text
- chunks are derived on demand using a selected chunker
- chunk boundaries are not treated as canonical truth

Chunkers must therefore be:
- **reusable** (avoid instantiation overhead per call)
- **stable** (same config produces same boundaries)
- **identifiable** (via a stable `chunker_id`)
- **pluggable** (multiple strategies can coexist)

This module defines:
- `Chunker` protocol
- chunk data types
- `ChunkerRegistry` contract and lifecycle expectations

---

## Core Principles

1. **Chunkers are first-class, reusable objects**
   - avoid creating new chunkers per request
   - allow internal caching (tokenizer, compiled regexes, etc.)

2. **Chunker identity is stable**
   - every chunker is addressed by `chunker_id`
   - `chunker_id` must uniquely represent the configuration

3. **Determinism**
   - given the same input text and options, chunking output must be deterministic

4. **Token-aware (preferred), char-based fallback**
   - token-based chunking aligns with LLM context usage
   - char-based chunking may exist as fallback for early versions

5. **No domain assumptions**
   - chunkers should work for Jira tickets, Confluence pages, PDFs (post-extraction),
     job postings, notes, etc.

---

## Public Data Types

### Chunk

A chunk is a derived segment of a document, with optional structure.

```python
class Chunk(BaseModel):
    chunk_index: int

    text: str

    # Optional location hints within the original document
    start_idx: int | None = None
    end_idx: int | None = None

    # Optional token count if tokenization is available
    token_count: int | None = None

    # Optional structure hints (useful for evidence)
    heading_path: list[str] | None = None
    anchors: dict | None = None
```

Notes:

* `start_idx/end_idx` are best-effort, not guaranteed for all chunkers.
* `heading_path/anchors` are optional; chunkers may ignore.

---

## Chunking Options

Chunkers accept options that tune boundaries.
These may be partially ignored depending on implementation capability.

```python
class ChunkingOptions(BaseModel):
    include_headers: bool = True

    # Preferred token-based controls
    max_chunk_tokens: int | None = None
    overlap_tokens: int | None = None

    # Fallback char-based controls (optional)
    max_chunk_chars: int | None = None
    overlap_chars: int | None = None

    # Future: allow strategy hints like "semantic" or "sentence"
    strategy: str | None = None
```

---

## Chunker Protocol

Chunker is a reusable object.
Instantiation is allowed to be “expensive”.

```python
class Chunker(Protocol):
    chunker_id: str

    def chunk(
        self,
        text: str,
        options: ChunkingOptions,
    ) -> list[Chunk]:
        """
        Split text into deterministic chunks.

        Must:
        - be deterministic for same input+options
        - return chunks in document order
        - set chunk_index sequentially
        - never return empty chunks unless explicitly allowed
        """
```

Guidelines:

* chunkers may internally use:

  * tokenizers
  * sentence splitters
  * heading parsers
  * regex structures
* those should live inside the chunker instance and be reused

---

## Chunker Identity

`chunker_id` must uniquely represent chunker configuration, including:

* chunking method name/version
* tokenization mode (if relevant)
* default max tokens/overlap (if baked into chunker)
* any heading/structure awareness configuration

Recommended format:

```
<name>@<version>:<config_hash>
```

Examples:

* `simple@v1:8b31c2`
* `header_aware@v1:2f09aa`
* `token_window@v1:91ac44`

The registry may support aliases:

* `default` → `token_window@v1:...`

---

## ChunkerRegistry

The registry provides:

* reusable instances
* consistent lookups by chunker_id
* a single construction path for chunkers

### Registry Protocol

```python
class ChunkerRegistry(Protocol):
    def get(self, chunker_id: str) -> Chunker:
        """
        Return a reusable Chunker instance by id.
        Must raise a clear error if not found.
        """

    def has(self, chunker_id: str) -> bool: ...

    def list_ids(self) -> list[str]: ...
```

### Lifecycle Expectations

* Registry is created at application startup.
* Chunkers are created lazily on first access OR eagerly at startup.
* Instances are reused across requests.
* Registry must be safe for concurrent requests:

  * either chunkers are thread-safe
  * or registry returns per-thread/per-task instances
  * Phase 1 may assume async single-process, but design must not break concurrency.

Implementation guidance:

* simplest v0.1: registry stores singleton chunker instances and chunkers are pure/deterministic
* if a chunker uses non-thread-safe tokenizers, wrap with internal locks or per-task clones

---

## Required Chunker Implementations (v0.1)

Codex should implement at least these chunkers:

### 1) `SimpleCharChunker`

* splits on characters (with overlap)
* deterministic
* used as fallback

### 2) `SimpleTokenLikeChunker` (v0.1 baseline for late chunking)

* approximates tokens via whitespace splitting (token-like units)
* supports max_chunk_tokens and overlap_tokens
* deterministic
* clearly marked TODO for real tokenizer integration

Both should:

* produce Chunk objects
* set token_count if possible

---

## Integration with Retriever (late chunking)

Retriever uses:

* `chunker = registry.get(prefs.chunking.chunker_id)`
* `chunks = chunker.chunk(item.content_text, options)`

Chunks then:

* may be embedded
* may be cached (chunk cache is derived data)
* top chunks become `EvidenceChunk` for DSPy synthesis

Chunkers must not:

* know about embeddings
* know about caching
* know about UI sources

---

## Design Invariants

* Chunkers are reusable objects (not per-call functions)
* Chunker identity is stable (`chunker_id`)
* Output is deterministic and ordered
* Token-aware options exist even if early implementations approximate tokens
* No product-specific logic in chunkers
* No DSPy / UI logic in chunkers

---

## Implementation Notes for Codex

Implement:

* Pydantic models: Chunk, ChunkingOptions
* Protocols: Chunker, ChunkerRegistry
* Registry with:

  * alias support (e.g. "default")
  * clear errors on missing ids
* Two chunkers:

  * SimpleCharChunker
  * SimpleTokenLikeChunker

Unit tests must cover:

* determinism (same input/options → same output)
* boundaries (no empty chunks)
* overlap correctness
* chunk_index sequence correctness

Leave TODO markers for:

* real tokenizer integration (tiktoken / HF tokenizers etc.)
* header-aware chunking
* semantic/sentence chunking strategies
