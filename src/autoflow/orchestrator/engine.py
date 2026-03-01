from typing import List, Sequence, Optional

from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.store import ContextGraphStore
from autoflow.types import ChangeProposal, ObservationEvent, GraphEdge
from autoflow.apply.applier import ProposalApplier


class AutoImproveEngine:
    def __init__(
        self,
        store: ContextGraphStore,
        graph_builder: ContextGraphBuilder,
        decision_graph: DecisionGraph,
        evaluator: CompositeEvaluator,
        applier: ProposalApplier,
    ) -> None:
        self.store = store
        self.graph_builder = graph_builder
        self.decision_graph = decision_graph
        self.evaluator = evaluator
        self.applier = applier

    def ingest(self, events: Sequence[ObservationEvent]) -> None:
        delta = self.graph_builder.build_delta(events)
        self.store.upsert(delta)

    def propose(
        self,
        node_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[ChangeProposal]:
        """
        Generate proposals from the current graph state.

        Args:
            node_type: Optional node type filter (e.g., "workflow_step")
            limit: Max nodes to query

        Returns:
            List of proposals
        """
        nodes = self.store.query_nodes(node_type=node_type, limit=limit)
        return self.decision_graph.run(nodes)

    def propose_with_edges(
        self,
        node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[ChangeProposal]:
        """
        Generate proposals with access to graph edges.

        Use this when rules need to analyze relationships between nodes.

        Args:
            node_type: Optional node type filter
            edge_type: Optional edge type filter
            limit: Max nodes/edges to query

        Returns:
            List of proposals
        """
        nodes = self.store.query_nodes(node_type=node_type, limit=limit)
        edges = self.store.query_edges(edge_type=edge_type, limit=limit)
        return self.decision_graph.run(nodes, edges)

    def evaluate_and_apply(self, proposals: Sequence[ChangeProposal]) -> None:
        for proposal in proposals:
            result = self.evaluator.evaluate(proposal)
            if result.passed:
                self.applier.apply(proposal)