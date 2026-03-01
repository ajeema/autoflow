"""
Workflow-Aware Context Graph Builder

Builds enhanced context graphs that capture:
- Sequential flow (step → next_step)
- Dependencies (parent → child)
- Error propagation (error → caused_failure)
- Parallel branches
"""

from collections import defaultdict
from typing import Sequence, List

from autoflow.types import (
    ObservationEvent,
    ContextGraphDelta,
    GraphNode,
    GraphEdge,
)


class WorkflowAwareGraphBuilder:
    """
    Enhanced graph builder that captures workflow relationships.

    Creates nodes for each step execution and edges showing:
    - next_step: Sequential execution flow
    - depends_on: Parent-child dependencies
    - caused_by: Error propagation (failure → downstream failures)
    - parallel_branch: Concurrent execution paths
    """

    def __init__(self, include_non_workflow: bool = True):
        """
        Args:
            include_non_workflow: Whether to include non-workflow events in the graph
        """
        self.include_non_workflow = include_non_workflow

    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        """Build a context graph with workflow relationships."""
        nodes = []
        edges = []

        # Separate workflow and non-workflow events
        workflow_events = []
        other_events = []

        for ev in events:
            if self._is_workflow_event(ev):
                workflow_events.append(ev)
            elif self.include_non_workflow:
                other_events.append(ev)

        # Build workflow graph
        workflow_nodes, workflow_edges = self._build_workflow_graph(workflow_events)
        nodes.extend(workflow_nodes)
        edges.extend(workflow_edges)

        # Add non-workflow events as simple nodes
        for ev in other_events:
            nodes.append(GraphNode(
                node_id=f"event:{ev.event_id}",
                node_type="event",
                properties={
                    "name": ev.name,
                    "source": ev.source,
                    **ev.attributes,
                },
            ))

        return ContextGraphDelta(nodes=nodes, edges=edges)

    def _is_workflow_event(self, event: ObservationEvent) -> bool:
        """Check if event is a workflow step event."""
        # Check for workflow event attributes
        attrs = event.attributes or {}
        return (
            event.name == "step_execution" and
            "workflow_id" in attrs and
            "step_name" in attrs and
            "step_id" in attrs
        )

    def _build_workflow_graph(
        self,
        events: List[ObservationEvent]
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Build workflow-specific graph structure."""
        nodes = []
        edges = []

        if not events:
            return nodes, edges

        # Group events by workflow run
        runs = defaultdict(list)
        for ev in events:
            run_id = self._get_run_id(ev)
            runs[run_id].append(ev)

        # Process each workflow run
        for run_id, run_events in runs.items():
            run_nodes = []
            run_edges = []

            # Create nodes for each step
            for ev in run_events:
                node = self._create_step_node(ev)
                nodes.append(node)
                run_nodes.append(node)

            # Sort by step order
            run_nodes.sort(key=lambda n: n.properties.get("step_order", 0))

            # Build edges
            run_edges = self._build_run_edges(run_id, run_nodes)
            edges.extend(run_edges)

        return nodes, edges

    def _get_run_id(self, event: ObservationEvent) -> str:
        """Extract workflow run ID from event."""
        # Check attributes
        return event.attributes.get("workflow_run_id", "unknown")

    def _create_step_node(self, event: ObservationEvent) -> GraphNode:
        """Create a graph node from a workflow step event."""
        # Extract from ObservationEvent attributes
        props = dict(event.attributes)
        # Ensure status field is set
        if "status" not in props and "step_status" in props:
            props["status"] = props["step_status"]

        return GraphNode(
            node_id=props.get("step_id", f"step:{event.event_id}"),
            node_type="workflow_step",
            properties=props,
        )

    def _build_run_edges(
        self,
        run_id: str,
        nodes: List[GraphNode],
    ) -> List[GraphEdge]:
        """Build edges for a single workflow run."""
        edges = []

        # Build sequential edges (step → next_step)
        for i in range(len(nodes) - 1):
            current = nodes[i]
            next_node = nodes[i + 1]

            # Check if this is actually a sequential relationship
            # (not a parallel branch)
            if self._is_sequential(current, next_node):
                edges.append(GraphEdge(
                    edge_type="next_step",
                    from_node_id=current.node_id,
                    to_node_id=next_node.node_id,
                    properties={
                        "workflow_run_id": run_id,
                        "order": current.properties.get("step_order"),
                    },
                ))

        # Build dependency edges (parent → child)
        for node in nodes:
            parent_id = node.properties.get("parent_step_id")
            if parent_id:
                edges.append(GraphEdge(
                    edge_type="depends_on",
                    from_node_id=parent_id,
                    to_node_id=node.node_id,
                    properties={
                        "workflow_run_id": run_id,
                    },
                ))

        # Build error propagation edges
        failed_nodes = [n for n in nodes if n.properties.get("status") == "failure"]

        for failed_node in failed_nodes:
            # Find downstream nodes that may have been affected
            downstream = self._find_downstream_nodes(failed_node, nodes)

            for downstream_node in downstream:
                # Only mark as caused_by if downstream also failed or was skipped
                downstream_status = downstream_node.properties.get("status")
                if downstream_status in ["failure", "skipped"]:
                    # Avoid duplicate edges
                    edge_exists = any(
                        e.edge_type == "caused_by" and
                        e.from_node_id == failed_node.node_id and
                        e.to_node_id == downstream_node.node_id
                        for e in edges
                    )
                    if not edge_exists:
                        edges.append(GraphEdge(
                            edge_type="caused_by",
                            from_node_id=failed_node.node_id,
                            to_node_id=downstream_node.node_id,
                            properties={
                                "workflow_run_id": run_id,
                                "reason": "error_propagation",
                                "error_type": failed_node.properties.get("error_type"),
                            },
                        ))

        return edges

    def _is_sequential(self, current: GraphNode, next_node: GraphNode) -> bool:
        """Check if two nodes have a sequential relationship."""
        current_parent = current.properties.get("parent_step_id")
        next_parent = next_node.properties.get("parent_step_id")

        # Sequential if:
        # - Next node has current as parent, OR
        # - Both have same parent (siblings in sequence)
        return (
            next_parent == current.properties.get("step_id") or
            current_parent == next_parent and current_parent is not None
        )

    def _find_downstream_nodes(
        self,
        node: GraphNode,
        all_nodes: List[GraphNode],
    ) -> List[GraphNode]:
        """Find all nodes that come after the given node."""
        node_order = node.properties.get("step_order", -1)
        return [
            n for n in all_nodes
            if n.properties.get("step_order", -1) > node_order
        ]
