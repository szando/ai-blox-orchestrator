from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

from aiblox_orchestrator.orchestrator.errors import RequiredStepFailed
from aiblox_orchestrator.orchestrator.interfaces import AgentResult, AgentRunner, DSPyRuntime, ToolResult, ToolRunner, Validator
from aiblox_orchestrator.protocol.context import RequestContext, UserInput
from aiblox_orchestrator.protocol.plans import PlanStep
from aiblox_orchestrator.retriever.models import CandidateItem, RetrievalBundle, RetrievalPrefs
from aiblox_orchestrator.retriever.protocols import Retriever


@dataclass
class StepState:
    retrieval: Optional[RetrievalBundle] = None
    tool_results: List[ToolResult] = field(default_factory=list)
    agent_results: List[AgentResult] = field(default_factory=list)
    results_payload: dict = field(default_factory=dict)


class StepRunner:
    """Runs individual ExecutionPlan steps."""

    def __init__(
        self,
        retriever: Retriever,
        dspy_runtime: DSPyRuntime,
        tool_runner: ToolRunner,
        agent_runner: AgentRunner,
        validator: Validator,
    ) -> None:
        self.retriever = retriever
        self.dspy_runtime = dspy_runtime
        self.tool_runner = tool_runner
        self.agent_runner = agent_runner
        self.validator = validator

    async def run_step(
        self,
        ctx: RequestContext,
        step: PlanStep,
        user_input: UserInput,
        state: StepState,
        emit,
    ) -> str:
        kind = step.kind
        if kind == "retrieve":
            return await self._run_retrieve(ctx, step, user_input, state, emit)
        if kind == "tool_call":
            return await self._run_tool_call(ctx, step, state)
        if kind == "agent_run":
            return await self._run_agent_run(ctx, step, state)
        if kind == "validate":
            return await self._run_validate(ctx, step)
        if kind == "synthesize":
            return await self._run_synthesize(ctx, user_input, state, emit)
        if kind == "emit_results":
            await emit("rag.results", step.params or {})
            return "completed"
        if kind == "finalize":
            return "completed"
        return "skipped"

    async def _run_retrieve(
        self,
        ctx: RequestContext,
        step: PlanStep,
        user_input: UserInput,
        state: StepState,
        emit,
    ) -> str:
        prefs_data = step.params.get("retrieval_prefs", {}) if step.params else {}
        if "query_text" not in prefs_data:
            prefs_data["query_text"] = user_input.text
        prefs = RetrievalPrefs(**prefs_data)
        bundle = await self.retriever.search(ctx, prefs)
        state.retrieval = bundle
        await emit("rag.sources", {"sources": self._pack_sources(bundle)})
        return "completed"

    async def _run_tool_call(self, ctx: RequestContext, step: PlanStep, state: StepState) -> str:
        result = await self.tool_runner.call(ctx, step.params or {})
        state.tool_results.append(result)
        return "completed" if result.success else "failed"

    async def _run_agent_run(self, ctx: RequestContext, step: PlanStep, state: StepState) -> str:
        result = await self.agent_runner.run(ctx, step.params or {})
        state.agent_results.append(result)
        return "completed" if result.success else "failed"

    async def _run_validate(self, ctx: RequestContext, step: PlanStep) -> str:
        validation = await self.validator.validate(ctx, step.params or {})
        return "completed" if validation.success else "failed"

    async def _run_synthesize(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        state: StepState,
        emit,
    ) -> str:
        tokens: List[str] = []
        async for token in self.dspy_runtime.stream_answer(
            ctx=ctx,
            user_input=user_input,
            retrieval=state.retrieval,
            tool_results=state.tool_results,
        ):
            if ctx.cancelled():
                raise asyncio.CancelledError()
            tokens.append(token)
            await emit("rag.token", {"token": token})
        if tokens:
            await emit("rag.message", {"message": "".join(tokens)})
        return "completed"

    def _pack_sources(self, bundle: RetrievalBundle | None) -> List[dict]:
        if not bundle:
            return []
        sources: List[dict] = []
        for idx, cand in enumerate(bundle.candidates):
            sources.append(
                {
                    "source_id": cand.item_id,
                    "kind": cand.kind,
                    "title": cand.title,
                    "url": cand.source_ref,
                    "snippet": cand.snippet,
                    "snippet_from": cand.snippet_from,
                    "score": cand.score,
                    "rank": idx + 1,
                }
            )
        return sources
