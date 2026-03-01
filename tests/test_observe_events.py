"""Tests for observation events module."""

import pytest
from datetime import datetime
from uuid import UUID

from autoflow.observe.events import make_event
from autoflow.types import ObservationEvent, StepStatus


class TestMakeEvent:
    """Tests for make_event function."""

    def test_make_event_basic(self):
        """Test creating a basic event."""
        event = make_event(
            source="test_app",
            name="test_event",
            attributes={"key": "value"},
        )

        assert isinstance(event, ObservationEvent)
        assert event.source == "test_app"
        assert event.name == "test_event"
        assert event.attributes == {"key": "value"}
        assert isinstance(event.event_id, str)
        assert isinstance(event.timestamp, datetime)

    def test_make_event_with_uuid(self):
        """Test that event_id is a valid UUID string."""
        event = make_event(
            source="test",
            name="test",
            attributes={},
        )

        # Should be able to parse as UUID
        uuid = UUID(event.event_id)
        assert str(uuid) == event.event_id

    def test_make_event_with_nested_attributes(self):
        """Test event with nested attribute values."""
        event = make_event(
            source="test",
            name="test",
            attributes={
                "user": {"id": "123", "name": "Test User"},
                "tags": ["tag1", "tag2"],
                "count": 42,
            },
        )

        assert event.attributes["user"]["id"] == "123"
        assert event.attributes["tags"] == ["tag1", "tag2"]
        assert event.attributes["count"] == 42

    def test_make_event_immutability(self):
        """Test that events are immutable (frozen dataclass)."""
        event = make_event(
            source="test",
            name="test",
            attributes={"key": "value"},
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            event.source = "new_source"

    def test_make_event_empty_attributes(self):
        """Test event with empty attributes."""
        event = make_event(
            source="test",
            name="test",
            attributes={},
        )

        assert event.attributes == {}

    def test_make_event_workflow_step(self):
        """Test creating workflow step event."""
        event = make_event(
            source="workflow_engine",
            name="step_execution",
            attributes={
                "workflow_id": "test_workflow",
                "workflow_run_id": "run_001",
                "step_name": "extract",
                "step_id": "run_001_step_1",
                "step_order": 1,
                "status": StepStatus.SUCCESS.value,
                "latency_ms": 500,
            },
        )

        assert event.attributes["workflow_id"] == "test_workflow"
        assert event.attributes["status"] == "success"
        assert event.attributes["latency_ms"] == 500


class TestObservationEvent:
    """Tests for ObservationEvent type."""

    def test_event_equality(self):
        """Test event equality."""
        event1 = make_event(
            source="test",
            name="test",
            attributes={"key": "value"},
        )
        event2 = make_event(
            source="test",
            name="test",
            attributes={"key": "value"},
        )

        # Different event_ids, so not equal
        assert event1 != event2

    def test_event_fields(self):
        """Test all event fields are accessible."""
        event = make_event(
            source="my_app",
            name="my_event",
            attributes={"custom_field": "custom_value"},
        )

        assert hasattr(event, "event_id")
        assert hasattr(event, "timestamp")
        assert hasattr(event, "source")
        assert hasattr(event, "name")
        assert hasattr(event, "attributes")
        assert event.source == "my_app"
        assert event.name == "my_event"
        assert event.attributes["custom_field"] == "custom_value"
