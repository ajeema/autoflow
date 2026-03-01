from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from autoflow.evaluate.replay import ReplayDataset, ReplayEvaluator, ReplayGates
from autoflow.types import ChangeProposal, ProposalKind
from autoflow_ai.dataset import AIDataset
from autoflow_ai.metrics import compute_metrics


def _to_core_dataset(ai: AIDataset) -> ReplayDataset:
    # The core evaluator only needs runs as mappings; we keep them opaque here.
    runs = [{"run": r} for r in ai.runs]
    return ReplayDataset(runs=runs)


@dataclass(frozen=True)
class AIReplayEvaluator:
    dataset: AIDataset
    gates: ReplayGates
    workflow_id: str | None = None

    def as_core(self) -> ReplayEvaluator:
        core_dataset = _to_core_dataset(self.dataset)

        def compute_baseline(_: ReplayDataset) -> Mapping[str, float]:
            m = compute_metrics(self.dataset, workflow_id=self.workflow_id)
            return dict(m.as_dict())

        def simulate_candidate(_: ReplayDataset, proposal: ChangeProposal) -> Mapping[str, float]:
            """
            Deterministic simulation:
            - CONFIG_EDIT proposals that tune retry policy can reduce tool_error_rate at a latency/cost tradeoff.
            - Everything else: return baseline (unknown effect).
            """
            baseline = compute_metrics(self.dataset, workflow_id=self.workflow_id).as_dict()

            if proposal.kind != ProposalKind.CONFIG_EDIT:
                return dict(baseline)

            # Convention for retry tuning proposals:
            # payload = {"op":"set", "path":"workflows.<id>.retry_policy", "value":{...}}
            payload = dict(proposal.payload)
            path = payload.get("path")
            value = payload.get("value")

            if not (isinstance(path, str) and isinstance(value, dict) and "retry_policy" in path):
                return dict(baseline)

            max_retries = value.get("max_retries")
            if not isinstance(max_retries, int):
                return dict(baseline)

            # Simple, bounded simulation heuristic:
            # - more retries reduces tool_error_rate up to a cap
            # - increases p95_tool_latency_ms and avg_cost_usd modestly
            tool_error_rate = float(baseline.get("tool_error_rate", 0.0))
            p95_tool_latency_ms = float(baseline.get("p95_tool_latency_ms", 0.0))
            avg_cost_usd = float(baseline.get("avg_cost_usd", 0.0))
            success_rate = float(baseline.get("success_rate", 0.0))

            # Improvements diminish quickly.
            reduction = min(0.25, 0.05 * max_retries)
            increased_latency = 0.10 * max_retries  # 10% p95 penalty per retry
            increased_cost = 0.02 * max_retries     # small cost bump

            candidate = dict(baseline)
            candidate["tool_error_rate"] = max(0.0, tool_error_rate * (1.0 - reduction))
            candidate["p95_tool_latency_ms"] = p95_tool_latency_ms * (1.0 + increased_latency)
            candidate["avg_cost_usd"] = avg_cost_usd * (1.0 + increased_cost)

            # If tool errors drop, overall success tends to rise slightly.
            candidate["success_rate"] = min(1.0, success_rate + (tool_error_rate - candidate["tool_error_rate"]) * 0.5)

            return candidate

        return ReplayEvaluator(
            dataset=core_dataset,
            compute_baseline=compute_baseline,
            simulate_candidate=simulate_candidate,
            gates=self.gates,
        )