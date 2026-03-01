#!/usr/bin/env python3
"""
Enhanced Multi-Step Workflow Demo

This demo uses the new workflow module features to analyze
a multi-step pipeline with proper workflow tracking.

Demonstrates:
1. WorkflowAwareGraphBuilder - builds workflow relationships
2. WorkflowQueryHelpers - query and analyze workflows
3. Workflow metrics - calculate step-level metrics
4. Workflow rules - targeted proposals for failing steps
"""

import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import StepStatus, ProposalKind, RiskLevel, ChangeProposal

# New workflow imports
from autoflow.workflow import WorkflowAwareGraphBuilder, WorkflowQueryHelpers
from autoflow.workflow.rules import FailingStepRule, SlowStepRule, ErrorPropagationRule
from autoflow.workflow.metrics import step_failure_rate, step_latency_stats, step_error_types

# Use the query helpers class
query_helpers = WorkflowQueryHelpers()


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    print(f"\n--- {title} ---\n")


def simulate_workflow_events(num_runs: int = 20):
    """Simulate a 4-step data pipeline workflow."""
    events = []

    for run_num in range(1, num_runs + 1):
        run_id = f"data_pipeline_{run_num}"

        # Simulate failures
        extract_timeout = random.random() < 0.20
        transform_error = random.random() < 0.10
        load_rate_limit = random.random() < 0.15

        # Step 1: Extract
        if extract_timeout:
            events.append(make_event(
                source="workflow_engine",
                name="step_execution",
                attributes={
                    "workflow_id": "data_pipeline",
                    "workflow_run_id": run_id,
                    "step_name": "extract",
                    "step_id": f"{run_id}_step_1",
                    "step_order": 1,
                    "status": StepStatus.FAILURE.value,
                    "latency_ms": 8500 + random.randint(-500, 1000),
                    "error_type": "timeout",
                },
            ))
            # Downstream steps skipped
            for i, step in enumerate(["transform", "validate", "load"], 2):
                events.append(make_event(
                    source="workflow_engine",
                    name="step_execution",
                    attributes={
                        "workflow_id": "data_pipeline",
                        "workflow_run_id": run_id,
                        "step_name": step,
                        "step_id": f"{run_id}_step_{i+2}",
                        "parent_step_id": f"{run_id}_step_{i+1}",
                        "step_order": i + 2,
                        "status": StepStatus.SKIPPED.value,
                        "latency_ms": 0,
                    },
                ))
        else:
            events.append(make_event(
                source="workflow_engine",
                name="step_execution",
                attributes={
                    "workflow_id": "data_pipeline",
                    "workflow_run_id": run_id,
                    "step_name": "extract",
                    "step_id": f"{run_id}_step_1",
                    "step_order": 1,
                    "status": StepStatus.SUCCESS.value,
                    "latency_ms": 500 + random.randint(-100, 300),
                },
            ))

            # Step 2: Transform
            if transform_error:
                events.append(make_event(
                    source="workflow_engine",
                    name="step_execution",
                    attributes={
                        "workflow_id": "data_pipeline",
                        "workflow_run_id": run_id,
                        "step_name": "transform",
                        "step_id": f"{run_id}_step_2",
                        "parent_step_id": f"{run_id}_step_1",
                        "step_order": 2,
                        "status": StepStatus.FAILURE.value,
                        "latency_ms": 1200,
                        "error_type": "validation_error",
                    },
                ))
                # Validate and Load skipped
                for i, step in enumerate(["validate", "load"], 2):
                    events.append(make_event(
                        source="workflow_engine",
                        name="step_execution",
                        attributes={
                            "workflow_id": "data_pipeline",
                            "workflow_run_id": run_id,
                            "step_name": step,
                            "step_id": f"{run_id}_step_{i+3}",
                            "parent_step_id": f"{run_id}_step_{i+2}",
                            "step_order": i + 3,
                            "status": StepStatus.SKIPPED.value,
                            "latency_ms": 0,
                        },
                    ))
            else:
                events.append(make_event(
                    source="workflow_engine",
                    name="step_execution",
                    attributes={
                        "workflow_id": "data_pipeline",
                        "workflow_run_id": run_id,
                        "step_name": "transform",
                        "step_id": f"{run_id}_step_2",
                        "parent_step_id": f"{run_id}_step_1",
                        "step_order": 2,
                        "status": StepStatus.SUCCESS.value,
                        "latency_ms": 1000 + random.randint(-200, 400),
                    },
                ))

                # Step 3: Validate
                events.append(make_event(
                    source="workflow_engine",
                    name="step_execution",
                    attributes={
                        "workflow_id": "data_pipeline",
                        "workflow_run_id": run_id,
                        "step_name": "validate",
                        "step_id": f"{run_id}_step_3",
                        "parent_step_id": f"{run_id}_step_2",
                        "step_order": 3,
                        "status": StepStatus.SUCCESS.value,
                        "latency_ms": 400 + random.randint(-100, 200),
                    },
                ))

                # Step 4: Load
                if load_rate_limit:
                    events.append(make_event(
                        source="workflow_engine",
                        name="step_execution",
                        attributes={
                            "workflow_id": "data_pipeline",
                            "workflow_run_id": run_id,
                            "step_name": "load",
                            "step_id": f"{run_id}_step_4",
                            "parent_step_id": f"{run_id}_step_3",
                            "step_order": 4,
                            "status": StepStatus.FAILURE.value,
                            "latency_ms": 2100,
                            "error_type": "rate_limit",
                        },
                    ))
                else:
                    events.append(make_event(
                        source="workflow_engine",
                        name="step_execution",
                        attributes={
                            "workflow_id": "data_pipeline",
                            "workflow_run_id": run_id,
                            "step_name": "load",
                            "step_id": f"{run_id}_step_4",
                            "parent_step_id": f"{run_id}_step_3",
                            "step_order": 4,
                            "status": StepStatus.SUCCESS.value,
                            "latency_ms": 700 + random.randint(-100, 300),
                        },
                    ))

    return events


def run_workflow_demo():
    """Run the enhanced workflow demo."""

    print_section("Enhanced Multi-Step Workflow Demo")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "workflow.db"

        print_subsection("Simulating Data Pipeline Workflow")
        print("4-step pipeline: extract → transform → validate → load")
        print("Failure modes: extract timeouts, transform validation, load rate limits")

        # Generate events
        workflow_events = simulate_workflow_events(25)
        print(f"Generated {len(workflow_events)} step execution events")

        # Build workflow-aware graph
        print_subsection("Building Workflow-Aware Context Graph")

        builder = WorkflowAwareGraphBuilder()
        delta = builder.build_delta(workflow_events)

        print(f"Created {len(delta.nodes)} nodes")
        print(f"Created {len(delta.edges)} edges")

        # Edge breakdown
        edge_types = {}
        for edge in delta.edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        print("Edge types:")
        for etype, count in edge_types.items():
            print(f"  - {etype}: {count}")

        # Store in database
        print_subsection("Storing in Graph Database")

        store = SQLiteGraphStore(db_path=str(db_path))
        store.upsert(delta)

        # Query nodes
        nodes = store.query_nodes(node_type="workflow_step", limit=1000)
        edges = store.query_edges(limit=1000)

        print(f"Retrieved {len(nodes)} workflow_step nodes")
        print(f"Retrieved {len(edges)} edges")

        # Filter and analyze
        print_subsection("Workflow Analysis with Query Helpers")

        pipeline_nodes = query_helpers.filter_by_workflow(nodes, "data_pipeline")
        print(f"Data pipeline steps: {len(pipeline_nodes)}")

        # Group by step
        steps_by_name = query_helpers.group_by_step(pipeline_nodes)
        print(f"\nStep breakdown:")

        for step_name, step_nodes in steps_by_name.items():
            failure_rate = step_failure_rate(step_nodes)
            latency = step_latency_stats(step_nodes)
            errors = step_error_types(step_nodes)

            print(f"\n  {step_name}:")
            print(f"    Executions: {len(step_nodes)}")
            print(f"    Failure rate: {failure_rate:.1%}")
            print(f"    P95 latency: {latency['p95_ms']:.0f}ms")
            if errors:
                print(f"    Error types: {errors}")

        # Status breakdown
        status_counts = query_helpers.count_by_status(pipeline_nodes)
        print(f"\nOverall status breakdown:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

        # Error propagation analysis
        print_subsection("Error Propagation Analysis")

        propagations = query_helpers.find_error_propagation(pipeline_nodes, edges)
        print(f"Found {len(propagations)} error propagations:")

        if propagations:
            # Group by causing step
            from collections import Counter
            causes = Counter(p["from_step"] for p in propagations)
            for step, count in causes.most_common(5):
                print(f"  - {step}: caused {count} downstream failures")

        # Root cause analysis
        root_causes = query_helpers.find_root_cause_failures(pipeline_nodes, edges)
        print(f"\nRoot cause failures: {len(root_causes)}")

        for rc in root_causes[:5]:
            print(f"  - {rc.properties.get('step_name')}: {rc.properties.get('error_type')}")

        # Generate proposals with workflow rules
        print_subsection("AutoFlow Analysis with Workflow Rules")

        rules = [
            FailingStepRule("data_pipeline", failure_threshold=0.10),
            SlowStepRule("data_pipeline", slowness_threshold_ms=3000),
            ErrorPropagationRule("data_pipeline", cascade_threshold=2),
        ]

        decision_graph = DecisionGraph(rules=rules)
        proposals = decision_graph.run(nodes, edges)

        print(f"\nGenerated {len(proposals)} proposals:")

        for i, proposal in enumerate(proposals, 1):
            print(f"\n{i}. {proposal.title}")
            print(f"   {proposal.description}")
            print(f"   Risk: {proposal.risk}")
            print(f"   Payload: {proposal.payload}")

        # Evaluate
        print_subsection("Evaluation")

        evaluator = ShadowEvaluator()
        results = [evaluator.evaluate(p) for p in proposals]

        for proposal, result in zip(proposals, results):
            print(f"\n  {proposal.title[:60]}...")
            print(f"    Status: {'✓ PASS' if result.passed else '✗ FAIL'}")

    print_section("Demo Complete!")

    print("\n🎯 New Features Demonstrated:")
    print("  ✓ WorkflowAwareGraphBuilder - builds workflow relationships")
    print("  ✓ WorkflowQueryHelpers - filter, group, analyze workflows")
    print("  ✓ Workflow metrics - failure rates, latency stats, error types")
    print("  ✓ FailingStepRule - targeted proposals for failing steps")
    print("  ✓ SlowStepRule - identifies bottlenecks")
    print("  ✓ ErrorPropagationRule - tracks error cascades")
    print("\n📦 Workflow Module:")
    print("  - autoflow.workflow.graph_builder")
    print("  - autoflow.workflow.queries")
    print("  - autoflow.workflow.metrics")
    print("  - autoflow.workflow.rules")


if __name__ == "__main__":
    run_workflow_demo()
