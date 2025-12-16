# AI Blox Block: DSPy Action Orchestrator Backend (RAG-Centered)

## Purpose
This repository implements the AI Blox backend block that powers conversational AI workflows for multiple products.
Its primary job is to process a conversational request and stream events to a UI. It is **RAG-centered** (RAG provides grounding/informedness), but it is **not RAG-only**:
- Some requests are **chat-only** (no retrieval)
- Some requests are **tool/agent augmented** (MCP/tools, DSPy agents)
- Many requests are **hybrid** (RAG + tools/agents + synthesis)

The module is designed to be:
- product-agnostic
- UI-agnostic
- transport-agnostic (Phase 1 uses WebSocket)
- contract-stable

Codex should implement structure and interfaces first; business logic can be filled in iteratively.

## Non-goals (Phase 1)
- UI rendering/layout responsibility
- persistence beyond session scope (unless explicitly added later)
- multi-agent orchestration as a platform feature (single-request orchestration only)
- billing/multi-tenant org features

## Transport & Streaming Contract (UI-facing)
Phase 1 transport: **WebSocket** UI → backend.

Backend emits a **sequence of events**, not a single response object. Events are tied to `request_id`.

Event types:
- Lifecycle: `rag.started`, `rag.done`, `rag.error`
- Conversational output: `rag.token`, optional `rag.message`
- Retrieval evidence: `rag.sources` (emitted only when retrieval happens)
- Domain results: `rag.results` with `kind` hint
- Debug: `rag.debug` (optional)
- Layout hints: `rag.layout` (optional/advisory)

Cancellation:
- UI can send `rag.cancel { request_id }`
- Backend must stop processing and emit `rag.done { status: "cancelled" }` (preferred)

Payload guidance:
- Prefer many small events (token streaming).
- Do not send large blobs in-band; use IDs/URLs.

## Core Principle: Informed Action
Every action/output should be based on informed decisions.
RAG is the primary grounding mechanism, but the backend may choose:
- chat-only (no lookup)
- retrieval + synthesis
- tool/agent + synthesis
- retrieval + tool/agent + synthesis

## Architectural Overview (Component Breakdown)
### 1) WebSocket Gateway
- Authenticates/binds user context to connection/session
- Receives `rag.request`, `rag.cancel`
- Sends events via EventSink (adds `request_id`, `seq`, timestamps)

### 2) Decision Router
- Produces an **ExecutionPlan** (mode + ordered steps)
- Pure planning: no DB access, no tool calls, no token streaming

### 3) Orchestrator
- Runs the plan step-by-step
- Owns cancellation, timeouts, error handling
- Emits events at stage boundaries
- Coordinates capabilities (Retriever, ToolRunner/AgentRunner, DSPyRuntime, Validator)

### 4) Chunker Registry
- Manages reusable chunkers (late chunking)
- Chunkers have stable IDs (config-hashable)

### 5) Retriever
- Hybrid retrieval is mandatory when used:
  - vector similarity + `tsvector` full-text
  - **tsquery support** with default `websearch_to_tsquery`
- Supports **late chunking**:
  - doc-level recall, then chunk-level rerank within top docs
  - optional chunk cache

### 6) Evidence Packer
- Converts retrieval outputs into `rag.sources` items
- Groups by document/item, chooses snippets
- No large in-band content

### 7) DSPy Runtime
- Streams assistant tokens
- May emit structured outputs for `rag.results`
- May support tool routing / agent loops (still internal)

### 8) Result Builder Registry
- Produces `rag.results` payloads with `kind` hints:
  - `jobs|documents|entities|graph|custom`
- UI decides how to render; backend only provides structured data

### 9) Storage Layer (SQLAlchemy 2.0 ORM only)
- Postgres reference backend with pgvector and tsvector
- No raw SQL outside narrowly scoped query builders (if needed)

### 10) Observability Layer
- MLflow integration is **optional** and must not be required for correctness
- Use MLflow for tracing/experiments (Option B), but do not build the system around it

## Invariants / Constraints
- SQLAlchemy ORM 2.0+ only
- Hybrid search uses tsvector + tsquery + vector embeddings
- Late chunking is preferred; chunk cache is allowed
- Streaming is first-class; do not buffer full responses before emitting
- Never leak DSPy chain-of-thought; only emit safe debug metadata if enabled

## Data Model Direction (conceptual)
We generalize documents into a canonical searchable record with extensible metadata.
At minimum we will support:
- document/item records with metadata + tsvector
- embeddings (doc-level and/or chunk-level)
- chunk cache as optional, derived data

Exact schema will be refined, but code should be written to allow:
- item-level recall, chunk-level evidence selection

## Execution Plan and Contracts (v0.1)

### RequestContext (concept)
Contains: request_id, trace_id, user_id, conversation_id, turn_id, locale, timezone, cancellation token, flags/quotas.

### ExecutionPlan
- `mode`: chat | rag | tool | hybrid
- steps: PlanStep[] with dependencies

### PlanStep types
- decide, retrieve, tool_call, agent_run, validate, synthesize, emit_results, finalize

### DecisionRouter interface (sync)
`route(ctx, user_input, conversation_window, product_profile) -> ExecutionPlan`

### Orchestrator interface (async)
`run(ctx, user_input, conversation_window, product_profile, event_sink) -> None`

Orchestrator must always emit:
- `rag.started` at beginning
- `rag.done` at end (ok/cancelled/error)
- `rag.error` on failures (then `rag.done {status:"error"}`)

## Implementation Guidance for Codex
Implement the skeleton first:
- data models (Pydantic)
- Router with simple heuristics (chat vs rag vs tool) behind feature flags
- Orchestrator step runner with cancellation support
- WS gateway that wires `rag.request` to orchestrator and streams events

Leave TODOs for:
- Retriever internals (hybrid + tsquery + late chunking + cache)
- ToolRunner/AgentRunner connectors
- MLflow wiring (behind config)
