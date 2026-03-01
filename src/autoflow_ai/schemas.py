from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ToolCall:
    tool: str
    latency_ms: float
    success: bool
    error_type: str | None = None


@dataclass(frozen=True)
class ModelCall:
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class RunOutcome:
    success: bool
    human_override: bool = False
    quality_score: float | None = None  # optional offline judge/human score
    cost_usd: float | None = None


@dataclass(frozen=True)
class AIRun:
    """
    A single historical run of an AI workflow.

    This is the unit of replay.
    """
    run_id: str
    workflow_id: str
    tool_calls: Sequence[ToolCall] = field(default_factory=tuple)
    model_calls: Sequence[ModelCall] = field(default_factory=tuple)
    outcome: RunOutcome = field(default_factory=lambda: RunOutcome(success=True))
    attributes: Mapping[str, Any] = field(default_factory=dict)