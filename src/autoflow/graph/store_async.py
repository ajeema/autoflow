"""
Async graph store interfaces and implementations.
"""

from typing import Protocol, Sequence, Optional
from abc import abstractmethod

from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge


class AsyncContextGraphStore(Protocol):
    """Async protocol for graph storage backends."""

    @abstractmethod
    async def upsert(self, delta: ContextGraphDelta) -> None:
        """Store nodes and edges."""
        ...

    @abstractmethod
    async def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        """Query nodes by type."""
        ...

    @abstractmethod
    async def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        """Query edges by type."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the store and cleanup resources."""
        ...


class InMemoryGraphStore:
    """
    Simple in-memory store for testing and single-process use.

    Supports both sync and async operations.
    """

    def __init__(self):
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []

    # Sync methods
    def upsert(self, delta: ContextGraphDelta) -> None:
        """Sync version of upsert."""
        self._nodes.extend(delta.nodes)
        self._edges.extend(delta.edges)

    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        """Sync version of query_nodes."""
        if node_type:
            filtered = [n for n in self._nodes if n.node_type == node_type]
            return filtered[:limit]
        return self._nodes[:limit]

    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        """Sync version of query_edges."""
        if edge_type:
            filtered = [e for e in self._edges if e.edge_type == edge_type]
            return filtered[:limit]
        return self._edges[:limit]

    def close(self) -> None:
        """Sync version of close."""
        self._nodes.clear()
        self._edges.clear()

    # Async methods
    async def aupsert(self, delta: ContextGraphDelta) -> None:
        """Async version of upsert."""
        self.upsert(delta)

    async def aquery_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        """Async version of query_nodes."""
        return self.query_nodes(node_type, limit)

    async def aquery_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        """Async version of query_edges."""
        return self.query_edges(edge_type, limit)

    async def aclose(self) -> None:
        """Async version of close."""
        self.close()
