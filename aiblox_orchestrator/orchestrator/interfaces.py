from __future__ import annotations

from typing import AsyncIterator, Protocol

from pydantic import BaseModel, Field

from aiblox_orchestrator.protocol.context import RequestContext, UserInput
from aiblox_orchestrator.retriever.models import RetrievalBundle
from aiblox_orchestrator.retriever.protocols import Retriever


class ToolResult(BaseModel):
    tool_name: str
    output: dict = Field(default_factory=dict)
    success: bool = True


class AgentResult(BaseModel):
    agent_name: str
    output: dict = Field(default_factory=dict)
    success: bool = True


class ValidationResult(BaseModel):
    success: bool = True
    details: dict = Field(default_factory=dict)


class DSPyRuntime(Protocol):
    async def stream_answer(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        retrieval: RetrievalBundle | None = None,
        tool_results: list[ToolResult] | None = None,
    ) -> AsyncIterator[str]:
        ...


class ToolRunner(Protocol):
    async def call(self, ctx: RequestContext, step_params: dict) -> ToolResult:
        ...


class AgentRunner(Protocol):
    async def run(self, ctx: RequestContext, step_params: dict) -> AgentResult:
        ...


class Validator(Protocol):
    async def validate(self, ctx: RequestContext, step_params: dict) -> ValidationResult:
        ...
