#!/usr/bin/env python3
"""
Multi-Step Workflow Analysis Demo

This demo shows how to analyze multi-step workflows with AutoFlow,
identifying which steps are causing issues and proposing targeted fixes.

Workflow Example: Data Processing Pipeline
  Step 1: Extract (fetch data)
  Step 2: Transform (clean/normalize)
  Step 3: Validate (check quality)
  Step 4: Load (store result)

We track:
  - Each step's outcome
  - Causal relationships (step_id → parent_step_id)
  - Overall workflow success/failure
  - Error propagation through the pipeline
"""

import json
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent / "src"))

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import (
    GraphNode, ProposalKind, RiskLevel, ChangeProposal,
    ObservationEvent, ContextGraphDelta, GraphEdge
)


# =============================================================================
# Workflow Types
# =============================================================================

class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    RETRY = "retry"


@dataclass
class StepEvent:
    """A step in a workflow execution."""
    workflow_run_id: str
    step_name: str
    step_id: str
    parent_step_id: str | None = None
    status: StepStatus = StepStatus.SUCCESS
    latency_ms: float = 0.0
    error_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observation_event(self) -> ObservationEvent:
        """Convert to AutoFlow ObservationEvent."""
        return make_event(
            source="workflow_engine",
            name="step_execution",
            attributes={
                "workflow_run_id": self.workflow_run_id,
                "step_name": self.step_name,
                "step_id": self.step_id,
                "parent_step_id": self.parent_step_id,
                "status": self.status.value,
                "latency_ms": self.latency_ms,
                "error_type": self.error_type,
                **self.metadata,
            },
        )


@dataclass
class WorkflowRun:
    """A complete workflow execution."""
    workflow_id: str
    run_id: str
    status: StepStatus
    total_latency_ms: float
    steps: list[StepEvent] = field(default_factory=list)
    outcome_metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Enhanced Context Graph (Builds Edges Between Steps)
# =============================================================================

class WorkflowAwareGraphBuilder:
    """
    Enhanced graph builder that captures workflow relationships.

    Creates:
    - Nodes for each step execution
    - Edges showing the flow (step → next step)
    - Edges showing causality (error → failed steps)
    """

    def build_delta(self, events: list[ObservationEvent]) -> ContextGraphDelta:
        nodes = []
        edges = []

        # Group events by workflow run
        workflow_runs: dict[str, list[GraphNode]] = {}

        for ev in events:
            # Only process step_execution events
            if ev.name != "step_execution":
                continue

            node = GraphNode(
                node_id=f"step:{ev.attributes.get('step_id')}",
                node_type="workflow_step",
                properties={
                    "event_id": ev.event_id,
                    "workflow_run_id": ev.attributes.get("workflow_run_id"),
                    "step_name": ev.attributes.get("step_name"),
                    "status": ev.attributes.get("status"),
                    "latency_ms": ev.attributes.get("latency_ms"),
                    "error_type": ev.attributes.get("error_type"),
                    **{k: v for k, v in ev.attributes.items()
                       if k not in ["workflow_run_id", "step_name", "status", "latency_ms", "error_type"]},
                },
            )
            nodes.append(node)

            # Group by workflow run
            run_id = ev.attributes.get("workflow_run_id", "unknown")
            if run_id not in workflow_runs:
                workflow_runs[run_id] = []
            workflow_runs[run_id].append(node)

        # Build edges showing workflow flow
        for run_id, run_nodes in workflow_runs.items():
            # Sort by step_id to get execution order
            sorted_nodes = sorted(run_nodes, key=lambda n: n.properties.get("step_id", ""))

            # Create sequential edges (step → next step)
            for i in range(len(sorted_nodes) - 1):
                current = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]

                edges.append(GraphEdge(
                    edge_type="next_step",
                    from_node_id=current.node_id,
                    to_node_id=next_node.node_id,
                    properties={"workflow_run_id": run_id},
                ))

            # Create error propagation edges
            for node in sorted_nodes:
                if node.properties.get("status") == "failure":
                    # Find steps that came after this failed step
                    node_idx = sorted_nodes.index(node)
                    for later_node in sorted_nodes[node_idx + 1:]:
                        if later_node.properties.get("status") in ["skipped", "failure"]:
                            # This step likely failed due to the earlier error
                            edges.append(GraphEdge(
                                edge_type="caused_by",
                                from_node_id=node.node_id,
                                to_node_id=later_node.node_id,
                                properties={
                                    "reason": "error_propagation",
                                    "workflow_run_id": run_id,
                                },
                            ))

        return ContextGraphDelta(nodes=nodes, edges=edges)


# =============================================================================
# Multi-Step Analysis Rules
# =============================================================================

class FailingStepRule:
    """
    Identifies which specific steps are failing most frequently.

    Proposes targeted fixes for problematic steps.
    """

    def __init__(self, workflow_id: str, failure_threshold: float = 0.2):
        """
        Args:
            workflow_id: The workflow to analyze
            failure_threshold: Alert if step failure rate exceeds this (e.g., 0.2 = 20%)
        """
        self.workflow_id = workflow_id
        self.failure_threshold = failure_threshold

    def propose(self, nodes: list[GraphNode]) -> list[ChangeProposal]:
        """Analyze step executions and propose fixes."""
        # Filter for this workflow's steps
        workflow_steps = [
            n for n in nodes
            if n.node_type == "workflow_step"
            and n.properties.get("workflow_run_id", "").startswith(self.workflow_id)
        ]

        if len(workflow_steps) < 5:
            return []

        # Group by step name
        from collections import defaultdict
        steps_by_name: defaultdict[str, list[GraphNode]] = defaultdict(list)
        for node in workflow_steps:
            step_name = node.properties.get("step_name", "unknown")
            steps_by_name[step_name].append(node)

        # Analyze each step
        proposals = []

        for step_name, executions in steps_by_name.items():
            failures = [n for n in executions if n.properties.get("status") == "failure"]
            failure_rate = len(failures) / len(executions)

            if failure_rate >= self.failure_threshold:
                # Analyze error types
                error_types = {}
                for f in failures:
                    error = f.properties.get("error_type", "unknown")
                    error_types[error] = error_types.get(error, 0) + 1

                most_common_error = max(error_types, key=error_types.get)

                # Calculate avg latency for failed vs successful runs
                failed_latencies = [
                    f.properties.get("latency_ms", 0)
                    for f in failures
                    if f.properties.get("latency_ms")
                ]
                successful_executions = [n for n in executions if n.properties.get("status") == "success"]
                success_latencies = [
                    s.properties.get("latency_ms", 0)
                    for s in successful_executions
                    if s.properties.get("latency_ms")
                ]

                avg_failed_latency = sum(failed_latencies) / len(failed_latencies) if failed_latencies else 0
                avg_success_latency = sum(success_latencies) / len(success_latencies) if success_latencies else 0

                proposals.append(self._create_proposal(
                    step_name=step_name,
                    failure_rate=failure_rate,
                    most_common_error=most_common_error,
                    avg_failed_latency=avg_failed_latency,
                    avg_success_latency=avg_success_latency,
                    error_counts=error_types,
                ))

        return proposals

    def _create_proposal(self, step_name: str, failure_rate: float,
                        most_common_error: str, avg_failed_latency: float,
                        avg_success_latency: float, error_counts: dict) -> ChangeProposal:
        """Create a targeted proposal for a failing step."""

        # Determine proposal type based on error pattern
        if most_common_error == "timeout":
            title = f"Increase timeout for '{step_name}' step"
            description = (
                f"Step '{step_name}' is failing due to timeouts "
                f"({failure_rate:.1%} failure rate). "
                f"Failed runs avg {avg_failed_latency:.0f}ms vs "
                f"successful runs {avg_success_latency:.0f}ms."
            )
            payload = {
                "step": step_name,
                "setting": "timeout_ms",
                "value": int(avg_failed_latency * 1.5),  # 50% buffer
                "old_value": int(avg_success_latency * 1.2),
            }

        elif most_common_error == "rate_limit":
            title = f"Add rate limiting for '{step_name}' step"
            description = (
                f"Step '{step_name}' is hitting rate limits "
                f"({failure_rate:.1%} failure rate). "
                f"Proposing backoff and retry configuration."
            )
            payload = {
                "step": step_name,
                "add_retry_policy": {
                    "max_retries": 3,
                    "backoff_ms": [1000, 2000, 5000],
                },
            }

        elif most_common_error == "validation_error":
            title = f"Improve data validation in '{step_name}' step"
            description = (
                f"Step '{step_name}' has validation errors "
                f"({failure_rate:.1%} failure rate). "
                f"Proposing schema validation and error handling improvements."
            )
            payload = {
                "step": step_name,
                "add_validation": True,
                "error_handling": "strict",
            }

        else:
            title = f"Improve error handling in '{step_name}' step"
            description = (
                f"Step '{step_name}' is failing "
                f"({failure_rate:.1%} failure rate, "
                f"error: {most_common_error}). "
                f"Error breakdown: {error_counts}"
            )
            payload = {
                "step": step_name,
                "add_error_handling": True,
                "log_errors": True,
            }

        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=title,
            description=description,
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload=payload,
        )


class SlowStepRule:
    """Identifies slow steps that are bottlenecks."""

    def __init__(self, workflow_id: str, slowness_threshold_ms: float = 5000):
        self.workflow_id = workflow_id
        self.slowness_threshold_ms = slowness_threshold_ms

    def propose(self, nodes: list[GraphNode]) -> list[ChangeProposal]:
        """Find slow steps and propose optimizations."""
        workflow_steps = [
            n for n in nodes
            if n.node_type == "workflow_step"
            and n.properties.get("workflow_run_id", "").startswith(self.workflow_id)
        ]

        if len(workflow_steps) < 5:
            return []

        # Group by step name
        from collections import defaultdict
        steps_by_name: defaultdict[str, list[GraphNode]] = defaultdict(list)
        for node in workflow_steps:
            step_name = node.properties.get("step_name", "unknown")
            steps_by_name[step_name].append(node)

        proposals = []

        for step_name, executions in steps_by_name.items():
            latencies = [
                e.properties.get("latency_ms", 0)
                for e in executions
                if e.properties.get("latency_ms")
            ]

            if not latencies:
                continue

            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]

            if p95_latency > self.slowness_threshold_ms:
                proposals.append(ChangeProposal(
                    proposal_id=str(uuid4()),
                    kind=ProposalKind.CONFIG_EDIT,
                    title=f"Optimize slow step: '{step_name}'",
                    description=(
                        f"Step '{step_name}' has P95 latency of {p95_latency:.0f}ms "
                        f"(threshold: {self.slowness_threshold_ms:.0f}ms, "
                        f"avg: {avg_latency:.0f}ms). "
                        f"Proposing optimization (caching, batching, or parallelization)."
                    ),
                    risk=RiskLevel.LOW,
                    target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
                    payload={
                        "step": step_name,
                        "optimization": "enable_caching",
                        "config": {
                            "cache_ttl_seconds": 300,
                            "enable_batch_processing": True,
                        },
                    },
                ))

        return proposals


class ErrorPropagationRule:
    """Analyzes how errors propagate through the workflow."""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id

    def propose(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> list[ChangeProposal]:
        """Find error propagation patterns and propose resilience improvements."""
        # Find all "caused_by" edges
        causality_edges = [
            e for e in edges
            if e.edge_type == "caused_by"
        ]

        if not causality_edges:
            return []

        # Count which steps cause the most downstream failures
        from collections import Counter
        root_causes = Counter()

        for edge in causality_edges:
            from_node = next((n for n in nodes if n.node_id == edge.from_node_id), None)
            if from_node:
                step_name = from_node.properties.get("step_name", "unknown")
                root_causes[step_name] += 1

        if not root_causes:
            return []

        # Find the most problematic root cause
        worst_step, downstream_failures = root_causes.most_common(1)[0]

        if downstream_failures >= 3:  # If causing 3+ downstream failures
            return [ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title=f"Add resilience to '{worst_step}' step",
                description=(
                    f"Step '{worst_step}' failures are causing "
                    f"{downstream_failures} downstream step failures. "
                    f"Proposing retry logic and graceful degradation."
                ),
                risk=RiskLevel.MEDIUM,
                target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
                payload={
                    "step": worst_step,
                    "add_retry_policy": {
                        "max_retries": 3,
                        "backoff_ms": [500, 1000, 2000],
                    },
                    "add_circuit_breaker": {
                        "failure_threshold": 5,
                        "reset_timeout_ms": 30000,
                    },
                },
            )]

        return []


# =============================================================================
# Demo Workflow Execution
# =============================================================================

def simulate_data_pipeline() -> list[ObservationEvent]:
    """
    Simulate a data pipeline workflow with various failure modes.

    Pipeline steps:
    1. extract: Fetch data from API (sometimes times out)
    2. transform: Clean and normalize (sometimes has validation errors)
    3. validate: Check data quality (fails if transform failed)
    4. load: Store in database (sometimes hits rate limits)
    """
    import random

    events = []
    run_id = 0

    for _ in range(20):  # 20 workflow runs
        run_id += 1
        workflow_run_id = f"data_pipeline_{run_id}"

        # Simulate randomness
        extract_timeout = random.random() < 0.25  # 25% timeout rate
        transform_validation_error = random.random() < 0.15  # 15% validation error
        load_rate_limit = random.random() < 0.20  # 20% rate limit

        steps = []

        # Step 1: Extract
        if extract_timeout:
            steps.append(StepEvent(
                workflow_run_id=workflow_run_id,
                step_name="extract",
                step_id=f"{workflow_run_id}_step_1",
                status=StepStatus.FAILURE,
                latency_ms=8500,
                error_type="timeout",
            ))
            # Remaining steps skipped or failed due to this
            steps.append(StepEvent(
                workflow_run_id=workflow_run_id,
                step_name="transform",
                step_id=f"{workflow_run_id}_step_2",
                parent_step_id=f"{workflow_run_id}_step_1",
                status=StepStatus.SKIPPED,
                latency_ms=0,
            ))
            steps.append(StepEvent(
                workflow_run_id=workflow_run_id,
                step_name="validate",
                step_id=f"{workflow_run_id}_step_3",
                parent_step_id=f"{workflow_run_id}_step_2",
                status=StepStatus.SKIPPED,
                latency_ms=0,
            ))
            steps.append(StepEvent(
                workflow_run_id=workflow_run_id,
                step_name="load",
                step_id=f"{workflow_run_id}_step_4",
                parent_step_id=f"{workflow_run_id}_step_3",
                status=StepStatus.SKIPPED,
                latency_ms=0,
            ))
        else:
            # Extract succeeded
            extract_latency = 500 + random.randint(-100, 300)
            steps.append(StepEvent(
                workflow_run_id=workflow_run_id,
                step_name="extract",
                step_id=f"{workflow_run_id}_step_1",
                status=StepStatus.SUCCESS,
                latency_ms=extract_latency,
            ))

            # Step 2: Transform
            if transform_validation_error:
                steps.append(StepEvent(
                    workflow_run_id=workflow_run_id,
                    step_name="transform",
                    step_id=f"{workflow_run_id}_step_2",
                    parent_step_id=f"{workflow_run_id}_step_1",
                    status=StepStatus.FAILURE,
                    latency_ms=1200,
                    error_type="validation_error",
                ))
                # Validate and Load skipped
                steps.append(StepEvent(
                    workflow_run_id=workflow_run_id,
                    step_name="validate",
                    step_id=f"{workflow_run_id}_step_3",
                    parent_step_id=f"{workflow_run_id}_step_2",
                    status=StepStatus.SKIPPED,
                    latency_ms=0,
                ))
                steps.append(StepEvent(
                    workflow_run_id=workflow_run_id,
                    step_name="load",
                    step_id=f"{workflow_run_id}_step_4",
                    parent_step_id=f"{workflow_run_id}_step_3",
                    status=StepStatus.SKIPPED,
                    latency_ms=0,
                ))
            else:
                # Transform succeeded
                steps.append(StepEvent(
                    workflow_run_id=workflow_run_id,
                    step_name="transform",
                    step_id=f"{workflow_run_id}_step_2",
                    parent_step_id=f"{workflow_run_id}_step_1",
                    status=StepStatus.SUCCESS,
                    latency_ms=1000 + random.randint(-200, 400),
                ))

                # Step 3: Validate
                steps.append(StepEvent(
                    workflow_run_id=workflow_run_id,
                    step_name="validate",
                    step_id=f"{workflow_run_id}_step_3",
                    parent_step_id=f"{workflow_run_id}_step_2",
                    status=StepStatus.SUCCESS,
                    latency_ms=500 + random.randint(-100, 200),
                ))

                # Step 4: Load
                if load_rate_limit:
                    steps.append(StepEvent(
                        workflow_run_id=workflow_run_id,
                        step_name="load",
                        step_id=f"{workflow_run_id}_step_4",
                        parent_step_id=f"{workflow_run_id}_step_3",
                        status=StepStatus.FAILURE,
                        latency_ms=2300,
                        error_type="rate_limit",
                    ))
                else:
                    steps.append(StepEvent(
                        workflow_run_id=workflow_run_id,
                        step_name="load",
                        step_id=f"{workflow_run_id}_step_4",
                        parent_step_id=f"{workflow_run_id}_step_3",
                        status=StepStatus.SUCCESS,
                        latency_ms=800 + random.randint(-100, 300),
                    ))

        # Convert to observation events
        for step in steps:
            events.append(step.to_observation_event())

    return events


# =============================================================================
# Enhanced Decision Graph (Passes edges to rules)
# =============================================================================

class EnhancedDecisionGraph:
    """Decision graph that passes both nodes and edges to rules."""

    def __init__(self, rules: list):
        self.rules = rules

    def run_with_graph(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> list[ChangeProposal]:
        """Run rules with access to both nodes and edges."""
        proposals = []

        for rule in self.rules:
            # Check if rule wants edges
            import inspect
            sig = inspect.signature(rule.propose)
            if len(sig.parameters) > 1:
                # Rule accepts both nodes and edges
                proposals.extend(rule.propose(nodes, edges))
            else:
                # Rule only wants nodes
                proposals.extend(rule.propose(nodes))

        return proposals


# =============================================================================
# Main Demo
# =============================================================================

def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    print(f"\n--- {title} ---\n")


def run_multistep_demo() -> None:
    """Demonstrate multi-step workflow analysis."""

    print_section("Multi-Step Workflow Analysis Demo")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "workflow_graph.db"

        print_subsection("Simulating Data Pipeline Workflow")
        print("Running 20 iterations of a 4-step data pipeline:")
        print("  1. Extract (fetch from API)")
        print("  2. Transform (clean/normalize)")
        print("  3. Validate (check quality)")
        print("  4. Load (store in database)")
        print("\nSimulated failure modes:")
        print("  - Extract: 25% timeout rate")
        print("  - Transform: 15% validation error rate")
        print("  - Load: 20% rate limit")

        # Generate workflow events
        workflow_events = simulate_data_pipeline()

        print(f"\nGenerated {len(workflow_events)} step execution events")

        # Calculate some stats
        successful_steps = sum(1 for e in workflow_events
                              if e.attributes.get("status") == "success")
        failed_steps = sum(1 for e in workflow_events
                          if e.attributes.get("status") == "failure")
        skipped_steps = sum(1 for e in workflow_events
                           if e.attributes.get("status") == "skipped")

        print(f"\nStep outcomes:")
        print(f"  Success: {successful_steps}")
        print(f"  Failure: {failed_steps}")
        print(f"  Skipped: {skipped_steps}")

        # Build enhanced context graph
        print_subsection("Building Context Graph with Relationships")

        graph_builder = WorkflowAwareGraphBuilder()
        delta = graph_builder.build_delta(workflow_events)

        print(f"Created {len(delta.nodes)} nodes")
        print(f"Created {len(delta.edges)} edges")
        print(f"  Edge types:")
        from collections import Counter
        edge_types = Counter(e.edge_type for e in delta.edges)
        for etype, count in edge_types.items():
            print(f"    {etype}: {count}")

        # Store in database
        print_subsection("Storing in Graph Database")

        store = SQLiteGraphStore(db_path=str(db_path))
        store.upsert(delta)

        # Query for specific steps
        print_subsection("Querying Specific Steps")

        for step_name in ["extract", "transform", "load"]:
            step_nodes = store.query_nodes("workflow_step", limit=100)
            step_executions = [
                n for n in step_nodes
                if n.properties.get("step_name") == step_name
            ]

            if step_executions:
                failures = [n for n in step_executions if n.properties.get("status") == "failure"]
                print(f"\n  Step: {step_name}")
                print(f"    Total executions: {len(step_executions)}")
                print(f"    Failures: {len(failures)}")
                print(f"    Failure rate: {len(failures)/len(step_executions):.1%}")

        # Run analysis
        print_subsection("AutoFlow Analysis")

        # Create rules
        rules = [
            FailingStepRule(workflow_id="data_pipeline", failure_threshold=0.15),
            SlowStepRule(workflow_id="data_pipeline", slowness_threshold_ms=3000),
            ErrorPropagationRule(workflow_id="data_pipeline"),
        ]

        decision_graph = EnhancedDecisionGraph(rules=rules)

        # Get all nodes for analysis
        all_nodes = list(store.query_nodes("workflow_step", limit=1000))

        proposals = decision_graph.run_with_graph(
            nodes=all_nodes,
            edges=list(delta.edges)
        )

        print(f"\nGenerated {len(proposals)} targeted proposals:\n")

        for i, p in enumerate(proposals, 1):
            print(f"{i}. {p.title}")
            print(f"   {p.description}")
            print(f"   Risk: {p.risk}")
            print(f"   Target: {p.target_paths[0]}")
            print(f"   Payload: {json.dumps(p.payload, indent=6)}")
            print()

        # Evaluate
        print_subsection("Evaluation")

        evaluator = ShadowEvaluator()
        results = [evaluator.evaluate(p) for p in proposals]

        for proposal, result in zip(proposals, results):
            print(f"  Proposal: {proposal.title[:50]}...")
            print(f"    Status: {'✓ PASS' if result.passed else '✗ FAIL'}")
            print()

    print_section("Demo Complete!")

    print("\nKey Takeaways:")
    print("  1. Tracked multi-step workflow with causal relationships")
    print("  2. Built context graph with edges showing flow and error propagation")
    print("  3. Analyzed each step independently to find bottlenecks")
    print("  4. Generated targeted proposals for specific problematic steps")
    print("  5. Each proposal includes context (failure rates, error types)")
    print("\nWhat This Enables:")
    print("  ✓ Identify which specific steps need improvement")
    print("  ✓ Understand error propagation through the pipeline")
    print("  ✓ Target fixes at the step level (not just whole workflow)")
    print("  ✓ Track improvement impact on individual steps")


if __name__ == "__main__":
    run_multistep_demo()
