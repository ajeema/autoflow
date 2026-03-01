from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from autoflow.errors import EvaluationError
from autoflow.types import ChangeProposal, EvaluationResult, ProposalKind


MetricDict = Mapping[str, float]


@dataclass(frozen=True)
class ReplayGates:
    """
    Defines pass/fail gates for replay evaluation.

    - max_regressions: metrics in this dict may not increase (or decrease) beyond allowed delta.
      Example: {"p95_latency_ms": 50.0} means candidate must not exceed baseline by > 50ms.
    - min_improvements: metrics in this dict must improve by at least delta.
      Example: {"success_rate": 0.01} means success_rate must increase by >= 1 percentage point.
    """
    max_regressions: Mapping[str, float] = None  # type: ignore[assignment]
    min_improvements: Mapping[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_regressions", dict(self.max_regressions or {}))
        object.__setattr__(self, "min_improvements", dict(self.min_improvements or {}))


@dataclass(frozen=True)
class ReplayReport:
    baseline: MetricDict
    candidate: MetricDict
    deltas: MetricDict
    passed: bool
    notes: str


@dataclass(frozen=True)
class ReplayDataset:
    """
    Generic replay dataset.

    The dataset is intentionally simple: a list of 'runs', each run is a dict with event/outcome keys.
    Domain-specific packages (autoflow_ai) can define richer typed structures and converters.
    """
    runs: Sequence[Mapping[str, object]]


ComputeBaselineFn = Callable[[ReplayDataset], MetricDict]
SimulateCandidateFn = Callable[[ReplayDataset, ChangeProposal], MetricDict]


@dataclass(frozen=True)
class ReplayEvaluator:
    """
    Deterministic offline evaluator.

    You supply:
      - compute_baseline(dataset) -> metrics
      - simulate_candidate(dataset, proposal) -> metrics

    This keeps the core evaluator domain-agnostic and testable.
    """
    dataset: ReplayDataset
    compute_baseline: ComputeBaselineFn
    simulate_candidate: SimulateCandidateFn
    gates: ReplayGates

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        if proposal.kind not in (ProposalKind.CONFIG_EDIT, ProposalKind.TEXT_PATCH):
            # Replay can still run, but most sims assume config edits.
            raise EvaluationError(f"ReplayEvaluator does not support proposal kind: {proposal.kind}")

        baseline = self.compute_baseline(self.dataset)
        candidate = self.simulate_candidate(self.dataset, proposal)

        report = self._compare(baseline=baseline, candidate=candidate, gates=self.gates)

        # Score: simple heuristic—sum of improvements minus regressions.
        score = 0.0
        for k, d in report.deltas.items():
            score += d

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=report.passed,
            score=score,
            metrics={**{f"baseline.{k}": v for k, v in baseline.items()},
                     **{f"candidate.{k}": v for k, v in candidate.items()},
                     **{f"delta.{k}": v for k, v in report.deltas.items()}},
            notes=report.notes,
        )

    @staticmethod
    def _compare(*, baseline: MetricDict, candidate: MetricDict, gates: ReplayGates) -> ReplayReport:
        deltas: dict[str, float] = {}
        for k, b in baseline.items():
            c = float(candidate.get(k, b))
            deltas[k] = c - float(b)

        # Apply gates
        failures: list[str] = []

        for metric, allowed in gates.max_regressions.items():
            b = float(baseline.get(metric, 0.0))
            c = float(candidate.get(metric, 0.0))
            if (c - b) > float(allowed):
                failures.append(f"{metric} regressed by {c - b:.4f} > allowed {allowed:.4f}")

        for metric, required in gates.min_improvements.items():
            b = float(baseline.get(metric, 0.0))
            c = float(candidate.get(metric, 0.0))
            if (c - b) < float(required):
                failures.append(f"{metric} improved by {c - b:.4f} < required {required:.4f}")

        passed = len(failures) == 0
        notes = "PASS" if passed else "FAIL: " + "; ".join(failures)

        return ReplayReport(baseline=baseline, candidate=candidate, deltas=deltas, passed=passed, notes=notes)