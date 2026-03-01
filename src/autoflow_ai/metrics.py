from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from autoflow_ai.dataset import AIDataset


def _percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


@dataclass(frozen=True)
class AIMetrics:
    success_rate: float
    override_rate: float
    tool_error_rate: float
    p95_tool_latency_ms: float
    p95_model_latency_ms: float
    avg_cost_usd: float

    def as_dict(self) -> Mapping[str, float]:
        return {
            "success_rate": self.success_rate,
            "override_rate": self.override_rate,
            "tool_error_rate": self.tool_error_rate,
            "p95_tool_latency_ms": self.p95_tool_latency_ms,
            "p95_model_latency_ms": self.p95_model_latency_ms,
            "avg_cost_usd": self.avg_cost_usd,
        }


def compute_metrics(dataset: AIDataset, *, workflow_id: str | None = None) -> AIMetrics:
    runs = [r for r in dataset.runs if workflow_id is None or r.workflow_id == workflow_id]
    if not runs:
        return AIMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    successes = sum(1 for r in runs if r.outcome.success)
    overrides = sum(1 for r in runs if r.outcome.human_override)

    tool_calls = [tc for r in runs for tc in r.tool_calls]
    tool_errors = sum(1 for tc in tool_calls if not tc.success)

    tool_latencies = [float(tc.latency_ms) for tc in tool_calls]
    model_latencies = [float(mc.latency_ms) for r in runs for mc in r.model_calls]

    costs = [float(r.outcome.cost_usd) for r in runs if r.outcome.cost_usd is not None]
    avg_cost = sum(costs) / len(costs) if costs else 0.0

    return AIMetrics(
        success_rate=successes / len(runs),
        override_rate=overrides / len(runs),
        tool_error_rate=(tool_errors / len(tool_calls)) if tool_calls else 0.0,
        p95_tool_latency_ms=_percentile(tool_latencies, 0.95),
        p95_model_latency_ms=_percentile(model_latencies, 0.95),
        avg_cost_usd=avg_cost,
    )