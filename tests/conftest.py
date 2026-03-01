"""Pytest configuration and fixtures."""

from pathlib import Path
from datetime import datetime
import pytest

from autoflow.observe.events import make_event
from autoflow.types import StepStatus


@pytest.fixture
def tmp_path(tmp_path: Path) -> Path:
    """Create a temporary path for tests."""
    return Path(tmp_path)


@pytest.fixture
def sample_events():
    """Create sample observation events for testing."""
    return [
        make_event(
            source="test_app",
            name="request_processed",
            attributes={
                "user_id": "user_123",
                "success": True,
                "latency_ms": 150,
            },
        ),
        make_event(
            source="test_app",
            name="request_error",
            attributes={
                "user_id": "user_456",
                "success": False,
                "error_type": "timeout",
                "latency_ms": 5000,
            },
        ),
        make_event(
            source="database",
            name="query_executed",
            attributes={
                "query": "SELECT * FROM users",
                "latency_ms": 50,
                "rows_returned": 100,
            },
        ),
    ]


@pytest.fixture
def sample_workflow_events():
    """Create sample workflow step events."""
    return [
        make_event(
            source="workflow_engine",
            name="step_execution",
            attributes={
                "workflow_id": "etl_pipeline",
                "workflow_run_id": "run_001",
                "step_name": "extract",
                "step_id": "run_001_step_1",
                "step_order": 1,
                "status": StepStatus.SUCCESS.value,
                "latency_ms": 500,
            },
        ),
        make_event(
            source="workflow_engine",
            name="step_execution",
            attributes={
                "workflow_id": "etl_pipeline",
                "workflow_run_id": "run_001",
                "step_name": "transform",
                "step_id": "run_001_step_2",
                "step_order": 2,
                "status": StepStatus.SUCCESS.value,
                "latency_ms": 1200,
            },
        ),
        make_event(
            source="workflow_engine",
            name="step_execution",
            attributes={
                "workflow_id": "etl_pipeline",
                "workflow_run_id": "run_001",
                "step_name": "load",
                "step_id": "run_001_step_3",
                "step_order": 3,
                "status": StepStatus.FAILURE.value,
                "latency_ms": 800,
                "error_type": "timeout",
            },
        ),
    ]


@pytest.fixture
def sample_nodes():
    """Create sample graph nodes."""
    from autoflow.types import GraphNode

    return [
        GraphNode(
            node_id="node_1",
            node_type="event",
            properties={"source": "test", "name": "event1", "value": 10},
        ),
        GraphNode(
            node_id="node_2",
            node_type="event",
            properties={"source": "test", "name": "event2", "value": 20},
        ),
        GraphNode(
            node_id="node_3",
            node_type="event",
            properties={"source": "test", "name": "event3", "value": 30},
        ),
    ]


@pytest.fixture
def sample_edges():
    """Create sample graph edges."""
    from autoflow.types import GraphEdge

    return [
        GraphEdge(
            edge_type="next_step",
            from_node_id="node_1",
            to_node_id="node_2",
            properties={"order": 1},
        ),
        GraphEdge(
            edge_type="next_step",
            from_node_id="node_2",
            to_node_id="node_3",
            properties={"order": 2},
        ),
    ]
