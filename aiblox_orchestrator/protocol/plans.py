from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


PlanStepKind = Literal[
    "retrieve",
    "tool_call",
    "agent_run",
    "validate",
    "synthesize",
    "emit_results",
    "finalize",
]


class PlanStep(BaseModel):
    """Single execution step in a plan."""

    step_id: str
    kind: PlanStepKind
    required: bool = True
    depends_on: List[str] = Field(default_factory=list)
    params: Dict[str, object] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """Ordered set of steps to execute for a request."""

    plan_id: str
    steps: List[PlanStep] = Field(default_factory=list)
