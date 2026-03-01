"""Tests for observation collector module."""

import pytest

from autoflow.observe.collector import ObservationSink, InMemorySink
from autoflow.observe.events import make_event
from autoflow.types import ObservationEvent


class TestObservationSink:
    """Tests for ObservationSink protocol."""

    def test_protocol_has_write_method(self):
        """Test that ObservationSink protocol requires write method."""

        class CustomSink:
            def write(self, events):
                pass

        # Should be compatible with protocol
        sink: ObservationSink = CustomSink()
        assert hasattr(sink, "write")
        assert callable(sink.write)

    def test_protocol_write_accepts_events_sequence(self):
        """Test that write accepts sequence of events."""

        class TestSink:
            def write(self, events):
                return events

        sink = TestSink()
        events = [
            make_event(source="test", name="event1", attributes={}),
            make_event(source="test", name="event2", attributes={}),
        ]

        result = sink.write(events)
        assert len(result) == 2


class TestInMemorySink:
    """Tests for InMemorySink."""

    def test_initialization(self):
        """Test that InMemorySink initializes with empty events list."""
        sink = InMemorySink()

        assert hasattr(sink, "events")
        assert isinstance(sink.events, list)
        assert len(sink.events) == 0

    def test_write_single_event(self):
        """Test writing a single event to sink."""
        sink = InMemorySink()
        event = make_event(source="test", name="test_event", attributes={"key": "value"})

        sink.write([event])

        assert len(sink.events) == 1
        assert sink.events[0] is event
        assert sink.events[0].source == "test"
        assert sink.events[0].name == "test_event"

    def test_write_multiple_events(self):
        """Test writing multiple events to sink."""
        sink = InMemorySink()
        events = [
            make_event(source="app", name="request", attributes={"path": "/api"}),
            make_event(source="db", name="query", attributes={"sql": "SELECT *"}),
            make_event(source="cache", name="hit", attributes={"key": "user:123"}),
        ]

        sink.write(events)

        assert len(sink.events) == 3
        assert sink.events[0].source == "app"
        assert sink.events[1].source == "db"
        assert sink.events[2].source == "cache"

    def test_write_appends_to_existing_events(self):
        """Test that write appends to existing events."""
        sink = InMemorySink()

        # First write
        events1 = [
            make_event(source="test", name="event1", attributes={}),
        ]
        sink.write(events1)
        assert len(sink.events) == 1

        # Second write should append
        events2 = [
            make_event(source="test", name="event2", attributes={}),
            make_event(source="test", name="event3", attributes={}),
        ]
        sink.write(events2)
        assert len(sink.events) == 3
        assert sink.events[0].name == "event1"
        assert sink.events[1].name == "event2"
        assert sink.events[2].name == "event3"

    def test_write_empty_sequence(self):
        """Test writing empty sequence doesn't add events."""
        sink = InMemorySink()

        sink.write([])

        assert len(sink.events) == 0

    def test_write_preserves_event_attributes(self):
        """Test that write preserves all event attributes."""
        sink = InMemorySink()
        event = make_event(
            source="application",
            name="user_action",
            attributes={
                "user_id": "12345",
                "action": "click",
                "timestamp": 1234567890,
                "nested": {"key": "value"},
            },
        )

        sink.write([event])

        assert len(sink.events) == 1
        stored_event = sink.events[0]
        assert stored_event.source == "application"
        assert stored_event.name == "user_action"
        assert stored_event.attributes["user_id"] == "12345"
        assert stored_event.attributes["action"] == "click"
        assert stored_event.attributes["nested"]["key"] == "value"

    def test_write_stores_event_references(self):
        """Test that write stores actual event objects, not copies."""
        sink = InMemorySink()
        event = make_event(source="test", name="test_event", attributes={"count": 0})

        sink.write([event])

        # Modify original event
        event.attributes["count"] = 100

        # Sink should reference the same object
        assert sink.events[0].attributes["count"] == 100

    def test_write_with_complex_attributes(self):
        """Test writing events with complex attribute types."""
        sink = InMemorySink()
        event = make_event(
            source="test",
            name="complex_event",
            attributes={
                "list": [1, 2, 3],
                "dict": {"nested": {"deep": "value"}},
                "none": None,
                "bool": True,
                "float": 3.14,
            },
        )

        sink.write([event])

        assert len(sink.events) == 1
        attrs = sink.events[0].attributes
        assert attrs["list"] == [1, 2, 3]
        assert attrs["dict"]["nested"]["deep"] == "value"
        assert attrs["none"] is None
        assert attrs["bool"] is True
        assert attrs["float"] == 3.14

    def test_multiple_independent_sinks(self):
        """Test that multiple InMemorySink instances are independent."""
        sink1 = InMemorySink()
        sink2 = InMemorySink()

        event1 = make_event(source="sink1", name="event1", attributes={})
        event2 = make_event(source="sink2", name="event2", attributes={})

        sink1.write([event1])
        sink2.write([event2])

        assert len(sink1.events) == 1
        assert len(sink2.events) == 1
        assert sink1.events[0].source == "sink1"
        assert sink2.events[0].source == "sink2"

    def test_write_large_batch(self):
        """Test writing a large batch of events."""
        sink = InMemorySink()

        # Create 1000 events
        events = [
            make_event(source="test", name=f"event_{i}", attributes={"index": i})
            for i in range(1000)
        ]

        sink.write(events)

        assert len(sink.events) == 1000
        assert sink.events[0].name == "event_0"
        assert sink.events[999].name == "event_999"
        assert sink.events[500].attributes["index"] == 500

    def test_sink_compatibility_with_protocol(self):
        """Test that InMemorySink implements ObservationSink protocol."""
        sink: ObservationSink = InMemorySink()

        # Should work as ObservationSink
        events = [make_event(source="test", name="test", attributes={})]
        sink.write(events)

        assert isinstance(sink, InMemorySink)


class TestCollectorIntegration:
    """Integration tests for collector module."""

    def test_sink_as_callback(self):
        """Test using sink as a callback for event processing."""
        sink = InMemorySink()

        def process_events(source, name, count):
            events = [
                make_event(source=source, name=f"{name}_{i}", attributes={})
                for i in range(count)
            ]
            sink.write(events)

        # Simulate event processing
        process_events("app", "request", 5)
        process_events("db", "query", 3)

        assert len(sink.events) == 8
        assert sum(1 for e in sink.events if e.source == "app") == 5
        assert sum(1 for e in sink.events if e.source == "db") == 3

    def test_collecting_events_from_multiple_sources(self):
        """Test collecting events from different sources."""
        sink = InMemorySink()

        sources = ["application", "database", "cache", "queue"]
        for source in sources:
            events = [
                make_event(source=source, name="event", attributes={"source": source})
            ]
            sink.write(events)

        assert len(sink.events) == 4
        collected_sources = {e.source for e in sink.events}
        assert collected_sources == set(sources)

    def test_event_ordering_preserved(self):
        """Test that write preserves event order."""
        sink = InMemorySink()

        events = [
            make_event(source="test", name="first", attributes={"order": 1}),
            make_event(source="test", name="second", attributes={"order": 2}),
            make_event(source="test", name="third", attributes={"order": 3}),
        ]

        sink.write(events)

        assert sink.events[0].attributes["order"] == 1
        assert sink.events[1].attributes["order"] == 2
        assert sink.events[2].attributes["order"] == 3
