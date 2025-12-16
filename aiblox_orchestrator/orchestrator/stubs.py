from __future__ import annotations

import asyncio
from typing import AsyncIterator

from aiblox_orchestrator.orchestrator.interfaces import (
    AgentResult,
    AgentRunner,
    DSPyRuntime,
    ToolResult,
    ToolRunner,
    Validator,
    ValidationResult,
)
from aiblox_orchestrator.protocol.context import RequestContext, UserInput
from aiblox_orchestrator.retriever.models import RetrievalBundle


class FakeDSPyRuntime(DSPyRuntime):
    """Stub runtime that streams back the user input as tokens."""

    async def stream_answer(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        retrieval: RetrievalBundle | None = None,
        tool_results: list[ToolResult] | None = None,
    ) -> AsyncIterator[str]:
        text = user_input.text or ""
        for token in text.split():
            await asyncio.sleep(0.01)
            yield f"{token} "


class StubToolRunner(ToolRunner):
    async def call(self, ctx: RequestContext, step_params: dict) -> ToolResult:
        await asyncio.sleep(0)
        return ToolResult(tool_name=step_params.get("tool") or "stub_tool", output={"echo": True}, success=True)


class StubAgentRunner(AgentRunner):
    async def run(self, ctx: RequestContext, step_params: dict) -> AgentResult:
        await asyncio.sleep(0)
        return AgentResult(agent_name="stub_agent", output={"note": "agent run placeholder"}, success=True)


class StubValidator(Validator):
    async def validate(self, ctx: RequestContext, step_params: dict) -> ValidationResult:
        await asyncio.sleep(0)
        return ValidationResult(success=True, details={"note": "validation stub"})
