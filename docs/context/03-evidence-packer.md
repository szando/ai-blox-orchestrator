# AI Blox – Evidence Packer Design (v0.1)

## Role of the Evidence Packer

The Evidence Packer is responsible for transforming **retrieval output**
into **UI-facing source artifacts**.

It sits between:
- the **Retriever** (which finds candidates and evidence chunks)
- the **Orchestrator** (which emits UI events)

The Evidence Packer:
- does NOT perform retrieval
- does NOT perform chunking
- does NOT generate assistant text
- does NOT render UI

Its sole responsibility is:
> Turn retrieval results into clean, stable `rag.sources` payloads.

---

## Core Principles

1. **Documents are sources**
   - UI sources correspond to document-level `CandidateItem`s
   - Chunks are never UI-visible

2. **Sources are evidence, not answers**
   - They justify or ground assistant output
   - They are not conversational messages

3. **Stable, minimal payloads**
   - Small snippets
   - IDs and URLs instead of full content
   - No large blobs in-band

4. **Product-agnostic**
   - Job ads, wiki pages, tickets, notes all follow the same rules
   - Rendering decisions belong to the UI

5. **Deterministic output**
   - Same retrieval input → same sources output
   - Important for reproducibility and debugging

---

## Inputs

The Evidence Packer consumes:

- `CandidateItem[]` (document-level retrieval output)
- optionally `EvidenceChunk[]` (for snippet selection)
- `EvidencePackOptions` (limits, formatting hints)

It does **not** see:
- DSPy internals
- execution plans
- UI layout state

---

## EvidencePackOptions

```python
class EvidencePackOptions(BaseModel):
    max_sources: int = 6

    # Snippet selection
    prefer_chunk_snippets: bool = True
    max_snippet_chars: int = 360

    # Metadata exposure
    include_metadata_keys: list[str] | None = None
    exclude_metadata_keys: list[str] | None = None

    # Ordering
    order_by: Literal["score", "rank", "input"] = "score"

    debug: bool = False
```

Notes:

* `max_sources` limits UI clutter.
* Metadata exposure is explicitly controlled to avoid accidental leakage.

---

## Output Contract

### SourceItem (UI-facing)

```python
class SourceItem(BaseModel):
    source_id: str              # stable id (maps to CandidateItem.item_id)
    kind: str                   # documents | jobs | entities | custom
    title: str | None
    url: str | None

    snippet: str | None
    snippet_from: str           # doc | chunk | unknown

    score: float | None
    rank: int | None

    metadata: dict = {}
```

These objects map **directly** to `rag.sources.payload.sources[]`.

---

## EvidencePacker Interface

```python
class EvidencePacker(Protocol):
    def pack(
        self,
        candidates: list[CandidateItem],
        evidence_chunks: list[EvidenceChunk] | None,
        options: EvidencePackOptions,
    ) -> list[SourceItem]:
        """
        Convert retrieval output into UI-facing sources.
        Must be deterministic.
        """
```

---

## Packing Algorithm (v0.1)

### Step 1: Candidate selection

* Start from `candidates`
* Apply ordering:

  * default: by descending `CandidateItem.score`
* Take top `options.max_sources`

### Step 2: Snippet selection

For each selected candidate:

1. If `prefer_chunk_snippets` and matching `EvidenceChunk`s exist:

   * choose the highest-scoring chunk for that item
   * truncate to `max_snippet_chars`
   * mark `snippet_from="chunk"`
2. Else:

   * fall back to candidate-level summary or content preview
   * mark `snippet_from="doc"`
3. Else:

   * snippet may be `None`
   * mark `snippet_from="unknown"`

### Step 3: Metadata filtering

* If `include_metadata_keys` is set:

  * only include those keys
* If `exclude_metadata_keys` is set:

  * remove those keys
* Otherwise:

  * include metadata as-is (safe subset only)

### Step 4: Rank assignment

* Assign `rank` based on final ordering (1-based)

---

## Ordering Semantics

* `order_by="score"`:

  * use `CandidateItem.score`
* `order_by="rank"`:

  * use retrieval rank (if available)
* `order_by="input"`:

  * preserve incoming candidate order

Default is `"score"`.

---

## Error Handling

* Missing titles or URLs are allowed.
* Missing snippets are allowed.
* Evidence Packer must **never raise** for missing optional data.
* Invalid inputs should result in:

  * empty source list
  * optional debug output (if enabled)

---

## Integration with Orchestrator

The Orchestrator:

1. calls Retriever
2. calls EvidencePacker.pack(...)
3. emits:

```json
{
  "type": "rag.sources",
  "payload": {
    "sources": [ SourceItem, ... ]
  }
}
```

The Evidence Packer does not emit events itself.

---

## Design Invariants

* Sources are document-level, never chunk-level
* No DSPy logic
* No retrieval logic
* No UI rendering logic
* No large content in-band
* Deterministic output

---

## Implementation Notes for Codex

Implement:

* Pydantic models: SourceItem, EvidencePackOptions
* EvidencePacker Protocol
* DefaultEvidencePacker implementation
* Unit tests:

  * chunk-snippet preference
  * doc fallback
  * metadata include/exclude
  * ordering correctness
  * determinism

Leave TODOs for:

* richer snippet heuristics
* multi-snippet per source (future)
* citation anchoring (future)
