# AI Blox Orchestrator – Context Index

This directory contains the **authoritative architectural context** for the
**AI Blox Orchestrator** backend module.

These documents define:
- the purpose of the module
- its responsibilities and non-goals
- stable interfaces and contracts
- design invariants and constraints

They are written to be read by both humans and code-generation tools (e.g. Codex).

**All implementations in this repository must conform to these documents.**

---

## Reading Order (important)

Implementers should read these files in order:

1. **00-context.md**  
   High-level purpose, system boundaries, UI-facing contract, core principles,
   component overview, and global invariants.

2. **01-retriever.md**  
   Detailed design of the Retriever capability:
   hybrid search (vector + full-text), tsquery usage, late chunking,
   chunk cache rules, and retrieval contracts.

3. **02-chunker.md**  
   Chunker and ChunkerRegistry contracts, reusable chunkers, token-aware chunking,
   and late-chunking mechanics.

4. **03-evidence-packer.md**  
   Rules for converting retrieval output into UI-facing `rag.sources`
   and internal DSPy evidence structures.

5. **04-orchestrator.md**  
   Execution engine internals: step scheduling, cancellation, partial failures,
   streaming semantics, and event emission guarantees.

6. **05-db.md**  
   Database design and persistence layer decisions:
   schema awareness (`kb`), UUID-based identifiers, late-chunk cache schema,
   dependency-injected async session handling, and Alembic migration strategy.

7. **06-packaging.md**  
   Workspace and packaging strategy:
   root-is-runtime uv workspace, KB contract extraction into `aiblox_kb`,
   dependency rules, migration ownership, and versioning boundaries.

8. **07-item-repo.md**
   Minimal KB write/read contract:
   ownership rules, idempotent ingestion semantics,
   and full-text search guarantees.


---

## Design Vocabulary (stable)

The following terms are **deliberately defined and must be used consistently**
in code, documentation, and module names:

- **Orchestrator** – Executes an ExecutionPlan and emits events
- **Decision Router** – Produces an ExecutionPlan from user input and context
- **Execution Plan** – Ordered steps describing how a request is processed
- **Retriever** – Hybrid retrieval capability (documents + evidence chunks)
- **Chunker / ChunkerRegistry** – Reusable chunking logic for late chunking
- **Evidence Packer** – Prepares retrieval results for UI consumption
- **DSPy Runtime** – Internal synthesis and reasoning engine
- **CandidateItem** – Document-level retrieval result (UI source)
- **EvidenceChunk** – Chunk-level retrieval result (DSPy context)

These concepts should be reflected directly in:
- package and module names
- class names
- interface names

Avoid introducing synonymous terms.

---

## Architectural Invariants (TL;DR)

- This module is an **Action Orchestrator**, not “just RAG”
- RAG is a grounding mechanism, not the end goal
- Streaming, event-driven output is mandatory
- UI consumes events; backend never renders
- Hybrid search is required when retrieval is used
- Late chunking is the default strategy
- SQLAlchemy ORM 2.0+ only
- DSPy internals are never exposed to the UI
- Large content is never sent in-band

If an implementation choice conflicts with any of the above,
the context documents take precedence.

---

## Intended Audience

- Codex (primary implementation engine)
- Human contributors extending or reviewing the backend
- Future maintainers of the AI Blox platform

---

## Change Discipline

- Changes that affect interfaces, contracts, or invariants
  should be reflected by updating these documents.
- Significant or constraining decisions should eventually be
  promoted to Architecture Decision Records (ADRs).

Until then, these context files are the single source of truth.
