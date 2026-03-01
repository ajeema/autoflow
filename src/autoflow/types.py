"""
AutoFlow type definitions.

This module provides type definitions for AutoFlow core data structures.
It now uses Pydantic models for type safety, validation, and serialization.

For backward compatibility, most imports work exactly as before.
New code should import directly from autoflow.types_pyantic for full Pydantic features.

Usage:
    # Old way (still works)
    from autoflow.types import ObservationEvent, GraphNode, ChangeProposal

    # New way (recommended - more features)
    from autoflow.types_pyantic import ObservationEvent, GraphNode, ChangeProposal
"""

# Import all Pydantic models for backward compatibility
from autoflow.types_pyantic import (
    # Enums
    RiskLevel,
    ProposalKind,
    StepStatus,
    NodeType,
    EdgeType,
    # Core Models
    ObservationEvent,
    GraphNode,
    GraphEdge,
    ContextGraphDelta,
    ChangeProposal,
    EvaluationResult,
    WorkflowStep,
    WorkflowExecution,
    ContextSource,
    # Helpers
    make_event,
)

# Re-export for backward compatibility
__all__ = [
    # Enums
    "RiskLevel",
    "ProposalKind",
    "StepStatus",
    "NodeType",
    "EdgeType",
    # Core Models
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
