from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReasoningStrategy(str, Enum):
    SINGLE_SHOT = "single_shot"
    MULTI_STEP_TOOLS = "multi_step_tools"
    SUPERVISOR_WORKERS = "supervisor_workers"
    PARALLEL_SPECIALISTS = "parallel_specialists"
    REVIEWER_LOOP = "reviewer_loop"


@dataclass
class ReasoningLimits:
    max_steps: int = 50
    max_tool_calls: int = 50
    max_tokens: int = 1_000_000
    max_wall_seconds: int = 300
    max_cost: float = 5.0


@dataclass
class ReasoningContext:
    agent_id: str
    conversation_id: str
    strategy: ReasoningStrategy
    limits: ReasoningLimits
    metadata: dict[str, Any]


class ReasoningLoopSelector:
    """Selects orchestration strategy from agent/task metadata.

    The selector is intentionally conservative for backward compatibility:
    unsupported strategy requests fall back to `MULTI_STEP_TOOLS`.
    """

    @staticmethod
    def choose(agent: Any | None, task_hint: str | None = None) -> ReasoningStrategy:
        style = (getattr(agent, "reasoning_style", "") or "").lower()
        hint = (task_hint or "").lower()

        if "single" in style or "single-shot" in style or "quick" in hint:
            return ReasoningStrategy.SINGLE_SHOT
        if "review" in style or "maker-checker" in style:
            return ReasoningStrategy.REVIEWER_LOOP
        if "parallel" in style or "fan-out" in style:
            return ReasoningStrategy.PARALLEL_SPECIALISTS
        if "supervisor" in style or "manager" in style:
            return ReasoningStrategy.SUPERVISOR_WORKERS
        return ReasoningStrategy.MULTI_STEP_TOOLS


class ReasoningPolicy:
    """Policy helper used by chat/orchestration services.

    Today this reads from existing Task/Agent fields and returns a unified limit
    profile. It can later be sourced from DB-backed policy tables.
    """

    @staticmethod
    def limits_from_task(task: Any | None) -> ReasoningLimits:
        if task is None:
            return ReasoningLimits()
        return ReasoningLimits(
            max_steps=max(1, int(getattr(task, "max_steps", 50) or 50)),
            max_tool_calls=max(1, int(getattr(task, "max_tool_calls", 50) or 50)),
            max_tokens=max(1_000, int(getattr(task, "max_tokens", 1_000_000) or 1_000_000)),
            max_wall_seconds=300,
            max_cost=5.0,
        )
