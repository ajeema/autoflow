"""Tests for context graph module."""

import pytest

from autoflow.observe.events import make_event
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge


class TestContextGraphBuilder:
    """Tests for ContextGraphBuilder."""

    def test_build_delta_creates_nodes(self, sample_events):
        """Test that build_delta creates nodes from events."""
        builder = ContextGraphBuilder()
        delta = builder.build_delta(sample_events)

        assert isinstance(delta, ContextGraphDelta)
        assert len(delta.nodes) == len(sample_events)
        assert len(delta.edges) == 0  # Basic builder doesn't create edges

    def test_build_delta_node_properties(self, sample_events):
        """Test that node properties include event data."""
        builder = ContextGraphBuilder()
        delta = builder.build_delta(sample_events)

        for i, node in enumerate(delta.nodes):
            # node_id format is "event:{event_id}"
            assert "event:" in node.node_id
            assert node.properties["source"] == sample_events[i].source
            assert node.properties["name"] == sample_events[i].name

    def test_build_delta_empty_events(self):
        """Test build_delta with empty events list."""
        builder = ContextGraphBuilder()
        delta = builder.build_delta([])

        assert len(delta.nodes) == 0
        assert len(delta.edges) == 0


class TestSQLiteGraphStore:
    """Tests for SQLiteGraphStore."""

    def test_init_creates_tables(self, tmp_path):
        """Test that store initialization creates tables."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # Check nodes table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
        )
        assert cur.fetchone() is not None

        # Check edges table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='edges'"
        )
        assert cur.fetchone() is not None

        conn.close()

    def test_upsert_nodes(self, tmp_path, sample_nodes):
        """Test upserting nodes to the store."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        delta = ContextGraphDelta(nodes=sample_nodes, edges=[])
        store.upsert(delta)

        # Query nodes
        nodes = store.query_nodes()
        assert len(nodes) == len(sample_nodes)

    def test_upsert_edges(self, tmp_path, sample_edges):
        """Test upserting edges to the store."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        # First add nodes (foreign key constraint)
        from autoflow.types import GraphNode

        nodes = [
            GraphNode(
                node_id="node_1",
                node_type="test",
                properties={},
            ),
            GraphNode(
                node_id="node_2",
                node_type="test",
                properties={},
            ),
        ]

        store.upsert(ContextGraphDelta(nodes=nodes, edges=sample_edges))

        # Query edges
        edges = store.query_edges()
        assert len(edges) == len(sample_edges)

    def test_query_nodes_with_type_filter(self, tmp_path):
        """Test querying nodes with type filter."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        nodes = [
            GraphNode(
                node_id="node_1",
                node_type="event",
                properties={},
            ),
            GraphNode(
                node_id="node_2",
                node_type="metric",
                properties={},
            ),
        ]

        store.upsert(ContextGraphDelta(nodes=nodes, edges=[]))

        # Query all nodes
        all_nodes = store.query_nodes()
        assert len(all_nodes) == 2

        # Query by type
        event_nodes = store.query_nodes(node_type="event")
        assert len(event_nodes) == 1
        assert event_nodes[0].node_type == "event"

    def test_query_edges_with_type_filter(self, tmp_path, sample_edges):
        """Test querying edges with type filter."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        # Add nodes first
        nodes = [
            GraphNode(node_id="node_1", node_type="test", properties={}),
            GraphNode(node_id="node_2", node_type="test", properties={}),
            GraphNode(node_id="node_3", node_type="test", properties={}),
        ]

        store.upsert(ContextGraphDelta(nodes=nodes, edges=sample_edges))

        # Query all edges
        all_edges = store.query_edges()
        assert len(all_edges) == 2

        # Query by type
        next_step_edges = store.query_edges(edge_type="next_step")
        assert len(next_step_edges) == 2

    def test_query_limit(self, tmp_path):
        """Test query limit parameter."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        nodes = [
            GraphNode(node_id=f"node_{i}", node_type="test", properties={})
            for i in range(10)
        ]

        store.upsert(ContextGraphDelta(nodes=nodes, edges=[]))

        # Query with limit
        limited_nodes = store.query_nodes(limit=5)
        assert len(limited_nodes) == 5

    def test_node_properties_preserved(self, tmp_path):
        """Test that node properties are preserved when round-tripping."""
        db_path = tmp_path / "test.db"
        store = SQLiteGraphStore(db_path=str(db_path))

        original_node = GraphNode(
            node_id="test_node",
            node_type="test",
            properties={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "list": [1, 2, 3],
                "nested": {"key": "value"},
            },
        )

        store.upsert(ContextGraphDelta(nodes=[original_node], edges=[]))

        retrieved_nodes = store.query_nodes()
        assert len(retrieved_nodes) == 1

        retrieved = retrieved_nodes[0]
        assert retrieved.node_id == "test_node"
        assert retrieved.properties["string"] == "value"
        assert retrieved.properties["number"] == 42
        assert retrieved.properties["float"] == 3.14
        assert retrieved.properties["bool"] is True
        assert retrieved.properties["list"] == [1, 2, 3]
        assert retrieved.properties["nested"]["key"] == "value"
