#!/usr/bin/env python3
"""
AutoFlow Demo Script

This script demonstrates the key features of the AutoFlow library:
1. Basic shadow evaluation for workflow optimization
2. Replay-based evaluation with AI datasets
3. Policy-gated application of changes

Run with: python demo.py
"""

import json
import tempfile
from pathlib import Path
from shutil import rmtree

# Add src to path for development
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.evaluate.replay import ReplayGates
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import RiskLevel

# Import AI module components
try:
    from autoflow_ai.dataset import load_jsonl_dataset
    from autoflow_ai.eval.replay_ai import AIReplayEvaluator
    from autoflow_ai.rules.retry_tuning import RetryTuningRule
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: autoflow_ai module not available. Install with: pip install 'autoflow[ai]'")


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---\n")


def demo_basic_shadow_evaluation() -> None:
    """Demonstrate basic shadow evaluation for workflow optimization."""
    print_section("DEMO 1: Basic Shadow Evaluation")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "autoflow.db"

        # Create a sample config file
        config_dir = tmpdir / "config"
        config_dir.mkdir()
        config_file = config_dir / "workflows.yaml"
        config_file.write_text("""
workflows:
  data_pipeline:
    retry_policy:
      max_retries: 1
      backoff_ms: [100]
      jitter: false
""")

        print_subsection("Setup")
        print(f"Working directory: {tmpdir}")
        print(f"Database: {db_path}")
        print(f"Config file: {config_file}")
        print("\nInitial retry policy: max_retries=1, backoff_ms=[100]")

        # Initialize the engine
        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=str(db_path)),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(
                rules=[
                    HighErrorRateRetryRule(
                        workflow_id="data_pipeline",
                        threshold=3  # Trigger after 3 exceptions
                    )
                ]
            ),
            evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
            applier=ProposalApplier(
                policy=ApplyPolicy(
                    allowed_paths_prefixes=("config/",),
                    max_risk=RiskLevel.LOW
                ),
                backend=GitApplyBackend(repo_path=tmpdir),
            ),
        )

        print_subsection("Ingesting Events")
        # Simulate system emitting exception events
        events = [
            make_event(
                source="data_pipeline",
                name="exception",
                attributes={
                    "workflow_id": "data_pipeline",
                    "error_type": "ConnectionError"
                }
            ),
            make_event(
                source="data_pipeline",
                name="exception",
                attributes={
                    "workflow_id": "data_pipeline",
                    "error_type": "TimeoutError"
                }
            ),
            make_event(
                source="data_pipeline",
                name="exception",
                attributes={
                    "workflow_id": "data_pipeline",
                    "error_type": "ConnectionError"
                }
            ),
        ]

        for i, event in enumerate(events, 1):
            print(f"  Event {i}: {event.name} from {event.source} - {event.attributes['error_type']}")

        engine.ingest(events)

        print_subsection("Generating Proposals")
        proposals = engine.propose()
        print(f"Generated {len(proposals)} proposal(s):")
        for p in proposals:
            print(f"  - {p.title}")
            print(f"    Kind: {p.kind}")
            print(f"    Risk: {p.risk}")
            print(f"    Description: {p.description}")
            print(f"    Target: {p.target_paths}")
            print(f"    Payload: {json.dumps(p.payload, indent=4)}")

        print_subsection("Evaluating Proposals (Shadow Mode)")
        # Evaluate proposals
        results = [engine.evaluator.evaluate(p) for p in proposals]
        for r in results:
            print(f"  Proposal {r.proposal_id[:8]}...")
            print(f"    Passed: {r.passed}")
            print(f"    Score: {r.score:.2f}")
            print(f"    Notes: {r.notes}")

        print_subsection("Applying Changes")
        # Apply only proposals that passed evaluation
        applied = []
        for proposal, result in zip(proposals, results):
            if result.passed:
                engine.applier.apply(proposal)
                applied.append(proposal)
        print(f"Applied {len(applied)} change(s):")
        for a in applied:
            print(f"  - {a.title} -> {a.target_paths[0]}")


def demo_ai_replay_evaluation() -> None:
    """Demonstrate AI replay evaluation with a JSONL dataset."""
    if not AI_AVAILABLE:
        print("\n[Skipping AI Replay Demo - autoflow_ai not installed]")
        print("Install with: pip install 'autoflow[ai]'\n")
        return

    print_section("DEMO 2: AI Replay Evaluation")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "autoflow_ai.db"

        # Create sample replay dataset
        replay_file = tmpdir / "replay_runs.jsonl"
        create_sample_dataset(replay_file)

        print_subsection("Setup")
        print(f"Working directory: {tmpdir}")
        print(f"Database: {db_path}")
        print(f"Replay dataset: {replay_file}")

        # Load and display dataset
        dataset = load_jsonl_dataset(str(replay_file))
        print(f"\nLoaded {len(dataset.runs)} historical runs")
        print("\nSample runs:")
        for i, run in enumerate(dataset.runs[:3], 1):
            print(f"  Run {i}: {run.run_id} - workflow={run.workflow_id}, "
                  f"success={run.outcome.success}, "
                  f"tool_calls={len(run.tool_calls)}, "
                  f"model_calls={len(run.model_calls)}")

        # Compute baseline metrics
        print_subsection("Baseline Metrics")
        from autoflow_ai.metrics import compute_metrics
        baseline = compute_metrics(dataset, workflow_id="support_router")
        print(f"  Success rate: {baseline.success_rate:.1%}")
        print(f"  Override rate: {baseline.override_rate:.1%}")
        print(f"  Tool error rate: {baseline.tool_error_rate:.1%}")
        print(f"  P95 tool latency: {baseline.p95_tool_latency_ms:.0f}ms")
        print(f"  P95 model latency: {baseline.p95_model_latency_ms:.0f}ms")
        print(f"  Avg cost: ${baseline.avg_cost_usd:.4f}")

        # Setup engine with replay evaluator
        ai_replay_evaluator = AIReplayEvaluator(
            dataset=dataset,
            workflow_id="support_router",
            gates=ReplayGates(
                max_regressions={
                    "p95_tool_latency_ms": 100.0,  # Don't regress by > 100ms
                    "avg_cost_usd": 0.02,          # Don't increase cost by > 2 cents
                },
                min_improvements={
                    "success_rate": 0.01,          # Must improve by >= 1%
                },
            ),
        ).as_core()

        # Also get the core replay evaluator for direct evaluation
        core_replay_evaluator = ai_replay_evaluator

        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=str(db_path)),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(
                rules=[
                    RetryTuningRule(
                        workflow_id="support_router",
                        exception_threshold=2
                    )
                ]
            ),
            evaluator=CompositeEvaluator(evaluators=[
                ShadowEvaluator(),
                core_replay_evaluator
            ]),
            applier=ProposalApplier(
                policy=ApplyPolicy(
                    allowed_paths_prefixes=("config/",),
                    max_risk=RiskLevel.LOW
                ),
                backend=GitApplyBackend(repo_path=tmpdir),
            ),
        )

        # Ingest exception events
        print_subsection("Ingesting Events")
        events = [
            make_event(
                source="support_agent",
                name="exception",
                attributes={
                    "workflow_id": "support_router",
                    "error_type": "SearchTimeout"
                }
            ),
            make_event(
                source="support_agent",
                name="exception",
                attributes={
                    "workflow_id": "support_router",
                    "error_type": "APIThrottleError"
                }
            ),
        ]
        engine.ingest(events)
        print(f"Ingested {len(events)} exception events")

        # Generate and evaluate proposals
        print_subsection("Generating Proposals")
        proposals = engine.propose()
        print(f"Generated {len(proposals)} proposal(s):")
        for p in proposals:
            print(f"  - {p.title}")
            print(f"    Proposed retry policy: {p.payload.get('value')}")

        print_subsection("Evaluating with Replay Gates")
        # Use the core replay evaluator directly to get detailed metrics
        results = [core_replay_evaluator.evaluate(p) for p in proposals]
        for r in results:
            print(f"  Proposal {r.proposal_id[:8]}...")
            print(f"    Passed: {r.passed}")
            print(f"    Score: {r.score:.4f}")

            # Show baseline vs candidate metrics
            print("\n    Metrics comparison:")
            baseline_metrics = {k: v for k, v in r.metrics.items() if k.startswith("baseline.")}
            candidate_metrics = {k: v for k, v in r.metrics.items() if k.startswith("candidate.")}

            # Get all unique metric names
            metric_names = set(k.replace("baseline.", "").replace("candidate.", "")
                              for k in list(baseline_metrics.keys()) + list(candidate_metrics.keys()))

            for metric_name in sorted(metric_names):
                baseline_val = r.metrics.get(f"baseline.{metric_name}", "N/A")
                candidate_val = r.metrics.get(f"candidate.{metric_name}", "N/A")
                delta_val = r.metrics.get(f"delta.{metric_name}")

                # Format the values
                if "rate" in metric_name or "success" in metric_name:
                    baseline_str = f"{float(baseline_val):.1%}" if baseline_val != "N/A" else "N/A"
                    candidate_str = f"{float(candidate_val):.1%}" if candidate_val != "N/A" else "N/A"
                    delta_str = f"{delta_val:+.1%}" if delta_val is not None else "N/A"
                elif "latency" in metric_name:
                    baseline_str = f"{float(baseline_val):.0f}ms" if baseline_val != "N/A" else "N/A"
                    candidate_str = f"{float(candidate_val):.0f}ms" if candidate_val != "N/A" else "N/A"
                    delta_str = f"{delta_val:+.0f}ms" if delta_val is not None else "N/A"
                elif "cost" in metric_name:
                    baseline_str = f"${float(baseline_val):.4f}" if baseline_val != "N/A" else "N/A"
                    candidate_str = f"${float(candidate_val):.4f}" if candidate_val != "N/A" else "N/A"
                    delta_str = f"${delta_val:+.4f}" if delta_val is not None else "N/A"
                else:
                    baseline_str = str(baseline_val)
                    candidate_str = str(candidate_val)
                    delta_str = f"{delta_val:+.4f}" if delta_val is not None else "N/A"

                print(f"      {metric_name}:")
                print(f"        Baseline: {baseline_str}")
                print(f"        Candidate: {candidate_str}")
                print(f"        Delta: {delta_str}")

            print(f"\n    Evaluation result: {r.notes}")

        print_subsection("Summary")
        print("Replay evaluation ensures:")
        print("  - No regression in P95 latency beyond allowed threshold")
        print("  - No cost increase beyond budget")
        print("  - Minimum required improvement in success rate")
        print("  - Changes are validated on historical data before production")


def create_sample_dataset(path: Path) -> None:
    """Create a sample AI replay dataset."""
    dataset_content = """{"run_id":"run_001","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":120,"success":true},{"tool":"api_call","latency_ms":250,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":300,"input_tokens":800,"output_tokens":200}],"outcome":{"success":true,"human_override":false,"cost_usd":0.012}}
{"run_id":"run_002","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":450,"success":false,"error_type":"timeout"},{"tool":"api_call","latency_ms":280,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":280,"input_tokens":700,"output_tokens":180}],"outcome":{"success":false,"human_override":true,"cost_usd":0.010}}
{"run_id":"run_003","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":200,"success":true},{"tool":"api_call","latency_ms":220,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":320,"input_tokens":900,"output_tokens":220}],"outcome":{"success":true,"human_override":false,"cost_usd":0.013}}
{"run_id":"run_004","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":150,"success":true},{"tool":"api_call","latency_ms":180,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":250,"input_tokens":750,"output_tokens":190}],"outcome":{"success":true,"human_override":false,"cost_usd":0.011}}
{"run_id":"run_005","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":380,"success":false,"error_type":"rate_limit"},{"tool":"api_call","latency_ms":240,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":290,"input_tokens":820,"output_tokens":200}],"outcome":{"success":false,"human_override":true,"cost_usd":0.012}}
{"run_id":"run_006","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":110,"success":true},{"tool":"api_call","latency_ms":200,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":280,"input_tokens":780,"output_tokens":210}],"outcome":{"success":true,"human_override":false,"cost_usd":0.011}}
{"run_id":"run_007","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":190,"success":true},{"tool":"api_call","latency_ms":230,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":310,"input_tokens":850,"output_tokens":205}],"outcome":{"success":true,"human_override":false,"cost_usd":0.012}}
{"run_id":"run_008","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":420,"success":false,"error_type":"timeout"},{"tool":"api_call","latency_ms":260,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":270,"input_tokens":730,"output_tokens":175}],"outcome":{"success":false,"human_override":true,"cost_usd":0.010}}
{"run_id":"run_009","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":140,"success":true},{"tool":"api_call","latency_ms":190,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":260,"input_tokens":800,"output_tokens":195}],"outcome":{"success":true,"human_override":false,"cost_usd":0.011}}
{"run_id":"run_010","workflow_id":"support_router","tool_calls":[{"tool":"vector_search","latency_ms":210,"success":true},{"tool":"api_call","latency_ms":240,"success":true}],"model_calls":[{"model":"gpt-4","latency_ms":300,"input_tokens":870,"output_tokens":215}],"outcome":{"success":true,"human_override":false,"cost_usd":0.012}}
"""
    path.write_text(dataset_content)


def main() -> None:
    """Run all demo scenarios."""
    print("\n" + "=" * 70)
    print("  AutoFlow Library Demo")
    print("  Policy-Gated Auto-Improvement for AI Workflows")
    print("=" * 70)

    try:
        demo_basic_shadow_evaluation()
        demo_ai_replay_evaluation()

        print_section("Demo Complete!")
        print("\nKey Takeaways:")
        print("  1. AutoFlow observes system events and builds a context graph")
        print("  2. Decision rules detect optimization opportunities")
        print("  3. Proposals are evaluated before application (shadow/replay)")
        print("  4. Policy gates enforce safety (path restrictions, risk levels)")
        print("  5. Replay evaluation validates changes on historical data")
        print("\nFor more information, see README.md\n")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
