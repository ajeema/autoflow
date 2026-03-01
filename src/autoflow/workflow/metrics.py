"""
Workflow Metrics

Calculate metrics for workflow steps and entire workflows.
"""

from collections import Counter
from statistics import mean, median
from typing import List, Dict, Any, Sequence, Optional

from autoflow.types import GraphNode


def step_success_rate(
    step_executions: Sequence[GraphNode],
) -> float:
    """
    Calculate success rate for a step.

    Args:
        step_executions: List of step execution nodes

    Returns:
        Success rate as a float (0.0 to 1.0)
    """
    if not step_executions:
        return 0.0

    successful = sum(
        1 for n in step_executions
        if n.properties.get("status") == "success"
    )

    return successful / len(step_executions)


def step_failure_rate(
    step_executions: Sequence[GraphNode],
) -> float:
    """
    Calculate failure rate for a step.

    Args:
        step_executions: List of step execution nodes

    Returns:
        Failure rate as a float (0.0 to 1.0)
    """
    if not step_executions:
        return 0.0

    failed = sum(
        1 for n in step_executions
        if n.properties.get("status") == "failure"
    )

    return failed / len(step_executions)


def step_latency_stats(
    step_executions: Sequence[GraphNode],
) -> Dict[str, float]:
    """
    Calculate latency statistics for a step.

    Args:
        step_executions: List of step execution nodes

    Returns:
        Dict with avg, median, p95, p99 latency in milliseconds
    """
    latencies = [
        n.properties.get("latency_ms", 0)
        for n in step_executions
        if n.properties.get("latency_ms")
    ]

    if not latencies:
        return {
            "avg_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return {
        "avg_ms": mean(latencies),
        "median_ms": median(latencies),
        "p95_ms": sorted_latencies[int(n * 0.95)] if n > 1 else latencies[0],
        "p99_ms": sorted_latencies[int(n * 0.99)] if n > 1 else latencies[0],
        "min_ms": min(latencies),
        "max_ms": max(latencies),
    }


def step_error_types(
    step_executions: Sequence[GraphNode],
) -> Dict[str, int]:
    """
    Count error types for a step.

    Args:
        step_executions: List of step execution nodes

    Returns:
        Dict mapping error_type to count
    """
    errors = []

    for n in step_executions:
        if n.properties.get("status") == "failure":
            error_type = n.properties.get("error_type", "unknown")
            errors.append(error_type)

    return dict(Counter(errors))


def workflow_throughput(
    workflow_runs: int,
    time_window_seconds: float,
) -> float:
    """
    Calculate workflow throughput (runs per second).

    Args:
        workflow_runs: Number of workflow runs completed
        time_window_seconds: Time window in seconds

    Returns:
        Throughput as runs per second
    """
    if time_window_seconds <= 0:
        return 0.0

    return workflow_runs / time_window_seconds


def workflow_bottlenecks(
    all_nodes: Sequence[GraphNode],
    top_n: int = 5,
    latency_threshold_ms: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Find workflow bottlenecks (slowest steps).

    Args:
        all_nodes: All workflow step nodes
        top_n: Return top N bottlenecks
        latency_threshold_ms: Only include steps above this latency

    Returns:
        List of dicts with step_name, avg_latency, etc.
    """
    # Group by step name
    from autoflow.workflow.queries import WorkflowQueryHelpers
    steps_by_name = WorkflowQueryHelpers.group_by_step(all_nodes)

    bottlenecks = []

    for step_name, executions in steps_by_name.items():
        stats = step_latency_stats(executions)

        # Filter by threshold if provided
        if latency_threshold_ms is None or stats["avg_ms"] >= latency_threshold_ms:
            bottlenecks.append({
                "step_name": step_name,
                "avg_latency_ms": stats["avg_ms"],
                "p95_latency_ms": stats["p95_ms"],
                "execution_count": len(executions),
                "failure_rate": step_failure_rate(executions),
            })

    # Sort by average latency (descending)
    bottlenecks.sort(key=lambda b: b["avg_latency_ms"], reverse=True)

    return bottlenecks[:top_n]


def critical_path_analysis(
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphNode],
) -> List[Dict[str, Any]]:
    """
    Analyze the critical path (slowest path) through the workflow.

    Args:
        nodes: Workflow step nodes
        edges: Workflow edges

    Returns:
        List of dicts describing the critical path
    """
    from autoflow.workflow.queries import WorkflowQueryHelpers

    # Group by run
    runs = WorkflowQueryHelpers.group_by_workflow_run(nodes)

    critical_paths = []

    for run_id, run_nodes in runs.items():
        # Sort by step order
        run_nodes.sort(key=lambda n: n.properties.get("step_order", 0))

        # Calculate total latency for this run
        total_latency = sum(
            n.properties.get("latency_ms", 0)
            for n in run_nodes
            if n.properties.get("status") == "success"
        )

        critical_paths.append({
            "run_id": run_id,
            "total_latency_ms": total_latency,
            "step_count": len(run_nodes),
            "steps": [
                {
                    "step_name": n.properties.get("step_name"),
                    "latency_ms": n.properties.get("latency_ms", 0),
                }
                for n in run_nodes
            ],
        })

    # Sort by total latency (descending)
    critical_paths.sort(key=lambda p: p["total_latency_ms"], reverse=True)

    return critical_paths[:10]  # Return top 10 slowest runs


def step_percentile(
    step_executions: Sequence[GraphNode],
    percentile: float,
    property_name: str = "latency_ms",
) -> float:
    """
    Calculate a percentile value for a step property.

    Args:
        step_executions: List of step execution nodes
        percentile: Percentile to calculate (0.0 to 1.0)
        property_name: Property to calculate percentile for

    Returns:
        Percentile value
    """
    values = [
        n.properties.get(property_name, 0)
        for n in step_executions
        if property_name in n.properties
    ]

    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)
    index = int(n * percentile)

    return sorted_values[min(index, n - 1)]


def workflow_completion_rate(
    workflow_runs_nodes: Sequence[GraphNode],
) -> float:
    """
    Calculate what percentage of workflow runs completed successfully.

    A workflow is considered complete if all its steps succeeded.

    Args:
        workflow_runs_nodes: All nodes from workflow runs

    Returns:
        Completion rate (0.0 to 1.0)
    """
    from autoflow.workflow.queries import WorkflowQueryHelpers

    runs = WorkflowQueryHelpers.group_by_workflow_run(workflow_runs_nodes)

    complete_runs = 0

    for run_id, run_nodes in runs.items():
        # Check if all steps succeeded
        if all(
            n.properties.get("status") == "success"
            for n in run_nodes
        ):
            complete_runs += 1

    if not runs:
        return 0.0

    return complete_runs / len(runs)


def step_comparison(
    step1_executions: Sequence[GraphNode],
    step2_executions: Sequence[GraphNode],
) -> Dict[str, Any]:
    """
    Compare two steps across multiple metrics.

    Args:
        step1_executions: Executions of first step
        step2_executions: Executions of second step

    Returns:
        Dict comparing the two steps
    """
    step1_name = step1_executions[0].properties.get("step_name", "step1") if step1_executions else "step1"
    step2_name = step2_executions[0].properties.get("step_name", "step2") if step2_executions else "step2"

    return {
        "step1": {
            "name": step1_name,
            "success_rate": step_success_rate(step1_executions),
            "failure_rate": step_failure_rate(step1_executions),
            "latency": step_latency_stats(step1_executions),
            "error_types": step_error_types(step1_executions),
        },
        "step2": {
            "name": step2_name,
            "success_rate": step_success_rate(step2_executions),
            "failure_rate": step_failure_rate(step2_executions),
            "latency": step_latency_stats(step2_executions),
            "error_types": step_error_types(step2_executions),
        },
        "comparison": {
            "relative_success_rate": (
                step_success_rate(step1_executions) - step_success_rate(step2_executions)
            ),
            "relative_latency": (
                step_latency_stats(step1_executions)["avg_ms"] -
                step_latency_stats(step2_executions)["avg_ms"]
            ),
        },
    }


def workflow_run_success_rate(
    nodes: Sequence[GraphNode],
) -> float:
    """
    Calculate the percentage of workflow runs that succeeded.

    Unlike workflow_completion_rate, this considers a run successful
    if it didn't have any failed steps (skipped steps are OK).

    Args:
        nodes: All workflow step nodes

    Returns:
        Success rate (0.0 to 1.0)
    """
    from autoflow.workflow.queries import WorkflowQueryHelpers

    runs = WorkflowQueryHelpers.group_by_workflow_run(nodes)

    successful_runs = 0

    for run_id, run_nodes in runs.items():
        # Check if there are any failed steps
        has_failures = any(
            n.properties.get("status") == "failure"
            for n in run_nodes
        )

        if not has_failures:
            successful_runs += 1

    if not runs:
        return 0.0

    return successful_runs / len(runs)
