from pathlib import Path

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


def test_engine_smoke(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"

    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=str(db_path)),
        graph_builder=ContextGraphBuilder(),
        decision_graph=DecisionGraph(rules=[HighErrorRateRetryRule(workflow_id="wf", threshold=2)]),
        evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
        applier=ProposalApplier(
            policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            backend=GitApplyBackend(repo_path=tmp_path),
        ),
    )

    engine.ingest(
        [
            make_event(source="test", name="exception", attributes={"workflow_id": "wf"}),
            make_event(source="test", name="exception", attributes={"workflow_id": "wf"}),
        ]
    )

    proposals = engine.propose()
    assert len(proposals) >= 1
    results = [engine.evaluator.evaluate(p) for p in proposals]
    assert all(r.passed for r in results)