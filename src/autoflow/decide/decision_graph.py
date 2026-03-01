import inspect
from typing import Sequence, Optional

from autoflow.types import ChangeProposal, GraphNode, GraphEdge


class DecisionGraph:
    """
    Orchestrates multiple rules to generate proposals.

    Rules can accept either:
    - Just nodes: rule.propose(nodes)
    - Nodes and edges: rule.propose(nodes, edges)
    """

    def __init__(self, rules: Sequence[object]) -> None:
        self.rules = rules

    def run(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> list[ChangeProposal]:
        """
        Run all rules and collect proposals.

        Args:
            nodes: Graph nodes to analyze
            edges: Optional graph edges for relationship analysis

        Returns:
            List of proposals from all rules
        """
        proposals: list[ChangeProposal] = []

        for rule in self.rules:
            # Check if rule accepts edges parameter
            sig = inspect.signature(rule.propose)
            params = list(sig.parameters.keys())

            if len(params) >= 2 and "edges" in params:
                # Rule accepts edges
                proposals.extend(rule.propose(list(nodes), edges or []))
            else:
                # Rule only accepts nodes
                proposals.extend(rule.propose(list(nodes)))

        return proposals