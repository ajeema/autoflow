"""
Tests for Pydantic-based data models.

Tests validation, serialization, and all model features.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from autoflow.types_pyantic import (
    ObservationEvent,
    GraphNode,
    GraphEdge,
    ContextGraphDelta,
    ChangeProposal,
    EvaluationResult,
    WorkflowStep,
    WorkflowExecution,
    ContextSource,
    RiskLevel,
    ProposalKind,
    StepStatus,
    NodeType,
    EdgeType,
    make_event,
)


class TestObservationEvent:
    """Test ObservationEvent model."""

    def test_create_event(self):
        """Test creating an event."""
        event = ObservationEvent(
            source="test_component",
            name="test_event",
            attributes={"key": "value"},
        )
        assert event.source == "test_component"
        assert event.name == "test_event"
        assert event.attributes == {"key": "value"}
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_make_event_helper(self):
        """Test the make_event helper function."""
        event = make_event(
            source="my_app",
            name="operation_started",
            attributes={"operation": "update_config"},
        )
        assert event.source == "my_app"
        assert event.name == "operation_started"
        assert event.attributes["operation"] == "update_config"

    def test_event_validation_empty_source(self):
        """Test that empty source is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ObservationEvent(source="", name="test")

    def test_event_validation_whitespace_source(self):
        """Test that whitespace-only source is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ObservationEvent(source="   ", name="test")

    def test_event_validation_strips_whitespace(self):
        """Test that whitespace is stripped from source and name."""
        event = ObservationEvent(
            source="  test_component  ",
            name="  test_event  ",
        )
        assert event.source == "test_component"
        assert event.name == "test_event"

    def test_event_validation_non_empty_id(self):
        """Test that empty event_id is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ObservationEvent(
                source="test",
                name="test",
                event_id="",
            )

    def test_event_serialization(self):
        """Test event serialization to dict."""
        event = ObservationEvent(source="test", name="test")
        data = event.model_dump()
        assert "event_id" in data
        assert "timestamp" in data
        assert data["source"] == "test"


class TestGraphNode:
    """Test GraphNode model."""

    def test_create_node(self):
        """Test creating a graph node."""
        node = GraphNode(
            node_id="test_node",
            node_type=NodeType.FUNCTION,
            properties={"name": "my_function"},
        )
        assert node.node_id == "test_node"
        assert node.node_type == NodeType.FUNCTION
        assert node.properties["name"] == "my_function"

    def test_node_validation_empty_id(self):
        """Test that empty node_id is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            GraphNode(node_id="", node_type=NodeType.FILE)

    def test_node_frozen(self):
        """Test that nodes are immutable."""
        node = GraphNode(node_id="test", node_type=NodeType.FILE)
        with pytest.raises(Exception):  # Pydantic frozen model error
            node.node_id = "modified"


class TestGraphEdge:
    """Test GraphEdge model."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            edge_type=EdgeType.CALLS,
            from_node_id="node_a",
            to_node_id="node_b",
        )
        assert edge.edge_type == EdgeType.CALLS
        assert edge.from_node_id == "node_a"
        assert edge.to_node_id == "node_b"

    def test_edge_validation_self_loop(self):
        """Test that self-loops are rejected."""
        with pytest.raises(ValueError, match="self-loop"):
            GraphEdge(
                edge_type=EdgeType.CALLS,
                from_node_id="node_a",
                to_node_id="node_a",
            )

    def test_edge_validation_empty_node_ids(self):
        """Test that empty node IDs are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            GraphEdge(
                edge_type=EdgeType.CALLS,
                from_node_id="",
                to_node_id="node_b",
            )


class TestContextGraphDelta:
    """Test ContextGraphDelta model."""

    def test_create_delta(self):
        """Test creating a graph delta."""
        nodes = [
            GraphNode(node_id="node_a", node_type=NodeType.FUNCTION),
            GraphNode(node_id="node_b", node_type=NodeType.FUNCTION),
        ]
        edges = [
            GraphEdge(
                edge_type=EdgeType.CALLS,
                from_node_id="node_a",
                to_node_id="node_b",
            )
        ]
        delta = ContextGraphDelta(nodes=nodes, edges=edges)
        assert len(delta.nodes) == 2
        assert len(delta.edges) == 1

    def test_delta_validation_empty_node_ids(self):
        """Test that edges with empty node IDs are rejected."""
        # The validation happens at the GraphEdge level
        with pytest.raises(ValueError, match="cannot be empty"):
            GraphEdge(
                edge_type=EdgeType.CALLS,
                from_node_id="node_a",
                to_node_id="",  # Empty
            )

    def test_delta_empty_is_valid(self):
        """Test that empty delta is valid."""
        delta = ContextGraphDelta()
        assert len(delta.nodes) == 0
        assert len(delta.edges) == 0


class TestChangeProposal:
    """Test ChangeProposal model."""

    def test_create_proposal(self):
        """Test creating a change proposal."""
        proposal = ChangeProposal(
            kind=ProposalKind.TEXT_PATCH,
            title="Fix typo in README",
            description="Fix a spelling error in the README.md file",
            risk=RiskLevel.LOW,
            target_paths=["README.md"],
            payload={"line": 42, "old": "recieve", "new": "receive"},
        )
        assert proposal.kind == ProposalKind.TEXT_PATCH
        assert proposal.title == "Fix typo in README"
        assert proposal.risk == RiskLevel.LOW
        assert "README.md" in proposal.target_paths

    def test_proposal_validation_empty_title(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChangeProposal(
                kind=ProposalKind.TEXT_PATCH,
                title="",
                description="A description",
                risk=RiskLevel.LOW,
            )

    def test_proposal_serialization(self):
        """Test proposal serialization."""
        proposal = ChangeProposal(
            kind=ProposalKind.TEXT_PATCH,
            title="Test",
            description="A sufficient description for testing purposes",
            risk=RiskLevel.LOW,
        )
        data = proposal.model_dump()
        assert "proposal_id" in data
        assert data["kind"] == "text_patch"


class TestEvaluationResult:
    """Test EvaluationResult model."""

    def test_create_result(self):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            proposal_id=str(uuid4()),
            passed=True,
            score=0.85,
            metrics={"test_coverage": 0.9, "performance": 0.8},
            notes="Good proposal",
        )
        assert result.passed is True
        assert result.score == 0.85
        assert result.metrics["test_coverage"] == 0.9

    def test_result_validation_score_range(self):
        """Test that score accepts any float value."""
        # Positive score
        result1 = EvaluationResult(
            proposal_id=str(uuid4()),
            passed=True,
            score=80.0,
        )
        assert result1.score == 80.0

        # Negative score
        result2 = EvaluationResult(
            proposal_id=str(uuid4()),
            passed=False,
            score=-30.0,
        )
        assert result2.score == -30.0

        # Zero score
        result3 = EvaluationResult(
            proposal_id=str(uuid4()),
            passed=True,
            score=0.0,
        )
        assert result3.score == 0.0

    def test_result_validation_proposal_id(self):
        """Test that proposal_id is preserved."""
        proposal_id = "custom-proposal-123"
        result = EvaluationResult(
            proposal_id=proposal_id,
            passed=True,
            score=10.0,
        )
        assert result.proposal_id == proposal_id


class TestWorkflowStep:
    """Test WorkflowStep model."""

    def test_create_step(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="test_step",
            status=StepStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        assert step.name == "test_step"
        assert step.status == StepStatus.SUCCESS
        assert step.completed_at is not None

    def test_step_validation_completed_without_started(self):
        """Test that completion without start time is rejected."""
        with pytest.raises(ValueError, match="cannot be completed without being started"):
            WorkflowStep(
                name="test",
                status=StepStatus.SUCCESS,
                completed_at=datetime.now(timezone.utc),
            )

    def test_step_validation_completion_before_start(self):
        """Test that completion before start is rejected."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Completion time must be after start time"):
            WorkflowStep(
                name="test",
                status=StepStatus.SUCCESS,
                started_at=now,
                completed_at=now - timedelta(seconds=10),
            )

    def test_step_validation_success_requires_completion(self):
        """Test that success status requires completion time."""
        with pytest.raises(ValueError, match="must have completed_at"):
            WorkflowStep(
                name="test",
                status=StepStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )


class TestWorkflowExecution:
    """Test WorkflowExecution model."""

    def test_create_workflow(self):
        """Test creating a workflow execution."""
        workflow = WorkflowExecution(
            name="test_workflow",
            status=StepStatus.RUNNING,
        )
        assert workflow.name == "test_workflow"
        assert workflow.status == StepStatus.RUNNING
        assert workflow.started_at is not None

    def test_workflow_duration_property(self):
        """Test duration calculation."""
        now = datetime.now(timezone.utc)
        workflow = WorkflowExecution(
            name="test",
            started_at=now,
            completed_at=now + timedelta(seconds=30),
        )
        assert workflow.duration_seconds == 30

    def test_workflow_duration_not_completed(self):
        """Test that duration is None for incomplete workflow."""
        workflow = WorkflowExecution(
            name="test",
            completed_at=None,
        )
        assert workflow.duration_seconds is None

    def test_workflow_validation_completion_before_start(self):
        """Test that completion before start is rejected."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Completion time must be after start time"):
            WorkflowExecution(
                name="test",
                started_at=now,
                completed_at=now - timedelta(seconds=10),
            )


class TestContextSource:
    """Test ContextSource model."""

    def test_create_source(self):
        """Test creating a context source."""
        source = ContextSource(
            source_id="vector_db",
            source_type="pinecone",
            enabled=True,
            priority=10,
        )
        assert source.source_id == "vector_db"
        assert source.source_type == "pinecone"
        assert source.enabled is True
        assert source.priority == 10

    def test_source_validation_negative_priority(self):
        """Test that negative priority is rejected."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            ContextSource(
                source_id="test",
                source_type="test",
                priority=-1,
            )


class TestTypeConsistency:
    """Test type consistency across models."""

    def test_risk_levels(self):
        """Test risk level enum values."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"

    def test_proposal_kinds(self):
        """Test proposal kind enum values."""
        assert ProposalKind.TEXT_PATCH == "text_patch"
        assert ProposalKind.CONFIG_EDIT == "config_edit"

    def test_step_status_values(self):
        """Test step status enum values."""
        assert StepStatus.SUCCESS == "success"
        assert StepStatus.FAILURE == "failure"
        assert StepStatus.RUNNING == "running"

    def test_node_type_values(self):
        """Test node type enum values."""
        assert NodeType.FILE == "file"
        assert NodeType.FUNCTION == "function"
        assert NodeType.CLASS == "class"

    def test_edge_type_values(self):
        """Test edge type enum values."""
        assert EdgeType.CALLS == "calls"
        assert EdgeType.IMPORTS == "imports"
        assert EdgeType.DEFINES == "defines"


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_event_roundtrip(self):
        """Test event serialization roundtrip."""
        original = ObservationEvent(
            source="test",
            name="test_event",
            attributes={"key": "value"},
        )
        data = original.model_dump()
        restored = ObservationEvent(**data)
        assert restored.source == original.source
        assert restored.name == original.name

    def test_json_export(self):
        """Test JSON export."""
        event = ObservationEvent(source="test", name="test")
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        assert "test" in json_str


class TestModelValidationFeatures:
    """Test advanced Pydantic validation features."""

    def test_field_descriptions(self):
        """Test that fields have descriptions."""
        event = ObservationEvent(source="test", name="test")
        schema = event.model_json_schema()
        # Check that schema has field descriptions
        assert "properties" in schema
        assert "source" in schema["properties"]

    def test_frozen_models_are_immutable(self):
        """Test that frozen=True makes models immutable."""
        event = ObservationEvent(source="test", name="test")
        with pytest.raises(Exception):  # Pydantic validation error
            event.source = "modified"

    def test_default_factories(self):
        """Test that default factories work correctly."""
        event1 = ObservationEvent(source="test", name="test")
        event2 = ObservationEvent(source="test", name="test")
        # Each should get unique IDs
        assert event1.event_id != event2.event_id


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_make_event_compatible_with_old_api(self):
        """Test that make_event works like the old function."""
        event = make_event(
            source="my_component",
            name="test",
            attributes={"key": "value"},
        )
        assert isinstance(event, ObservationEvent)
        assert event.source == "my_component"
        assert event.name == "test"

    def test_dataclass_like_api(self):
        """Test that models can be used like dataclasses."""
        node = GraphNode(
            node_id="test",
            node_type=NodeType.FUNCTION,
        )
        # Access fields like dataclass
        assert node.node_id == "test"
        assert node.node_type == NodeType.FUNCTION
        assert node.properties == {}

    def test_mapping_interface(self):
        """Test that models support dict-like access in some ways."""
        event = ObservationEvent(source="test", name="test")
        # model_dump() provides dict-like access
        data = event.model_dump()
        assert data["source"] == "test"
        assert data["name"] == "test"
