"""Tests for decision graph module."""

import pytest

from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.types import ChangeProposal, GraphNode, RiskLevel, ProposalKind


class TestDecisionGraph:
    """Tests for DecisionGraph."""

    def test_init(self):
        """Test DecisionGraph initialization."""
        rules = [HighErrorRateRetryRule(workflow_id="test", threshold=3)]
        graph = DecisionGraph(rules=rules)

        assert graph.rules == rules

    def test_run_without_edges(self, sample_nodes):
        """Test running decision graph without edges."""
        class TestRule:
            def propose(self, nodes):
                return [
                    ChangeProposal(
                        proposal_id="prop_1",
                        kind=ProposalKind.CONFIG_EDIT,
                        title="Test Proposal",
                        description="Test",
                        risk=RiskLevel.LOW,
                        target_paths=("config/test.yaml",),
                        payload={"test": True},
                    )
                ]

        graph = DecisionGraph(rules=[TestRule()])
        proposals = graph.run(sample_nodes)

        assert len(proposals) == 1
        assert proposals[0].title == "Test Proposal"

    def test_run_with_edges(self, sample_nodes, sample_edges):
        """Test running decision graph with edges."""
        class TestRuleWithEdges:
            def propose(self, nodes, edges=None):
                # Check that edges are passed
                assert edges is not None
                assert len(edges) == 2
                return []

        graph = DecisionGraph(rules=[TestRuleWithEdges()])
        proposals = graph.run(sample_nodes, sample_edges)

        assert len(proposals) == 0

    def test_run_multiple_rules(self, sample_nodes):
        """Test running multiple rules."""
        class Rule1:
            def propose(self, nodes):
                return [
                    ChangeProposal(
                        proposal_id="prop_1",
                        kind=ProposalKind.CONFIG_EDIT,
                        title="Rule 1 Proposal",
                        description="Test",
                        risk=RiskLevel.LOW,
                        target_paths=("config/test.yaml",),
                        payload={},
                    )
                ]

        class Rule2:
            def propose(self, nodes):
                return [
                    ChangeProposal(
                        proposal_id="prop_2",
                        kind=ProposalKind.CONFIG_EDIT,
                        title="Rule 2 Proposal",
                        description="Test",
                        risk=RiskLevel.LOW,
                        target_paths=("config/test.yaml",),
                        payload={},
                    )
                ]

        graph = DecisionGraph(rules=[Rule1(), Rule2()])
        proposals = graph.run(sample_nodes)

        assert len(proposals) == 2

    def test_run_empty_rules(self, sample_nodes):
        """Test running decision graph with no rules."""
        graph = DecisionGraph(rules=[])
        proposals = graph.run(sample_nodes)

        assert len(proposals) == 0

    def test_rule_with_edges_parameter(self, sample_nodes, sample_edges):
        """Test that rules accepting edges parameter receive them."""
        class EdgeAwareRule:
            def propose(self, nodes, edges=None):
                if edges:
                    return [
                        ChangeProposal(
                            proposal_id="prop_1",
                            kind=ProposalKind.CONFIG_EDIT,
                            title="Edge Proposal",
                            description="Test",
                            risk=RiskLevel.LOW,
                            target_paths=("config/test.yaml",),
                            payload={},
                        )
                    ]
                return []

        graph = DecisionGraph(rules=[EdgeAwareRule()])
        proposals = graph.run(sample_nodes, sample_edges)

        assert len(proposals) == 1

    def test_rule_without_edges_parameter(self, sample_nodes):
        """Test that rules not accepting edges still work."""
        class SimpleRule:
            def propose(self, nodes):
                return [
                    ChangeProposal(
                        proposal_id="prop_1",
                        kind=ProposalKind.CONFIG_EDIT,
                        title="Simple Proposal",
                        description="Test",
                        risk=RiskLevel.LOW,
                        target_paths=("config/test.yaml",),
                        payload={},
                    )
                ]

        graph = DecisionGraph(rules=[SimpleRule()])
        proposals = graph.run(sample_nodes, edges=None)

        assert len(proposals) == 1


class TestHighErrorRateRetryRule:
    """Tests for HighErrorRateRetryRule."""

    def test_trigger_on_threshold(self):
        """Test that rule triggers when error count reaches threshold."""
        rule = HighErrorRateRetryRule(workflow_id="test_workflow", threshold=3)

        # Create nodes with 3 exceptions
        nodes = [
            GraphNode(
                node_id=f"node_{i}",
                node_type="event",
                properties={"source": "app", "name": "exception", "workflow_id": "test_workflow"},
            )
            for i in range(3)
        ]

        proposals = rule.propose(nodes)

        assert len(proposals) == 1
        assert "retry" in proposals[0].title.lower()

    def test_no_trigger_below_threshold(self):
        """Test that rule doesn't trigger below threshold."""
        rule = HighErrorRateRetryRule(workflow_id="test_workflow", threshold=3)

        # Create nodes with 2 exceptions
        nodes = [
            GraphNode(
                node_id=f"node_{i}",
                node_type="event",
                properties={"source": "app", "name": "exception", "workflow_id": "test_workflow"},
            )
            for i in range(2)
        ]

        proposals = rule.propose(nodes)

        assert len(proposals) == 0

    def test_filters_by_workflow_id(self):
        """Test that rule only counts exceptions for its workflow."""
        rule = HighErrorRateRetryRule(workflow_id="workflow_a", threshold=2)

        nodes = [
            GraphNode(
                node_id="node_1",
                node_type="event",
                properties={"source": "app", "name": "exception", "workflow_id": "workflow_a"},
            ),
            GraphNode(
                node_id="node_2",
                node_type="event",
                properties={"source": "app", "name": "exception", "workflow_id": "workflow_b"},
            ),
            GraphNode(
                node_id="node_3",
                node_type="event",
                properties={"source": "app", "name": "exception", "workflow_id": "workflow_a"},
            ),
        ]

        proposals = rule.propose(nodes)

        # Should trigger (2 exceptions for workflow_a)
        assert len(proposals) == 1

    def test_ignores_non_exception_events(self):
        """Test that rule only counts exception events."""
        rule = HighErrorRateRetryRule(workflow_id="test_workflow", threshold=2)

        nodes = [
            GraphNode(
                node_id="node_1",
                node_type="event",
                properties={
                    "source": "app",
                    "name": "exception",
                    "workflow_id": "test_workflow",
                },
            ),
            GraphNode(
                node_id="node_2",
                node_type="event",
                properties={
                    "source": "app",
                    "name": "request_processed",
                    "workflow_id": "test_workflow",
                },
            ),
        ]

        proposals = rule.propose(nodes)

        # Should not trigger (only 1 exception)
        assert len(proposals) == 0
