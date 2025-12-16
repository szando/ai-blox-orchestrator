import asyncio
from typing import List
from uuid import uuid4

import pytest

from aiblox_orchestrator.orchestrator import Orchestrator, StepRunner
from aiblox_orchestrator.orchestrator.interfaces import AgentResult, DSPyRuntime, ToolResult, ValidationResult
from aiblox_orchestrator.orchestrator.stubs import FakeDSPyRuntime, StubAgentRunner, StubToolRunner, StubValidator
from aiblox_orchestrator.protocol.context import ConversationWindow, ProductProfile, RequestContext, UserInput
from aiblox_orchestrator.protocol.event_sink import EventSink
from aiblox_orchestrator.protocol.events import EventEnvelope
from aiblox_orchestrator.protocol.plans import ExecutionPlan, PlanStep
from aiblox_orchestrator.retriever.models import CandidateItem, RetrievalBundle, RetrievalPrefs
from aiblox_orchestrator.retriever.protocols import Retriever
from aiblox_orchestrator.router.decision_router import DecisionRouter


class CollectingEventSink(EventSink):
    def __init__(self) -> None:
        self.events: List[EventEnvelope] = []

    async def emit(self, event: EventEnvelope) -> None:
        self.events.append(event)


class StubRetriever(Retriever):
    async def search(self, ctx: RequestContext, prefs: RetrievalPrefs) -> RetrievalBundle:
        candidate = CandidateItem(item_id="doc1", kind="doc", source="kb", score=1.0, title="t", summary="s")
        return RetrievalBundle(candidates=[candidate])


class FailingToolRunner(StubToolRunner):
    def __init__(self, success: bool) -> None:
        super().__init__()
        self._success = success

    async def call(self, ctx: RequestContext, step_params: dict) -> ToolResult:
        res = await super().call(ctx, step_params)
        res.success = self._success
        return res


class FailingValidator(StubValidator):
    def __init__(self, success: bool) -> None:
        self._success = success

    async def validate(self, ctx: RequestContext, step_params: dict) -> ValidationResult:
        return ValidationResult(success=self._success)


class SlowDSPyRuntime(DSPyRuntime):
    async def stream_answer(self, ctx: RequestContext, user_input: UserInput, retrieval=None, tool_results=None):
        for token in ["a", "b", "c"]:
            await asyncio.sleep(0.01)
            yield token


def make_orchestrator(step_runner: StepRunner, router: DecisionRouter | None = None) -> Orchestrator:
    router = router or DecisionRouter()
    return Orchestrator(decision_router=router, step_runner=step_runner)


def make_ctx() -> RequestContext:
    return RequestContext(request_id=str(uuid4()))


@pytest.mark.anyio
async def test_chat_only_plan():
    retriever = StubRetriever()
    runner = StepRunner(
        retriever=retriever,
        dspy_runtime=FakeDSPyRuntime(),
        tool_runner=StubToolRunner(),
        agent_runner=StubAgentRunner(),
        validator=StubValidator(),
    )
    orch = make_orchestrator(runner, router=DecisionRouter())
    sink = CollectingEventSink()
    await orch.run(
        ctx=make_ctx(),
        user_input=UserInput(text="hello world", mode="chat"),
        conversation=ConversationWindow(),
        product_profile=ProductProfile(),
        event_sink=sink,
    )
    types = [e.type for e in sink.events]
    assert types[0] == "rag.started"
    assert types[-1] == "rag.done"
    assert any(e.type == "rag.message" for e in sink.events)


@pytest.mark.anyio
async def test_retrieve_then_synthesize():
    retriever = StubRetriever()
    runner = StepRunner(
        retriever=retriever,
        dspy_runtime=FakeDSPyRuntime(),
        tool_runner=StubToolRunner(),
        agent_runner=StubAgentRunner(),
        validator=StubValidator(),
    )
    orch = make_orchestrator(runner, router=DecisionRouter())
    sink = CollectingEventSink()
    await orch.run(
        ctx=make_ctx(),
        user_input=UserInput(text="query text", mode="rag"),
        conversation=ConversationWindow(),
        product_profile=ProductProfile(),
        event_sink=sink,
    )
    types = [e.type for e in sink.events]
    assert "rag.sources" in types
    assert "rag.token" in types
    assert sink.events[-1].payload["status"] == "ok"


@pytest.mark.anyio
async def test_cancellation_mid_stream():
    retriever = StubRetriever()
    runner = StepRunner(
        retriever=retriever,
        dspy_runtime=SlowDSPyRuntime(),
        tool_runner=StubToolRunner(),
        agent_runner=StubAgentRunner(),
        validator=StubValidator(),
    )

    class SingleStepRouter:
        def build_plan(self, *args, **kwargs):
            return ExecutionPlan(plan_id="p", steps=[PlanStep(step_id="s1", kind="synthesize")])

    orch = make_orchestrator(runner, router=SingleStepRouter())
    sink = CollectingEventSink()
    ctx = make_ctx()
    task = asyncio.create_task(
        orch.run(
            ctx=ctx,
            user_input=UserInput(text="cancel me", mode="chat"),
            conversation=ConversationWindow(),
            product_profile=ProductProfile(),
            event_sink=sink,
        )
    )
    await asyncio.sleep(0.02)
    ctx.cancel()
    await task
    assert sink.events[-1].payload["status"] == "cancelled"


@pytest.mark.anyio
async def test_optional_step_failure():
    retriever = StubRetriever()
    runner = StepRunner(
        retriever=retriever,
        dspy_runtime=FakeDSPyRuntime(),
        tool_runner=FailingToolRunner(success=False),
        agent_runner=StubAgentRunner(),
        validator=StubValidator(),
    )

    class Router:
        def build_plan(self, *args, **kwargs):
            return ExecutionPlan(
                plan_id="p",
                steps=[
                    PlanStep(step_id="tool", kind="tool_call", required=False),
                    PlanStep(step_id="syn", kind="synthesize", depends_on=["tool"]),
                ],
            )

    orch = make_orchestrator(runner, router=Router())
    sink = CollectingEventSink()
    await orch.run(
        ctx=make_ctx(),
        user_input=UserInput(text="hi", mode="chat"),
        conversation=ConversationWindow(),
        product_profile=ProductProfile(),
        event_sink=sink,
    )
    assert sink.events[-1].payload["status"] == "ok"


@pytest.mark.anyio
async def test_required_step_failure():
    retriever = StubRetriever()
    runner = StepRunner(
        retriever=retriever,
        dspy_runtime=FakeDSPyRuntime(),
        tool_runner=StubToolRunner(),
        agent_runner=StubAgentRunner(),
        validator=FailingValidator(success=False),
    )

    class Router:
        def build_plan(self, *args, **kwargs):
            return ExecutionPlan(
                plan_id="p",
                steps=[
                    PlanStep(step_id="validate", kind="validate", required=True),
                    PlanStep(step_id="syn", kind="synthesize", depends_on=["validate"]),
                ],
            )

    orch = make_orchestrator(runner, router=Router())
    sink = CollectingEventSink()
    await orch.run(
        ctx=make_ctx(),
        user_input=UserInput(text="hi", mode="chat"),
        conversation=ConversationWindow(),
        product_profile=ProductProfile(),
        event_sink=sink,
    )
    types = [e.type for e in sink.events]
    assert types[-2] == "rag.error"
    assert sink.events[-1].payload["status"] == "error"
