"""Tests for AutoImproveEngine."""

import pytest
from pathlib import Path

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.observe.events import make_event


class TestAutoImproveEngine:
    """Tests for AutoImproveEngine."""

    def test_init(self, tmp_path):
        """Test engine initialization."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(
            store=store,
            graph_builder=builder,
            decision_graph=graph,
            evaluator=evaluator,
            applier=applier,
        )

        assert engine.store == store
        assert engine.graph_builder == builder
        assert engine.decision_graph == graph
        assert engine.evaluator == evaluator
        assert engine.applier == applier

    def test_ingest(self, tmp_path):
        """Test ingesting events."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        events = [
            make_event(
                source="test",
                name="test_event",
                attributes={"key": "value"},
            )
        ]

        engine.ingest(events)

        # Verify nodes were created
        nodes = store.query_nodes()
        assert len(nodes) == 1

    def test_propose(self, tmp_path):
        """Test generating proposals."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()

        # Create a rule that will trigger
        class TestRule:
            def propose(self, nodes):
                if nodes:
                    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

                    return [
                        ChangeProposal(
                            proposal_id="test_prop",
                            kind=ProposalKind.CONFIG_EDIT,
                            title="Test Proposal",
                            description="Test",
                            risk=RiskLevel.LOW,
                            target_paths=("config/test.yaml",),
                            payload={},
                        )
                    ]
                return []

        graph = DecisionGraph(rules=[TestRule()])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        # Ingest events
        engine.ingest(
            [
                make_event(
                    source="test",
                    name="test_event",
                    attributes={},
                )
            ]
        )

        # Generate proposals
        proposals = engine.propose()

        assert len(proposals) == 1
        assert proposals[0].title == "Test Proposal"

    def test_propose_with_node_type_filter(self, tmp_path):
        """Test proposing with node type filter."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        # Ingest events
        engine.ingest(
            [
                make_event(
                    source="test",
                    name="test_event",
                    attributes={},
                )
            ]
        )

        # Propose with no filter - should get nodes
        proposals = engine.propose()
        assert isinstance(proposals, list)

        # Propose with filter (no matching nodes)
        proposals_filtered = engine.propose(node_type="nonexistent")
        assert isinstance(proposals_filtered, list)

    def test_propose_with_limit(self, tmp_path):
        """Test proposing with limit parameter."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        # Ingest multiple events
        events = [
            make_event(
                source="test",
                name=f"event_{i}",
                attributes={},
            )
            for i in range(10)
        ]

        engine.ingest(events)

        # Propose with limit
        proposals = engine.propose(limit=5)

        # Should work without error
        assert isinstance(proposals, list)

    def test_propose_with_edges(self, tmp_path, sample_workflow_events):
        """Test propose_with_edges method."""
        from autoflow.workflow.graph_builder import WorkflowAwareGraphBuilder

        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = WorkflowAwareGraphBuilder()  # Creates edges
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        # Ingest workflow events
        engine.ingest(sample_workflow_events)

        # Propose with edges
        proposals = engine.propose_with_edges()

        assert isinstance(proposals, list)

    def test_evaluate_and_apply(self, tmp_path, capsys):
        """Test evaluate_and_apply method."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

        proposals = [
            ChangeProposal(
                proposal_id="test_prop",
                kind=ProposalKind.CONFIG_EDIT,
                title="Test",
                description="Test",
                risk=RiskLevel.LOW,
                target_paths=("config/test.yaml",),
                payload={},
            )
        ]

        # Evaluate and apply
        engine.evaluate_and_apply(proposals)

        # Verify apply was called
        captured = capsys.readouterr()
        assert "[APPLY]" in captured.out

    def test_evaluate_and_apply_skips_failing(self, tmp_path):
        """Test that evaluate_and_apply skips proposals that fail evaluation."""
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(rules=[])

        # Create evaluator that fails
        class FailingEvaluator:
            def evaluate(self, proposal):
                from autoflow.types import EvaluationResult

                return EvaluationResult(
                    proposal_id=proposal.proposal_id,
                    passed=False,
                    score=0.0,
                    metrics={},
                )

        evaluator = FailingEvaluator()
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

        proposals = [
            ChangeProposal(
                proposal_id="test_prop",
                kind=ProposalKind.CONFIG_EDIT,
                title="Test",
                description="Test",
                risk=RiskLevel.LOW,
                target_paths=("config/test.yaml",),
                payload={},
            )
        ]

        # Should not raise, just skip
        engine.evaluate_and_apply(proposals)


class TestEngineIntegration:
    """Integration tests for the full engine flow."""

    def test_full_flow(self, tmp_path):
        """Test complete flow: ingest -> propose -> evaluate -> apply."""
        # Setup
        store = SQLiteGraphStore(db_path=str(tmp_path / "test.db"))
        builder = ContextGraphBuilder()
        graph = DecisionGraph(
            rules=[HighErrorRateRetryRule(workflow_id="test_workflow", threshold=2)]
        )
        evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])
        applier = ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        )

        engine = AutoImproveEngine(store, builder, graph, evaluator, applier)

        # Ingest exception events
        events = [
            make_event(
                source="app",
                name="exception",
                attributes={"workflow_id": "test_workflow"},
            ),
            make_event(
                source="app",
                name="exception",
                attributes={"workflow_id": "test_workflow"},
            ),
        ]

        engine.ingest(events)

        # Propose
        proposals = engine.propose()
        assert len(proposals) >= 1

        # Evaluate
        results = [engine.evaluator.evaluate(p) for p in proposals]
        assert all(r.passed for r in results)

        # Apply
        for proposal, result in zip(proposals, results):
            if result.passed:
                engine.applier.apply(proposal)
