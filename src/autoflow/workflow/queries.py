"""
Workflow Query Helpers

Provides convenient methods for querying and analyzing workflow executions
from the context graph.
"""

from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Sequence

from autoflow.types import GraphNode, GraphEdge, StepStatus


class WorkflowQueryHelpers:
    """
    Helper methods for querying workflow data from the graph.

    Provides high-level query methods that work on GraphNode/GraphEdge
    structures returned from ContextGraphStore.
    """

    @staticmethod
    def filter_by_workflow(
        nodes: Sequence[GraphNode],
        workflow_id: str,
    ) -> List[GraphNode]:
        """Filter nodes to only those from a specific workflow."""
        return [
            n for n in nodes
            if n.properties.get("workflow_id") == workflow_id
        ]

    @staticmethod
    def filter_by_step(
        nodes: Sequence[GraphNode],
        step_name: str,
    ) -> List[GraphNode]:
        """Filter nodes to only those from a specific step."""
        return [
            n for n in nodes
            if n.properties.get("step_name") == step_name
        ]

    @staticmethod
    def filter_by_status(
        nodes: Sequence[GraphNode],
        status: str,
    ) -> List[GraphNode]:
        """Filter nodes by execution status."""
        return [
            n for n in nodes
            if n.properties.get("status") == status
        ]

    @staticmethod
    def group_by_step(
        nodes: Sequence[GraphNode],
    ) -> Dict[str, List[GraphNode]]:
        """Group nodes by step name."""
        grouped = defaultdict(list)
        for node in nodes:
            step_name = node.properties.get("step_name", "unknown")
            grouped[step_name].append(node)
        return dict(grouped)

    @staticmethod
    def group_by_workflow_run(
        nodes: Sequence[GraphNode],
    ) -> Dict[str, List[GraphNode]]:
        """Group nodes by workflow run ID."""
        grouped = defaultdict(list)
        for node in nodes:
            run_id = node.properties.get("workflow_run_id", "unknown")
            grouped[run_id].append(node)
        return dict(grouped)

    @staticmethod
    def get_workflow_runs(
        nodes: Sequence[GraphNode],
        workflow_id: str,
    ) -> List[str]:
        """Get all run IDs for a specific workflow."""
        run_ids = set()
        for node in nodes:
            if (
                node.properties.get("workflow_id") == workflow_id and
                node.properties.get("workflow_run_id")
            ):
                run_ids.add(node.properties["workflow_run_id"])
        return sorted(list(run_ids))

    @staticmethod
    def get_steps_for_run(
        nodes: Sequence[GraphNode],
        run_id: str,
    ) -> List[GraphNode]:
        """Get all steps for a specific workflow run, in order."""
        steps = [
            n for n in nodes
            if n.properties.get("workflow_run_id") == run_id
        ]
        steps.sort(key=lambda n: n.properties.get("step_order", 0))
        return steps

    @staticmethod
    def count_by_status(
        nodes: Sequence[GraphNode],
    ) -> Dict[str, int]:
        """Count nodes by status."""
        counter = Counter(
            n.properties.get("status", "unknown")
            for n in nodes
        )
        return dict(counter)

    @staticmethod
    def find_error_propagation(
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
    ) -> List[Dict[str, Any]]:
        """
        Find error propagation patterns.

        Returns list of dicts describing which failures caused
        downstream failures.
        """
        caused_by_edges = [
            e for e in edges
            if e.edge_type == "caused_by"
        ]

        propagations = []
        for edge in caused_by_edges:
            from_node = next(
                (n for n in nodes if n.node_id == edge.from_node_id),
                None
            )
            to_node = next(
                (n for n in nodes if n.node_id == edge.to_node_id),
                None
            )

            if from_node and to_node:
                propagations.append({
                    "from_step": from_node.properties.get("step_name"),
                    "from_run": from_node.properties.get("workflow_run_id"),
                    "from_error": from_node.properties.get("error_type"),
                    "to_step": to_node.properties.get("step_name"),
                    "to_status": to_node.properties.get("status"),
                    "reason": edge.properties.get("reason"),
                })

        return propagations

    @staticmethod
    def find_root_cause_failures(
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
    ) -> List[GraphNode]:
        """
        Find failures that are not caused by other failures.

        These are the root causes of workflow failures.
        """
        # Get all failed nodes
        failed_nodes = [
            n for n in nodes
            if n.properties.get("status") == "failure"
        ]

        # Get nodes that have incoming "caused_by" edges
        caused_nodes = set()
        for edge in edges:
            if edge.edge_type == "caused_by":
                caused_nodes.add(edge.to_node_id)

        # Root causes are failures that don't have incoming caused_by edges
        root_causes = [
            n for n in failed_nodes
            if n.node_id not in caused_nodes
        ]

        return root_causes

    @staticmethod
    def get_step_dependencies(
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
    ) -> Dict[str, List[str]]:
        """
        Get dependency graph: which steps depend on which.

        Returns: {step_name: [list of steps that depend on it]}
        """
        dependencies = defaultdict(list)

        for edge in edges:
            if edge.edge_type == "depends_on":
                from_node = next(
                    (n for n in nodes if n.node_id == edge.from_node_id),
                    None
                )
                to_node = next(
                    (n for n in nodes if n.node_id == edge.to_node_id),
                    None
                )

                if from_node and to_node:
                    from_step = from_node.properties.get("step_name")
                    to_step = to_node.properties.get("step_name")
                    if from_step and to_step:
                        dependencies[from_step].append(to_step)

        return dict(dependencies)

    @staticmethod
    def get_parallel_branches(
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
    ) -> List[List[str]]:
        """
        Find parallel execution branches.

        Returns list of branch lists, where each branch is a list of step names.
        """
        # Group by parent step
        children_by_parent = defaultdict(list)

        for edge in edges:
            if edge.edge_type == "depends_on":
                to_node = next(
                    (n for n in nodes if n.node_id == edge.to_node_id),
                    None
                )
                if to_node:
                    parent_step = to_node.properties.get("parent_step_id")
                    step_name = to_node.properties.get("step_name")
                    if parent_step and step_name:
                        children_by_parent[parent_step].append(step_name)

        # Find parents with multiple children (parallel branches)
        branches = [
            children for children in children_by_parent.values()
            if len(children) > 1
        ]

        return branches

    @staticmethod
    def trace_execution_path(
        nodes: Sequence[GraphNode],
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get the execution path for a specific workflow run.

        Returns list of dicts with step info in execution order.
        """
        steps = WorkflowQueryHelpers.get_steps_for_run(nodes, run_id)

        path = []
        for step in steps:
            path.append({
                "step_name": step.properties.get("step_name"),
                "step_id": step.properties.get("step_id"),
                "step_order": step.properties.get("step_order"),
                "status": step.properties.get("status"),
                "latency_ms": step.properties.get("latency_ms"),
                "error_type": step.properties.get("error_type"),
            })

        return path

    @staticmethod
    def get_workflow_statistics(
        nodes: Sequence[GraphNode],
        workflow_id: str,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for a workflow.

        Returns dict with counts, rates, etc.
        """
        workflow_nodes = WorkflowQueryHelpers.filter_by_workflow(
            nodes, workflow_id
        )

        if not workflow_nodes:
            return {}

        total_runs = len(set(
            n.properties.get("workflow_run_id")
            for n in workflow_nodes
        ))

        status_counts = WorkflowQueryHelpers.count_by_status(workflow_nodes)

        # Calculate success rate
        total_steps = len(workflow_nodes)
        successful = status_counts.get("success", 0)
        failed = status_counts.get("failure", 0)
        skipped = status_counts.get("skipped", 0)

        return {
            "workflow_id": workflow_id,
            "total_runs": total_runs,
            "total_step_executions": total_steps,
            "successful_steps": successful,
            "failed_steps": failed,
            "skipped_steps": skipped,
            "success_rate": successful / total_steps if total_steps > 0 else 0,
            "failure_rate": failed / total_steps if total_steps > 0 else 0,
            "status_breakdown": status_counts,
        }
