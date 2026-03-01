from typing import Protocol, Sequence, Optional

from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge


class ContextGraphStore(Protocol):
    def upsert(self, delta: ContextGraphDelta) -> None: ...
    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]: ...
    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]: ...