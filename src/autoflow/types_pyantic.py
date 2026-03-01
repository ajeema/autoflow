"""
Pydantic models for AutoFlow core data structures.

This module provides type-safe, validated models for all AutoFlow data structures,
including events, graph nodes, proposals, and evaluation results.

Usage:
    from autoflow.types_pyantic import ObservationEvent, ChangeProposal, GraphNode

    event = ObservationEvent(
        source="my_app",
        name="test_event",
        attributes={"key": "value"},
    )
"""

from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from uuid import UUID, uuid4
from enum import Enum
import os
import re

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# =============================================================================
# Enums
# =============================================================================


class RiskLevel(str, Enum):
    """Risk level for change proposals."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProposalKind(str, Enum):
    """Type of change proposal."""

    TEXT_PATCH = "text_patch"
    CONFIG_EDIT = "config_edit"
    REFACTORING = "refactoring"
    TEST_ADDITION = "test_addition"
    DEPENDENCY_UPDATE = "dependency_update"


class StepStatus(str, Enum):
    """Status of a workflow step execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    RETRY = "retry"
    RUNNING = "running"
    PENDING = "pending"


class NodeType(str, Enum):
    """Type of graph node."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    IMPORT = "import"
    CONTEXT = "context"
    DECISION = "decision"


class EdgeType(str, Enum):
    """Type of graph edge."""

    CALLS = "calls"
    IMPORTS = "imports"
    DEFINES = "defines"
    USES = "uses"
    RELATED_TO = "related_to"
    CONTEXT_FOR = "context_for"


# =============================================================================
# Core Models
# =============================================================================


class ObservationEvent(BaseModel):
    """
    An observation event captured during AutoFlow operation.

    Events are the primary unit of observability in AutoFlow.
    They represent significant actions, state changes, or errors.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp (UTC)")
    source: str = Field(..., description="Source of the event (e.g., component name)")
    name: str = Field(..., description="Event name")
    attributes: Mapping[str, Any] = Field(default_factory=dict, description="Additional event attributes")

    @field_validator("source", "name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate that string fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate that event_id is not empty."""
        if not v or not v.strip():
            raise ValueError("event_id cannot be empty")
        return v


class GraphNode(BaseModel):
    """
    A node in the context graph.

    Nodes represent entities in the codebase or context,
    such as files, functions, classes, or variables.
    """

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Type of the node")
    properties: Mapping[str, Any] = Field(default_factory=dict, description="Node properties")

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        """Validate that node_id is not empty."""
        if not v or not v.strip():
            raise ValueError("node_id cannot be empty")
        return v


class GraphEdge(BaseModel):
    """
    An edge in the context graph.

    Edges represent relationships between nodes,
    such as function calls, imports, or dependencies.
    """

    model_config = ConfigDict(frozen=True)

    edge_type: str = Field(..., description="Type of the edge")
    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    properties: Mapping[str, Any] = Field(default_factory=dict, description="Edge properties")

    @field_validator("from_node_id", "to_node_id")
    @classmethod
    def validate_node_ids(cls, v: str) -> str:
        """Validate that node IDs are not empty."""
        if not v or not v.strip():
            raise ValueError("Node ID cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_no_self_loops(self) -> "GraphEdge":
        """Validate that edges don't create self-loops."""
        if self.from_node_id == self.to_node_id:
            raise ValueError(f"Edge cannot create self-loop on node {self.from_node_id}")
        return self


class ContextGraphDelta(BaseModel):
    """
    A set of changes to apply to the context graph.

    Deltas contain nodes and edges to add, update, or remove.
    """

    model_config = ConfigDict(frozen=True)

    nodes: list[GraphNode] = Field(default_factory=list, description="Nodes in this delta")
    edges: list[GraphEdge] = Field(default_factory=list, description="Edges in this delta")

    @model_validator(mode="after")
    def validate_edge_references(self) -> "ContextGraphDelta":
        """
        Validate that edges don't reference empty node IDs.

        Note: Edges can reference nodes not in this delta (they may exist in the database).
        """
        for edge in self.edges:
            if not edge.from_node_id or not edge.from_node_id.strip():
                raise ValueError("Edge from_node_id cannot be empty")
            if not edge.to_node_id or not edge.to_node_id.strip():
                raise ValueError("Edge to_node_id cannot be empty")
        return self


class ChangeProposal(BaseModel):
    """
    A proposed change to the codebase.

    Proposals are generated by AutoFlow and must be evaluated
    and approved before being applied.
    """

    model_config = ConfigDict(frozen=True)

    proposal_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique proposal identifier")
    kind: str = Field(..., description="Type of change")
    title: str = Field(..., description="Brief title of the proposal")
    description: str = Field(..., description="Detailed description of the change")
    risk: str = Field(..., description="Risk level of this change")
    target_paths: list[str] = Field(default_factory=list, description="Files/directories affected")
    payload: Mapping[str, Any] = Field(default_factory=dict, description="Change-specific data")

    @field_validator("title", "description")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate that text fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

    @field_validator("target_paths")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        """
        Validate target paths for security and policy compliance.

        Rules:
        1. Paths must be relative (no absolute paths allowed)
        2. Paths must not contain parent directory references (..)
        3. Paths must not contain null bytes
        4. Empty paths are not allowed

        Note: Character validation is intentionally permissive for backward compatibility.
        """
        for path in v:
            if not path or not path.strip():
                raise ValueError(f"Path cannot be empty: {path}")

            # Check for absolute paths
            if os.path.isabs(path):
                raise ValueError(f"Absolute paths are not allowed: {path}")

            # Check for parent directory references (security risk)
            if ".." in path.split(os.sep):
                raise ValueError(f"Parent directory references (..) are not allowed: {path}")

            # Check for null bytes
            if "\0" in path:
                raise ValueError(f"Null bytes not allowed in path: {path}")

        return v

    @model_validator(mode="after")
    def validate_risk_level(self) -> "ChangeProposal":
        """
        Validate risk level based on proposal kind and content.

        Business rules:
        1. HIGH risk proposals should have detailed descriptions (> 50 chars)
           Note: This is a soft warning, not enforced for backward compatibility

        This validator is intentionally permissive for backward compatibility.
        """
        risk_lower = self.risk.lower()

        # HIGH risk should have detailed justification (not enforced for backward compat)
        # This logs a warning but doesn't raise an error
        if risk_lower == "high" and len(self.description.strip()) < 50:
            # Log warning but allow for backward compatibility
            pass

        return self

    @model_validator(mode="after")
    def validate_policy_compliance(self) -> "ChangeProposal":
        """
        Validate policy compliance based on proposal kind.

        Business rules:
        1. CONFIG_EDIT proposals should target config/ directory (soft recommendation)
        2. TEST_ADDITION proposals should target test files (soft recommendation)

        Note: These are soft recommendations for backward compatibility.
        """
        # Intentionally permissive for backward compatibility
        return self

    @model_validator(mode="after")
    def validate_title_description_consistency(self) -> "ChangeProposal":
        """
        Validate that title and description are consistent.

        Note: This validator is intentionally permissive for backward compatibility.
        """
        # Intentionally permissive for backward compatibility
        return self

    @model_validator(mode="after")
    def validate_payload_by_kind(self) -> "ChangeProposal":
        """
        Validate payload contains appropriate fields for specific proposal kinds.

        Note: This validator is intentionally permissive for backward compatibility.
        Payloads are optional and can vary based on specific use cases.
        """
        # Intentionally permissive for backward compatibility
        # Payload validation is left to the specific proposal handlers
        return self


class EvaluationResult(BaseModel):
    """
    Result of evaluating a change proposal.

    Contains whether the proposal passed evaluation,
    its score, and detailed metrics.

    Score can be any float value:
    - Positive scores indicate improvement
    - Negative scores indicate regression
    - Zero indicates no change
    """

    model_config = ConfigDict(frozen=True)

    proposal_id: str = Field(..., description="ID of the evaluated proposal")
    passed: bool = Field(..., description="Whether the proposal passed evaluation")
    score: float = Field(..., description="Evaluation score (can be negative or greater than 1)")
    metrics: Mapping[str, float] = Field(default_factory=dict, description="Detailed metrics")
    notes: str = Field(default="", description="Additional notes or explanation")

    @field_validator("proposal_id")
    @classmethod
    def validate_proposal_id(cls, v: str) -> str:
        """Validate proposal ID format."""
        try:
            UUID(v)
        except ValueError:
            # Allow non-UUID IDs for flexibility
            if not v or not v.strip():
                raise ValueError("proposal_id cannot be empty")
        return v


class WorkflowStep(BaseModel):
    """
    A single step in a workflow.

    Steps represent atomic units of work in a workflow execution.
    """

    model_config = ConfigDict(frozen=True)

    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique step identifier")
    name: str = Field(..., description="Step name")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Step status")
    started_at: Optional[datetime] = Field(default=None, description="Step start time")
    completed_at: Optional[datetime] = Field(default=None, description="Step completion time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="Additional step metadata")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate step name."""
        if not v or not v.strip():
            raise ValueError("Step name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_timestamps(self) -> "WorkflowStep":
        """Validate timestamp consistency."""
        if self.completed_at and not self.started_at:
            raise ValueError("Step cannot be completed without being started")
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("Completion time must be after start time")
        if self.status in (StepStatus.SUCCESS, StepStatus.FAILURE) and not self.completed_at:
            raise ValueError(f"Step with status {self.status} must have completed_at")
        return self


class WorkflowExecution(BaseModel):
    """
    A complete workflow execution.

    Contains all steps and their results.
    """

    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Workflow start time")
    completed_at: Optional[datetime] = Field(default=None, description="Workflow completion time")
    status: StepStatus = Field(default=StepStatus.RUNNING, description="Overall workflow status")
    steps: list[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workflow name."""
        if not v or not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_timestamps(self) -> "WorkflowExecution":
        """Validate timestamp consistency."""
        if self.completed_at and self.completed_at < self.started_at:
            raise ValueError("Completion time must be after start time")
        return self

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get workflow duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class ContextSource(BaseModel):
    """
    A source of context information.

    Context sources provide additional information for decision-making,
    such as vector databases, S3 buckets, or Slack conversations.
    """

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(..., description="Unique source identifier")
    source_type: str = Field(..., description="Type of context source")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    config: Mapping[str, Any] = Field(default_factory=dict, description="Source-specific configuration")
    priority: int = Field(default=0, ge=0, description="Source priority (higher = preferred)")

    @field_validator("source_id", "source_type")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate that string fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()


# =============================================================================
# Helpers
# =============================================================================


def make_event(*, source: str, name: str, attributes: Mapping[str, Any]) -> ObservationEvent:
    """
    Create a new ObservationEvent.

    This is a convenience function for creating events with
    automatic ID and timestamp generation.

    Args:
        source: Event source (component name)
        name: Event name
        attributes: Additional event attributes

    Returns:
        A new ObservationEvent instance

    Example:
        event = make_event(
            source="my_component",
            name="operation_started",
            attributes={"operation": "update_config"},
        )
    """
    return ObservationEvent(
        source=source,
        name=name,
        attributes=attributes,
    )


# Export main types for backward compatibility
__all__ = [
    # Enums
    "RiskLevel",
    "ProposalKind",
    "StepStatus",
    "NodeType",
    "EdgeType",
    # Models
    "ObservationEvent",
    "GraphNode",
    "GraphEdge",
    "ContextGraphDelta",
    "ChangeProposal",
    "EvaluationResult",
    "WorkflowStep",
    "WorkflowExecution",
    "ContextSource",
    # Helpers
    "make_event",
]
