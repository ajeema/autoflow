"""
Pydantic models for API request/response validation.

This module provides request and response models for AutoFlow's HTTP API,
ensuring type safety and automatic validation of all API data.

Usage:
    from autoflow.api_models import (
        ProposeRequest,
        ProposeResponse,
        EvaluateRequest,
        EvaluateResponse,
        ErrorResponse,
    )

    # In a FastAPI app
    @app.post("/api/v1/propose", response_model=ProposeResponse)
    async def propose(request: ProposeRequest):
        # Request is automatically validated
        result = engine.propose(**request.model_dump())
        return ProposeResponse.from_result(result)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Base Response Models
# =============================================================================


class Meta(BaseModel):
    """Metadata included in API responses."""

    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Error response returned when API calls fail."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


# =============================================================================
# Request Models
# =============================================================================


class ProposeRequest(BaseModel):
    """
    Request to generate change proposals.

    The engine will analyze the context and generate proposals
    for improvements.
    """

    context: Dict[str, Any] = Field(
        ...,
        description="Context data for proposal generation",
    )
    max_proposals: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of proposals to generate",
    )
    max_risk: Optional[str] = Field(
        default="medium",
        description="Maximum risk level for proposals",
    )
    include_reasoning: bool = Field(
        default=False,
        description="Include explanation for each proposal",
    )


class EvaluateRequest(BaseModel):
    """Request to evaluate a change proposal."""

    proposal: Dict[str, Any] = Field(
        ...,
        description="The proposal to evaluate",
    )
    evaluator_type: str = Field(
        default="shadow",
        description="Type of evaluator to use",
    )
    dataset: Optional[Dict[str, Any]] = Field(
        None,
        description="Dataset for replay evaluation",
    )
    gates: Optional[List[str]] = Field(
        None,
        description="Evaluation gates to apply",
    )


class ApplyRequest(BaseModel):
    """Request to apply a change proposal."""

    proposal_id: str = Field(
        ...,
        description="ID of the proposal to apply",
    )
    dry_run: bool = Field(
        default=True,
        description="Preview changes without applying",
    )
    force: bool = Field(
        default=False,
        description="Apply even if policy checks fail",
    )


class QueryGraphRequest(BaseModel):
    """Request to query the context graph."""

    query_type: str = Field(
        ...,
        description="Type of query (nodes, edges, paths)",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Query filters",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum results to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip",
    )


class IngestEventsRequest(BaseModel):
    """Request to ingest observation events."""

    events: List[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="Events to ingest (max 1000 at once)",
    )

    @field_validator("events")
    @classmethod
    def validate_events_not_empty(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate that events list is not empty."""
        if not v:
            raise ValueError("Events list cannot be empty")
        return v


class GetStatusRequest(BaseModel):
    """Request to get AutoFlow engine status."""

    include_metrics: bool = Field(
        default=False,
        description="Include performance metrics",
    )
    include_config: bool = Field(
        default=False,
        description="Include configuration details",
    )


# =============================================================================
# Response Models
# =============================================================================


class ProposalResponse(BaseModel):
    """A single change proposal in API responses."""

    proposal_id: str = Field(..., description="Unique proposal identifier")
    kind: str = Field(..., description="Type of change")
    title: str = Field(..., description="Proposal title")
    description: str = Field(..., description="Detailed description")
    risk: str = Field(..., description="Risk level")
    target_paths: List[str] = Field(..., description="Affected files")
    reasoning: Optional[str] = Field(None, description="Explanation for the proposal")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")


class ProposeResponse(BaseModel):
    """Response to a proposal generation request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    proposals: List[ProposalResponse] = Field(
        ...,
        description="Generated proposals",
    )
    total_count: int = Field(
        ...,
        description="Total number of proposals generated",
    )
    context_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary of analyzed context",
    )


class EvaluationMetricResponse(BaseModel):
    """A single evaluation metric."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    baseline: Optional[float] = Field(None, description="Baseline value")
    improvement: Optional[float] = Field(None, description="Improvement over baseline")


class EvaluateResponse(BaseModel):
    """Response to an evaluation request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    proposal_id: str = Field(..., description="Evaluated proposal ID")
    passed: bool = Field(..., description="Whether evaluation passed")
    score: float = Field(..., description="Overall score")
    metrics: Dict[str, float] = Field(..., description="Detailed metrics")
    notes: str = Field(default="", description="Additional notes")
    gates: Optional[List[str]] = Field(None, description="Gate results")


class ApplyResponse(BaseModel):
    """Response to an apply request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    proposal_id: str = Field(..., description="Applied proposal ID")
    success: bool = Field(..., description="Whether application succeeded")
    changes: List[Dict[str, Any]] = Field(
        ...,
        description="List of changes made",
    )
    summary: str = Field(..., description="Summary of changes")
    dry_run: bool = Field(..., description="Whether this was a dry run")


class GraphNodeResponse(BaseModel):
    """A graph node in API responses."""

    node_id: str = Field(..., description="Node identifier")
    node_type: str = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(..., description="Node properties")


class GraphEdgeResponse(BaseModel):
    """A graph edge in API responses."""

    edge_type: str = Field(..., description="Edge type")
    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    properties: Dict[str, Any] = Field(..., description="Edge properties")


class QueryGraphResponse(BaseModel):
    """Response to a graph query request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    nodes: List[GraphNodeResponse] = Field(
        ...,
        description="Query results (nodes)",
    )
    edges: List[GraphEdgeResponse] = Field(
        ...,
        description="Query results (edges)",
    )
    total_count: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Result limit used")
    offset: int = Field(..., description="Result offset used")


class IngestEventsResponse(BaseModel):
    """Response to an event ingestion request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    ingested_count: int = Field(..., description="Number of events ingested")
    failed_count: int = Field(default=0, description="Number of events that failed")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed events")


class StatusResponse(BaseModel):
    """Response to a status request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    status: str = Field(..., description="Engine status")
    version: str = Field(..., description="AutoFlow version")
    uptime_seconds: float = Field(..., description="Engine uptime in seconds")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration snapshot")


class WorkflowListResponse(BaseModel):
    """Response listing workflows."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    workflows: List[Dict[str, Any]] = Field(
        ...,
        description="List of workflows",
    )
    total_count: int = Field(..., description="Total number of workflows")


class WorkflowDetailResponse(BaseModel):
    """Response with workflow details."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    workflow_id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Workflow status")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# =============================================================================
# Pagination Models
# =============================================================================


class PaginatedResponse(BaseModel):
    """Base class for paginated responses."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    items: List[Any] = Field(..., description="Paginated items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=1000, description="Items per page")
    total_pages: int = Field(..., ge=1, description="Total number of pages")


# =============================================================================
# Batch Request Models
# =============================================================================


class BatchProposeRequest(BaseModel):
    """Request to generate proposals for multiple contexts."""

    contexts: List[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Contexts to process (max 10)",
    )
    max_proposals_per_context: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max proposals per context",
    )


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate multiple proposals."""

    proposals: List[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="Proposals to evaluate",
    )
    evaluator_type: str = Field(
        default="shadow",
        description="Type of evaluator to use",
    )


class BatchEvaluateResponse(BaseModel):
    """Response to batch evaluation request."""

    meta: Optional[Meta] = Field(None, description="Response metadata")
    results: List[EvaluateResponse] = Field(
        ...,
        description="Evaluation results",
    )
    total_count: int = Field(..., description="Total proposals evaluated")
    passed_count: int = Field(..., description="Number that passed")
    failed_count: int = Field(..., description="Number that failed")


# =============================================================================
# Export all models
# =============================================================================

__all__ = [
    # Base
    "Meta",
    "ErrorResponse",
    # Requests
    "ProposeRequest",
    "EvaluateRequest",
    "ApplyRequest",
    "QueryGraphRequest",
    "IngestEventsRequest",
    "GetStatusRequest",
    # Responses
    "ProposalResponse",
    "ProposeResponse",
    "EvaluationMetricResponse",
    "EvaluateResponse",
    "ApplyResponse",
    "GraphNodeResponse",
    "GraphEdgeResponse",
    "QueryGraphResponse",
    "IngestEventsResponse",
    "StatusResponse",
    "WorkflowListResponse",
    "WorkflowDetailResponse",
    # Pagination
    "PaginatedResponse",
    # Batch
    "BatchProposeRequest",
    "BatchEvaluateRequest",
    "BatchEvaluateResponse",
]
