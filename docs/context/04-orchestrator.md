# AI Blox – Orchestrator Design (v0.1)

## Role of the Orchestrator

The Orchestrator is the **execution engine** of the AI Blox Orchestrator backend.

It is responsible for:
- executing an ExecutionPlan step-by-step
- coordinating capabilities (Retriever, Chunker, Evidence Packer, DSPy Runtime, Tools)
- emitting streaming events to the UI
- handling cancellation, errors, and partial failures

The Orchestrator is:
- stateful per request
- event-driven
- streaming-first

The Orchestrator is **not**:
- a planner (that is the Decision Router)
- a retriever
- a chunker
- a renderer
- a UI state manager

---

## Core Principles

1. **Plans, not branches**
   - The Orchestrator executes an explicit ExecutionPlan
   - No hidden conditional logic based on “mode”

2. **Streaming is mandatory**
   - Tokens and results are emitted incrementally
   - No buffering full responses before emitting

3. **Cancellation is first-class**
   - Cancellation can occur at any step
   - Cleanup is mandatory
   - A cancelled request must terminate cleanly

4. **Partial failure tolerance**
   - Optional steps may fail without aborting the plan
   - Required steps abort execution on failure

5. **Event protocol stability**
   - Orchestrator is the single authority for emitting UI events
   - Event semantics must remain stable

---

## Orchestrator Interface

```python
class Orchestrator(Protocol):
    async def run(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        conversation: ConversationWindow,
        product_profile: ProductProfile,
        event_sink: EventSink,
    ) -> None:
        """
        Execute a request and emit streaming events.
        Must always terminate with rag.done.
        """
```

---

## Execution Model

### High-level algorithm

1. Emit `rag.started`
2. Call DecisionRouter to obtain ExecutionPlan
3. (Optional) emit `rag.debug` with plan summary
4. Execute plan steps in dependency order
5. Emit events during step execution
6. On completion, emit `rag.done`
7. On cancellation or error, emit appropriate termination events

---

## Step Execution Semantics

### Step lifecycle

Each `PlanStep` goes through:

1. **Pending**
2. **Running**
3. **Completed** or **Failed**

The Orchestrator must:

* respect `depends_on`
* skip steps whose dependencies failed (unless optional)
* never run the same step twice

---

## Supported Step Types (v0.1)

### `retrieve`

* Calls Retriever.search(...)
* On success:

  * store RetrievalBundle
  * call EvidencePacker
  * emit `rag.sources`
* On failure:

  * abort if required
  * continue if optional

---

### `tool_call`

* Calls ToolRunner.call(...)
* Stores ToolResult
* Emits `rag.debug` (optional)

---

### `agent_run`

* Calls AgentRunner.run(...)
* May involve internal loops
* Orchestrator treats as a single step

---

### `validate`

* Calls Validator.validate(...)
* Failure aborts if required

---

### `synthesize`

* Calls DSPyRuntime.stream_answer(...)
* Streams:

  * `rag.token` for each token
* Optionally emits:

  * `rag.message` at end (aggregated)

If synthesis is skipped or empty:

* Orchestrator may still emit `rag.done`

---

### `emit_results`

* Emits `rag.results`
* Payload provided by previous steps

---

### `finalize`

* Cleanup step
* No events required except termination

---

## Cancellation Semantics

### Trigger

* UI emits `rag.cancel { request_id }`
* Cancellation token is set in RequestContext

### Behavior

* Orchestrator must:

  * stop active step
  * stop token streaming
  * clean up resources
  * emit `rag.done { status:"cancelled" }`

### Rules

* Cancellation is not an error
* `rag.error` is optional for cancellation (prefer not emitting it)

---

## Error Handling

### Required steps

* Failure emits:

  * `rag.error`
  * followed by `rag.done { status:"error" }`
* Execution stops

### Optional steps

* Failure is logged
* Execution continues
* Error may be surfaced via `rag.debug`

---

## Event Emission Rules

### Ordering

* Events must be emitted in causal order
* Each event includes:

  * request_id
  * seq (monotonic)
  * ts (server timestamp)

### Event Types

* Lifecycle: `rag.started`, `rag.done`, `rag.error`
* Streaming: `rag.token`, `rag.message`
* Retrieval: `rag.sources`
* Results: `rag.results`
* Debug: `rag.debug`
* Layout hints: `rag.layout` (optional)

The Orchestrator is the **only** component allowed to emit UI events.

---

## Backpressure & Flow Control (v0.1)

* Token streaming should yield control regularly
* Orchestrator should await event_sink.emit(...)
* No unbounded buffering
* Advanced flow control may be added later

---

## Observability Hooks

* Orchestrator should:

  * create a trace_id per request
  * optionally attach MLflow spans per step
* Observability must never affect correctness

---

## Design Invariants

* Always emit `rag.started` and `rag.done`
* Never emit UI events from non-orchestrator components
* Never leak DSPy chain-of-thought
* Never block cancellation
* ExecutionPlan is the single source of truth

---

## Implementation Notes for Codex

Implement:

* Orchestrator class
* Step execution loop
* Dependency resolution
* Cancellation checks
* Event sequencing

Stub:

* ToolRunner
* AgentRunner
* Validator
* DSPyRuntime (if not already implemented)

Unit tests should cover:

* simple chat-only plan
* retrieve + synthesize plan
* cancellation mid-stream
* optional step failure
* required step failure

