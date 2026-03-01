"""Tests for API request/response models."""

import pytest
from datetime import datetime, timezone

from autoflow.api_models import (
    ProposeRequest,
    ProposeResponse,
    EvaluateRequest,
    EvaluateResponse,
    ApplyRequest,
    ApplyResponse,
    QueryGraphRequest,
    QueryGraphResponse,
    IngestEventsRequest,
    IngestEventsResponse,
    ErrorResponse,
    Meta,
)


class TestMeta:
    """Test Meta model."""

    def test_create_meta(self):
        """Test creating metadata."""
        meta = Meta(
            request_id="req-123",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
        )
        assert meta.request_id == "req-123"
        assert meta.version == "1.0.0"


class TestErrorResponse:
    """Test error response model."""

    def test_create_error_response(self):
        """Test creating error response."""
        error = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "title"},
        )
        assert error.error == "VALIDATION_ERROR"
        assert error.message == "Invalid input data"
        assert error.details["field"] == "title"


class TestProposeRequest:
    """Test proposal request model."""

    def test_create_request(self):
        """Test creating a valid request."""
        request = ProposeRequest(
            context={"file": "test.py", "content": "def foo(): pass"},
            max_proposals=5,
            max_risk="low",
            include_reasoning=True,
        )
        assert request.max_proposals == 5
        assert request.max_risk == "low"
        assert request.include_reasoning is True

    def test_default_values(self):
        """Test default values."""
        request = ProposeRequest(
            context={"file": "test.py"},
        )
        assert request.max_proposals == 10
        assert request.max_risk == "medium"
        assert request.include_reasoning is False

    def test_validation_max_proposals_too_high(self):
        """Test that max_proposals > 100 is rejected."""
        with pytest.raises(Exception):
            ProposeRequest(
                context={"file": "test.py"},
                max_proposals=101,
            )

    def test_validation_max_proposals_too_low(self):
        """Test that max_proposals < 1 is rejected."""
        with pytest.raises(Exception):
            ProposeRequest(
                context={"file": "test.py"},
                max_proposals=0,
            )


class TestEvaluateRequest:
    """Test evaluation request model."""

    def test_create_request(self):
        """Test creating a valid request."""
        request = EvaluateRequest(
            proposal={"proposal_id": "prop-1", "title": "Test"},
            evaluator_type="shadow",
        )
        assert request.evaluator_type == "shadow"

    def test_request_with_dataset(self):
        """Test request with dataset."""
        request = EvaluateRequest(
            proposal={"proposal_id": "prop-1"},
            evaluator_type="replay",
            dataset={"baseline": {"metric": 10}, "candidate": {"metric": 15}},
        )
        assert request.dataset is not None


class TestApplyRequest:
    """Test apply request model."""

    def test_create_request(self):
        """Test creating a valid request."""
        request = ApplyRequest(
            proposal_id="prop-123",
            dry_run=True,
            force=False,
        )
        assert request.proposal_id == "prop-123"
        assert request.dry_run is True


class TestQueryGraphRequest:
    """Test graph query request model."""

    def test_create_request(self):
        """Test creating a valid request."""
        request = QueryGraphRequest(
            query_type="nodes",
            filters={"node_type": "function"},
            limit=50,
            offset=0,
        )
        assert request.query_type == "nodes"
        assert request.filters["node_type"] == "function"
        assert request.limit == 50


class TestIngestEventsRequest:
    """Test event ingestion request model."""

    def test_create_request(self):
        """Test creating a valid request."""
        request = IngestEventsRequest(
            events=[
                {"source": "test", "name": "event1"},
                {"source": "test", "name": "event2"},
            ]
        )
        assert len(request.events) == 2

    def test_validation_empty_events(self):
        """Test that empty events list is rejected."""
        with pytest.raises(Exception):
            IngestEventsRequest(events=[])

    def test_validation_too_many_events(self):
        """Test that > 1000 events is rejected."""
        with pytest.raises(Exception):
            IngestEventsRequest(
                events=[{"source": "test", "name": f"event{i}"} for i in range(1001)]
            )


class TestResponseModels:
    """Test response models."""

    def test_propose_response(self):
        """Test ProposeResponse."""
        response = ProposeResponse(
            proposals=[],
            total_count=0,
            context_summary={"files": 1},
        )
        assert response.total_count == 0
        assert response.context_summary["files"] == 1

    def test_evaluate_response(self):
        """Test EvaluateResponse."""
        response = EvaluateResponse(
            proposal_id="prop-1",
            passed=True,
            score=85.0,
            metrics={"test_coverage": 0.9},
        )
        assert response.passed is True
        assert response.score == 85.0

    def test_apply_response(self):
        """Test ApplyResponse."""
        response = ApplyResponse(
            proposal_id="prop-1",
            success=True,
            changes=[{"file": "test.py", "operation": "modify"}],
            summary="Modified test.py",
            dry_run=True,
        )
        assert response.success is True
        assert response.dry_run is True

    def test_query_graph_response(self):
        """Test QueryGraphResponse."""
        response = QueryGraphResponse(
            nodes=[],
            edges=[],
            total_count=0,
            limit=100,
            offset=0,
        )
        assert response.total_count == 0
        assert response.limit == 100

    def test_ingest_events_response(self):
        """Test IngestEventsResponse."""
        response = IngestEventsResponse(
            ingested_count=100,
            failed_count=0,
            errors=[],
        )
        assert response.ingested_count == 100
        assert response.failed_count == 0


class TestModelSerialization:
    """Test model serialization for JSON APIs."""

    def test_propose_request_serialization(self):
        """Test that request models can be serialized."""
        request = ProposeRequest(
            context={"file": "test.py"},
            max_proposals=5,
        )
        data = request.model_dump()
        assert data["context"]["file"] == "test.py"
        assert data["max_proposals"] == 5

    def test_response_serialization(self):
        """Test that response models can be serialized."""
        response = EvaluateResponse(
            proposal_id="prop-1",
            passed=True,
            score=85.0,
            metrics={},
        )
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        assert "prop-1" in json_str


class TestRequestValidation:
    """Test automatic validation of requests."""

    def test_invalid_propose_request(self):
        """Test that invalid requests are rejected."""
        with pytest.raises(Exception):
            ProposeRequest(
                context=None,  # Missing required field
                max_proposals=5,
            )

    def test_invalid_query_graph_request(self):
        """Test that invalid graph queries are rejected."""
        with pytest.raises(Exception):
            QueryGraphRequest(
                query_type="",
                filters={},
                limit=0,  # Must be >= 1
            )
