from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List

from aiblox_orchestrator.orchestrator.errors import RequiredStepFailed
from aiblox_orchestrator.orchestrator.step_runner import StepRunner, StepState
from aiblox_orchestrator.protocol.context import ConversationWindow, ProductProfile, RequestContext, UserInput
from aiblox_orchestrator.protocol.event_sink import EventSink
from aiblox_orchestrator.protocol.events import EventEnvelope
from aiblox_orchestrator.protocol.plans import ExecutionPlan
from aiblox_orchestrator.router.decision_router import DecisionRouter


class Orchestrator:
    """Execution engine that runs ExecutionPlans and emits events."""

    def __init__(self, decision_router: DecisionRouter, step_runner: StepRunner) -> None:
        self.decision_router = decision_router
        self.step_runner = step_runner

    async def run(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        conversation: ConversationWindow,
        product_profile: ProductProfile,
        event_sink: EventSink,
    ) -> None:
        seq = 0

        async def emit(event_type: str, payload: dict | None = None) -> None:
            nonlocal seq
            seq += 1
            await event_sink.emit(
                EventEnvelope(
                    type=event_type,
                    request_id=ctx.request_id,
                    seq=seq,
                    payload=payload,
                )
            )

        await emit("rag.started", {"status": "running"})

        try:
            plan = self.decision_router.build_plan(
                ctx=ctx,
                user_input=user_input,
                conversation=conversation,
                product_profile=product_profile,
            )
            await self._execute_plan(ctx, plan, user_input, emit)
            await emit("rag.done", {"status": "ok"})
        except asyncio.CancelledError:
            await emit("rag.done", {"status": "cancelled"})
        except RequiredStepFailed as exc:
            await emit("rag.error", {"message": str(exc), "step_id": exc.step_id})
            await emit("rag.done", {"status": "error"})
        except Exception as exc:  # noqa: BLE001
            await emit("rag.error", {"message": str(exc)})
            await emit("rag.done", {"status": "error"})

    async def _execute_plan(
        self,
        ctx: RequestContext,
        plan: ExecutionPlan,
        user_input: UserInput,
        emit,
    ) -> None:
        statuses: Dict[str, str] = {}
        required_map: Dict[str, bool] = {step.step_id: step.required for step in plan.steps}
        state = StepState()

        for step in plan.steps:
            if ctx.cancelled():
                raise asyncio.CancelledError()
            if not self._dependencies_satisfied(step, statuses, required_map):
                statuses[step.step_id] = "skipped"
                continue

            status = await self.step_runner.run_step(ctx, step, user_input, state, emit)
            statuses[step.step_id] = status
            if status == "failed" and step.required:
                raise RequiredStepFailed(step.step_id)

    def _dependencies_satisfied(self, step, statuses: Dict[str, str], required_map: Dict[str, bool]) -> bool:
        if not step.depends_on:
            return True
        for dep in step.depends_on:
            if dep not in statuses:
                return False
            if statuses[dep] == "failed" and required_map.get(dep, True):
                return False
        return True
