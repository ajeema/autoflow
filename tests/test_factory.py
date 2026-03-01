"""Tests for the simplified AutoFlow factory API."""

import pytest
from pathlib import Path
import tempfile

from autoflow.factory import (
    autoflow,
    autoflow_testing,
    autoflow_persistent,
    autoflow_shadow,
    autoflow_auto_apply,
    autoflow_with_rules,
)
from autoflow.observe.events import make_event
from autoflow.types import ObservationEvent


class TestAutoflowFactory:
    """Tests for autoflow() factory function."""

    def test_autoflow_in_memory(self):
        """Test creating in-memory engine."""
        engine = autoflow(in_memory=True)

        # Should have ingest and propose methods
        assert hasattr(engine, 'ingest')
        assert hasattr(engine, 'propose')

        # Test basic usage (sync)
        events = [
            make_event(source="test", name="event1", attributes={"key": "value"}),
        ]
        engine.ingest(events)
        proposals = engine.propose()

        assert isinstance(proposals, list)

    def test_autoflow_with_custom_rules(self):
        """Test autoflow with custom rules."""
        from autoflow.decide.rules import HighErrorRateRetryRule

        engine = autoflow(
            in_memory=True,
            rules=[HighErrorRateRetryRule(workflow_id="test", threshold=2)]
        )

        # Ingest events that should trigger rule
        events = [
            make_event(source="test", name="exception", attributes={"workflow_id": "test"}),
            make_event(source="test", name="exception", attributes={"workflow_id": "test"}),
            make_event(source="test", name="exception", attributes={"workflow_id": "test"}),
        ]
        engine.ingest(events)
        proposals = engine.propose()

        assert isinstance(proposals, list)

    def test_autoflow_persistent(self, tmp_path):
        """Test persistent storage."""
        db_path = tmp_path / "test.db"
        engine = autoflow(db_path=db_path)

        events = [
            make_event(source="test", name="event1", attributes={}),
        ]
        engine.ingest(events)

        # Verify database file was created
        assert db_path.exists()


class TestPresets:
    """Tests for factory presets."""

    def test_autoflow_testing(self):
        """Test testing preset."""
        engine = autoflow_testing()
        assert engine is not None

    def test_autoflow_shadow(self):
        """Test shadow evaluation preset."""
        engine = autoflow_shadow()
        assert engine is not None

    def test_autoflow_auto_apply(self):
        """Test auto-apply preset."""
        engine = autoflow_auto_apply(allowed_paths=["config/"])
        assert engine is not None


class TestInMemoryStore:
    """Tests for InMemoryGraphStore."""

    def test_in_memory_store_sync(self):
        """Test sync operations on InMemoryGraphStore."""
        from autoflow.graph.store_async import InMemoryGraphStore
        from autoflow.types import GraphNode

        store = InMemoryGraphStore()

        # Test sync upsert
        from autoflow.types import ContextGraphDelta
        delta = ContextGraphDelta(
            nodes=[
                GraphNode(node_id="1", node_type="test", properties={}),
            ],
            edges=[],
        )
        store.upsert(delta)

        # Test sync query
        nodes = store.query_nodes()
        assert len(nodes) == 1
        assert nodes[0].node_id == "1"

        # Test sync close
        store.close()

    def test_in_memory_store_async_methods(self):
        """Test async methods exist and work with sync fallback."""
        from autoflow.graph.store_async import InMemoryGraphStore
        from autoflow.types import GraphNode, ContextGraphDelta
        import asyncio

        store = InMemoryGraphStore()

        # Test async methods exist
        assert hasattr(store, 'aupsert')
        assert hasattr(store, 'aquery_nodes')
        assert hasattr(store, 'aclose')

        # Test they work (they should delegate to sync methods)
        async def test_async():
            delta = ContextGraphDelta(
                nodes=[GraphNode(node_id="2", node_type="test", properties={})],
                edges=[],
            )
            await store.aupsert(delta)
            nodes = await store.aquery_nodes()
            assert len(nodes) == 1
            await store.aclose()

        asyncio.run(test_async())


class TestSyncEngineWithInMemoryStore:
    """Tests for sync engine with InMemoryGraphStore."""

    def test_sync_engine_with_in_memory_store(self):
        """Test sync engine works with InMemoryGraphStore."""
        from autoflow.orchestrator.engine import AutoImproveEngine
        from autoflow.graph.store_async import InMemoryGraphStore
        from autoflow.graph.context_graph import ContextGraphBuilder
        from autoflow.decide.decision_graph import DecisionGraph
        from autoflow.evaluate.evaluator import CompositeEvaluator

        store = InMemoryGraphStore()
        engine = AutoImproveEngine(
            store=store,
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(rules=[]),
            evaluator=CompositeEvaluator(evaluators=[]),
            applier=None,
        )

        # Test ingest
        events = [
            make_event(source="test", name="event1", attributes={}),
        ]
        engine.ingest(events)

        # Test propose
        proposals = engine.propose()
        assert isinstance(proposals, list)

        # Test close
        store.close()
