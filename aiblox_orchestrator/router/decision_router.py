from __future__ import annotations

import uuid
from typing import List

from aiblox_orchestrator.protocol.context import ConversationWindow, ProductProfile, RequestContext, UserInput
from aiblox_orchestrator.protocol.plans import ExecutionPlan, PlanStep


class DecisionRouter:
    """Deterministic, minimal router producing ExecutionPlans."""

    def build_plan(
        self,
        ctx: RequestContext,
        user_input: UserInput,
        conversation: ConversationWindow,
        product_profile: ProductProfile,
    ) -> ExecutionPlan:
        mode = (user_input.mode or "chat").lower()
        steps: List[PlanStep]

        if mode == "rag":
            steps = [
                PlanStep(
                    step_id="retrieve",
                    kind="retrieve",
                    required=True,
                    params={"retrieval_prefs": user_input.retrieval_prefs or {}},
                ),
                PlanStep(
                    step_id="synthesize",
                    kind="synthesize",
                    required=True,
                    depends_on=["retrieve"],
                ),
            ]
        elif mode == "tool":
            steps = [
                PlanStep(
                    step_id="tool_call",
                    kind="tool_call",
                    required=True,
                    params={"tool": user_input.metadata.get("tool") if user_input.metadata else None},
                ),
                PlanStep(
                    step_id="synthesize",
                    kind="synthesize",
                    required=True,
                    depends_on=["tool_call"],
                ),
            ]
        elif mode == "hybrid":
            steps = [
                PlanStep(
                    step_id="retrieve",
                    kind="retrieve",
                    required=False,
                    params={"retrieval_prefs": user_input.retrieval_prefs or {}},
                ),
                PlanStep(
                    step_id="tool_call",
                    kind="tool_call",
                    required=False,
                    depends_on=["retrieve"],
                    params={"tool": user_input.metadata.get("tool") if user_input.metadata else None},
                ),
                PlanStep(
                    step_id="synthesize",
                    kind="synthesize",
                    required=True,
                    depends_on=["retrieve", "tool_call"],
                ),
            ]
        else:
            steps = [
                PlanStep(
                    step_id="synthesize",
                    kind="synthesize",
                    required=True,
                )
            ]

        return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps)
