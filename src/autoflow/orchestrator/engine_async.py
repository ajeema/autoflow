"""
Async engine for AutoFlow with simplified API.
"""

from typing import List, Sequence, Optional

from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.store_async import AsyncContextGraphStore
from autoflow.types import ChangeProposal, ObservationEvent, GraphEdge
from autoflow.apply.applier import ProposalApplier


class AsyncAutoImproveEngine:
    """Async version of AutoImproveEngine."""

    def __init__(
        self,
        store: AsyncContextGraphStore,
        graph_builder: ContextGraphBuilder = None,
        decision_graph: DecisionGraph = None,
        evaluator: CompositeEvaluator = None,
        applier: ProposalApplier = None,
    ) -> None:
        self.store = store
        self.graph_builder = graph_builder or ContextGraphBuilder()
        self.decision_graph = decision_graph or DecisionGraph(rules=[])
        self.evaluator = evaluator or CompositeEvaluator(evaluators=[])
        self.applier = applier

    async def ingest(self, events: Sequence[ObservationEvent]) -> None:
        """Ingest observation events asynchronously."""
        delta = self.graph_builder.build_delta(events)
        await self.store.upsert(delta)

    async def propose(
        self,
        node_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[ChangeProposal]:
        """Generate proposals from the current graph state."""
        nodes = await self.store.query_nodes(node_type=node_type, limit=limit)
        return self.decision_graph.run(nodes)

    async def propose_with_edges(
        self,
        node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[ChangeProposal]:
        """Generate proposals with access to graph edges."""
        nodes = await self.store.query_nodes(node_type=node_type, limit=limit)
        edges = await self.store.query_edges(edge_type=edge_type, limit=limit)
        return self.decision_graph.run(nodes, edges)

    async def evaluate_and_apply(self, proposals: Sequence[ChangeProposal]) -> None:
        """Evaluate and apply proposals."""
        for proposal in proposals:
            result = self.evaluator.evaluate(proposal)
            if result.passed and self.applier:
                self.applier.apply(proposal)

    async def close(self) -> None:
        """Close the engine and cleanup resources."""
        await self.store.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
