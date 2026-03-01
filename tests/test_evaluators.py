"""Tests for evaluation module."""

import pytest

from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.replay import (
    ReplayEvaluator,
    ReplayDataset,
    ReplayGates,
    ReplayReport,
)
from autoflow.types import ChangeProposal, EvaluationResult, ProposalKind, RiskLevel


class TestShadowEvaluator:
    """Tests for ShadowEvaluator."""

    def test_always_passes(self):
        """Test that ShadowEvaluator always passes."""
        evaluator = ShadowEvaluator()

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.HIGH,
            target_paths=("*",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert result.passed is True
        assert result.score == 1.0

    def test_return_metrics(self):
        """Test that ShadowEvaluator returns metrics."""
        evaluator = ShadowEvaluator()

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert "shadow_pass" in result.metrics
        assert result.metrics["shadow_pass"] == 1.0


class TestCompositeEvaluator:
    """Tests for CompositeEvaluator."""

    def test_all_evaluators_must_pass(self):
        """Test that all evaluators must pass."""
        class PassEvaluator:
            def evaluate(self, proposal):
                return EvaluationResult(
                    proposal_id=proposal.proposal_id,
                    passed=True,
                    score=1.0,
                    metrics={},
                )

        class FailEvaluator:
            def evaluate(self, proposal):
                return EvaluationResult(
                    proposal_id=proposal.proposal_id,
                    passed=False,
                    score=0.0,
                    metrics={},
                )

        evaluator = CompositeEvaluator(evaluators=[PassEvaluator(), FailEvaluator()])

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert result.passed is False

    def test_score_averaging(self):
        """Test that scores are averaged."""
        evaluator = CompositeEvaluator(
            evaluators=[
                type(
                    "Eval",
                    (),
                    {
                        "evaluate": lambda self, proposal: EvaluationResult(
                            proposal_id=proposal.proposal_id,
                            passed=True,
                            score=0.5,
                            metrics={},
                        )
                    },
                )(),
                type(
                    "Eval",
                    (),
                    {
                        "evaluate": lambda self, proposal: EvaluationResult(
                            proposal_id=proposal.proposal_id,
                            passed=True,
                            score=1.0,
                            metrics={},
                        )
                    },
                )(),
            ]
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert result.score == 0.75  # (0.5 + 1.0) / 2

    def test_empty_evaluators(self):
        """Test composite evaluator with no evaluators."""
        evaluator = CompositeEvaluator(evaluators=[])

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        # Should not crash, score will be 0
        result = evaluator.evaluate(proposal)
        assert result.passed is True  # all([]) is True
        assert result.score == 0.0


class TestReplayEvaluator:
    """Tests for ReplayEvaluator."""

    def test_evaluate_passes_gates(self):
        """Test evaluation that passes gates."""
        dataset = ReplayDataset(
            runs=[
                {"latency_ms": 100, "success": True},
                {"latency_ms": 120, "success": True},
                {"latency_ms": 110, "success": True},
            ]
        )

        def compute_baseline(ds):
            latencies = [r["latency_ms"] for r in ds.runs]
            return {"p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)]}

        def simulate_candidate(ds, proposal):
            # Simulate improvement
            return {"p95_latency_ms": 90}

        gates = ReplayGates(
            max_regressions={"p95_latency_ms": 50},  # Allow up to 50ms regression
        )

        evaluator = ReplayEvaluator(
            dataset=dataset,
            compute_baseline=compute_baseline,
            simulate_candidate=simulate_candidate,
            gates=gates,
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert result.passed is True

    def test_evaluate_fails_gates(self):
        """Test evaluation that fails gates."""
        dataset = ReplayDataset(
            runs=[
                {"latency_ms": 100},
                {"latency_ms": 120},
            ]
        )

        def compute_baseline(ds):
            return {"p95_latency_ms": 120}

        def simulate_candidate(ds, proposal):
            # Simulate regression
            return {"p95_latency_ms": 200}

        gates = ReplayGates(
            max_regressions={"p95_latency_ms": 50},  # Only allow 50ms regression
        )

        evaluator = ReplayEvaluator(
            dataset=dataset,
            compute_baseline=compute_baseline,
            simulate_candidate=simulate_candidate,
            gates=gates,
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert result.passed is False
        assert "regressed" in result.notes.lower()

    def test_min_improvement_gate(self):
        """Test minimum improvement gate."""
        dataset = ReplayDataset(
            runs=[
                {"success_rate": 0.8},
                {"success_rate": 0.85},
            ]
        )

        def compute_baseline(ds):
            rates = [r["success_rate"] for r in ds.runs]
            return {"success_rate": sum(rates) / len(rates)}

        def simulate_candidate(ds, proposal):
            # Simulate small improvement
            return {"success_rate": 0.83}

        gates = ReplayGates(
            min_improvements={"success_rate": 0.05}  # Must improve by 5%
        )

        evaluator = ReplayEvaluator(
            dataset=dataset,
            compute_baseline=compute_baseline,
            simulate_candidate=simulate_candidate,
            gates=gates,
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        # Should fail - only improved by 0.03, need 0.05
        assert result.passed is False
        assert "improved" in result.notes.lower()

    def test_returns_metrics(self):
        """Test that evaluator returns detailed metrics."""
        dataset = ReplayDataset(runs=[{"value": 10}, {"value": 20}])

        def compute_baseline(ds):
            values = [r["value"] for r in ds.runs]
            return {"avg_value": sum(values) / len(values)}

        def simulate_candidate(ds, proposal):
            return {"avg_value": 15}

        gates = ReplayGates()

        evaluator = ReplayEvaluator(
            dataset=dataset,
            compute_baseline=compute_baseline,
            simulate_candidate=simulate_candidate,
            gates=gates,
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        result = evaluator.evaluate(proposal)

        assert "baseline.avg_value" in result.metrics
        assert "candidate.avg_value" in result.metrics
        assert "delta.avg_value" in result.metrics
        assert result.metrics["baseline.avg_value"] == 15.0
        assert result.metrics["candidate.avg_value"] == 15.0

    def test_unsupported_proposal_kind(self):
        """Test that unsupported proposal kinds raise error."""
        from autoflow.errors import EvaluationError

        evaluator = ReplayEvaluator(
            dataset=ReplayDataset(runs=[]),
            compute_baseline=lambda ds: {},
            simulate_candidate=lambda ds, p: {},
            gates=ReplayGates(),
        )

        # Create a proposal with unsupported kind
        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind="unknown_kind",  # type: ignore
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        with pytest.raises(EvaluationError):
            evaluator.evaluate(proposal)


class TestReplayGates:
    """Tests for ReplayGates."""

    def test_default_empty_gates(self):
        """Test default gates with no constraints."""
        gates = ReplayGates()

        assert gates.max_regressions == {}
        assert gates.min_improvements == {}

    def test_with_constraints(self):
        """Test gates with constraints."""
        gates = ReplayGates(
            max_regressions={"latency_ms": 100, "error_rate": 0.01},
            min_improvements={"success_rate": 0.05},
        )

        assert gates.max_regressions["latency_ms"] == 100
        assert gates.max_regressions["error_rate"] == 0.01
        assert gates.min_improvements["success_rate"] == 0.05


class TestReplayDataset:
    """Tests for ReplayDataset."""

    def test_create_dataset(self):
        """Test creating replay dataset."""
        dataset = ReplayDataset(runs=[{"data": 1}, {"data": 2}])

        assert len(dataset.runs) == 2
        assert dataset.runs[0]["data"] == 1

    def test_empty_dataset(self):
        """Test empty replay dataset."""
        dataset = ReplayDataset(runs=[])

        assert len(dataset.runs) == 0
