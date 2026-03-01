"""
AutoFlow main entry point.

Provides both legacy CLI functionality and new Pydantic-based CLI.
"""

import argparse
import sys
from pathlib import Path

# Import for legacy CLI
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.orchestrator.engine import AutoImproveEngine


def main_legacy() -> int:
    """
    Legacy CLI entry point.

    Maintains backward compatibility with existing CLI usage.
    """
    parser = argparse.ArgumentParser(prog="autoflow")
    parser.add_argument("--db", default="autoflow_graph.db")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--workflow-id", default="my_workflow")
    parser.add_argument("--threshold", type=int, default=3)
    args = parser.parse_args()

    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=args.db),
        graph_builder=ContextGraphBuilder(),
        decision_graph=DecisionGraph(
            rules=[HighErrorRateRetryRule(workflow_id=args.workflow_id, threshold=args.threshold)]
        ),
        evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
        applier=ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/", "prompts/", "skills/")),
            backend=GitApplyBackend(repo_path=Path(args.repo)),
        ),
    )

    # Emit a few synthetic failures so propose() returns something in a demo.
    engine.ingest(
        [
            make_event(source="cli", name="exception", attributes={"workflow_id": args.workflow_id}),
            make_event(source="cli", name="exception", attributes={"workflow_id": args.workflow_id}),
            make_event(source="cli", name="exception", attributes={"workflow_id": args.workflow_id}),
        ]
    )

    proposals = engine.propose()
    results = engine.evaluate(proposals)
    applied = engine.apply(proposals, results)

    print(f"proposals={len(proposals)} applied={len(applied)}")
    for p in proposals:
        print(f"- {p.title} (risk={p.risk})")
    return 0


def main():
    """
    Main entry point for AutoFlow CLI.

    Detects if new CLI commands are being used and routes appropriately.
    """
    # Check if any new CLI command is present
    if len(sys.argv) > 1 and sys.argv[1] in [
        "propose",
        "evaluate",
        "apply",
        "query",
        "ingest",
        "status",
        "config",
        "init",
    ]:
        # Use new CLI
        from autoflow.cli import app
        app()
    else:
        # Use legacy CLI
        sys.exit(main_legacy())


if __name__ == "__main__":
    main()
