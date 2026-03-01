"""Tests for types module."""

import pytest
from datetime import datetime
from uuid import UUID

from autoflow.types import (
    ObservationEvent,
    GraphNode,
    GraphEdge,
    ContextGraphDelta,
    ChangeProposal,
    EvaluationResult,
    RiskLevel,
    ProposalKind,
    StepStatus,
)


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


class TestProposalKind:
    """Tests for ProposalKind enum."""

    def test_values(self):
        """Test ProposalKind enum values."""
        assert ProposalKind.TEXT_PATCH.value == "text_patch"
        assert ProposalKind.CONFIG_EDIT.value == "config_edit"


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_values(self):
        """Test StepStatus enum values."""
        assert StepStatus.SUCCESS.value == "success"
        assert StepStatus.FAILURE.value == "failure"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.RETRY.value == "retry"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.PENDING.value == "pending"


class TestObservationEvent:
    """Tests for ObservationEvent dataclass."""

    def test_create_event(self):
        """Test creating an observation event."""
        event = ObservationEvent(
            event_id="test_id",
            timestamp=datetime.now(),
            source="test_source",
            name="test_name",
            attributes={"key": "value"},
        )

        assert event.event_id == "test_id"
        assert event.source == "test_source"
        assert event.name == "test_name"
        assert event.attributes == {"key": "value"}

    def test_event_immutability(self):
        """Test that ObservationEvent is immutable."""
        event = ObservationEvent(
            event_id="test_id",
            timestamp=datetime.now(),
            source="test",
            name="test",
            attributes={},
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            event.source = "new_source"


class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_create_node(self):
        """Test creating a graph node."""
        node = GraphNode(
            node_id="node_1",
            node_type="test_type",
            properties={"key": "value"},
        )

        assert node.node_id == "node_1"
        assert node.node_type == "test_type"
        assert node.properties == {"key": "value"}

    def test_node_immutability(self):
        """Test that GraphNode is immutable."""
        node = GraphNode(
            node_id="node_1",
            node_type="test",
            properties={},
        )

        with pytest.raises(Exception):
            node.node_type = "new_type"


class TestGraphEdge:
    """Tests for GraphEdge dataclass."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            edge_type="test_edge",
            from_node_id="node_1",
            to_node_id="node_2",
            properties={"weight": 1.0},
        )

        assert edge.edge_type == "test_edge"
        assert edge.from_node_id == "node_1"
        assert edge.to_node_id == "node_2"
        assert edge.properties == {"weight": 1.0}

    def test_edge_immutability(self):
        """Test that GraphEdge is immutable."""
        edge = GraphEdge(
            edge_type="test",
            from_node_id="node_1",
            to_node_id="node_2",
            properties={},
        )

        with pytest.raises(Exception):
            edge.edge_type = "new_type"


class TestContextGraphDelta:
    """Tests for ContextGraphDelta dataclass."""

    def test_create_delta(self):
        """Test creating a context graph delta."""
        nodes = [
            GraphNode(node_id="node_1", node_type="test", properties={}),
        ]
        edges = [
            GraphEdge(
                edge_type="test",
                from_node_id="node_1",
                to_node_id="node_2",
                properties={},
            ),
        ]

        delta = ContextGraphDelta(nodes=nodes, edges=edges)

        assert delta.nodes == nodes
        assert delta.edges == edges

    def test_empty_delta(self):
        """Test creating an empty delta."""
        delta = ContextGraphDelta(nodes=[], edges=[])

        assert len(delta.nodes) == 0
        assert len(delta.edges) == 0


class TestChangeProposal:
    """Tests for ChangeProposal dataclass."""

    def test_create_proposal(self):
        """Test creating a change proposal."""
        proposal = ChangeProposal(
            proposal_id="prop_1",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test Proposal",
            description="Test description",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={"key": "value"},
        )

        assert proposal.proposal_id == "prop_1"
        assert proposal.kind == ProposalKind.CONFIG_EDIT
        assert proposal.title == "Test Proposal"
        assert proposal.description == "Test description"
        assert proposal.risk == RiskLevel.LOW
        assert proposal.target_paths == ["config/test.yaml"]
        assert proposal.payload == {"key": "value"}

    def test_proposal_immutability(self):
        """Test that ChangeProposal is immutable."""
        proposal = ChangeProposal(
            proposal_id="prop_1",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        with pytest.raises(Exception):
            proposal.title = "New Title"

    def test_text_patch_proposal(self):
        """Test creating a text patch proposal."""
        proposal = ChangeProposal(
            proposal_id="prop_1",
            kind=ProposalKind.TEXT_PATCH,
            title="Fix bug",
            description="Add error handling",
            risk=RiskLevel.LOW,
            target_paths=("src/code.py",),
            payload={
                "patch": "--- a/src/code.py\n+++ b/src/code.py",
                "format": "unified",
            },
        )

        assert proposal.kind == ProposalKind.TEXT_PATCH
        assert "patch" in proposal.payload

    def test_config_edit_proposal(self):
        """Test creating a config edit proposal."""
        proposal = ChangeProposal(
            proposal_id="prop_1",
            kind=ProposalKind.CONFIG_EDIT,
            title="Increase timeout",
            description="Fix timeout issues",
            risk=RiskLevel.LOW,
            target_paths=("config/api.yaml",),
            payload={
                "op": "set",
                "path": "timeout_ms",
                "value": 5000,
                "old_value": 3000,
            },
        )

        assert proposal.kind == ProposalKind.CONFIG_EDIT
        assert proposal.payload["op"] == "set"


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_create_result(self):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            proposal_id="prop_1",
            passed=True,
            score=1.0,
            metrics={"metric1": 0.5, "metric2": 0.8},
            notes="Test passed",
        )

        assert result.proposal_id == "prop_1"
        assert result.passed is True
        assert result.score == 1.0
        assert result.metrics == {"metric1": 0.5, "metric2": 0.8}
        assert result.notes == "Test passed"

    def test_result_with_empty_notes(self):
        """Test result with default notes."""
        result = EvaluationResult(
            proposal_id="prop_1",
            passed=False,
            score=0.0,
            metrics={},
        )

        assert result.notes == ""

    def test_result_with_empty_metrics(self):
        """Test result with empty metrics."""
        result = EvaluationResult(
            proposal_id="prop_1",
            passed=True,
            score=1.0,
            metrics={},
        )

        assert result.metrics == {}
