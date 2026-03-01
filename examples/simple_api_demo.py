"""
Comparison: Old API vs New Simple API

This shows how much simpler AutoFlow is to use now.
"""

import asyncio
from autoflow.factory import autoflow
from autoflow.track import track_agent, track_workflow, track_error
from autoflow.observe.events import make_event


# =============================================================================
# OLD WAY (lots of boilerplate)
# =============================================================================

def old_way_example():
    """This is what you had to do before."""
    from autoflow.orchestrator.engine import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.graph.context_graph import ContextGraphBuilder
    from autoflow.decide.decision_graph import DecisionGraph
    from autoflow.decide.rules import HighErrorRateRetryRule
    from autoflow.evaluate.evaluator import CompositeEvaluator
    from autoflow.evaluate.shadow import ShadowEvaluator
    from autoflow.apply.applier import ProposalApplier
    from autoflow.apply.policy import ApplyPolicy
    from autoflow.apply.git_backend import GitApplyBackend
    from pathlib import Path

    # 1. Create store
    store = SQLiteGraphStore(db_path="autoflow.db")

    # 2. Create graph builder
    builder = ContextGraphBuilder()

    # 3. Create decision graph with rules
    graph = DecisionGraph(
        rules=[HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3)]
    )

    # 4. Create evaluator
    evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])

    # 5. Create applier
    applier = ProposalApplier(
        policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
        backend=GitApplyBackend(repo_path=Path(".")),
    )

    # 6. Create engine
    engine = AutoImproveEngine(
        store=store,
        graph_builder=builder,
        decision_graph=graph,
        evaluator=evaluator,
        applier=applier,
    )

    # 7. Use it
    events = [
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    ]
    engine.ingest(events)
    proposals = engine.propose()

    print(f"OLD WAY: Generated {len(proposals)} proposals")


# =============================================================================
# NEW WAY (minimal code)
# =============================================================================

async def new_way_example():
    """This is all you need now."""
    from autoflow.decide.rules import HighErrorRateRetryRule

    # Just create the engine with defaults
    engine = autoflow(
        rules=[HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3)]
    )

    # Use it
    events = [
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
        make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    ]
    await engine.ingest(events)
    proposals = await engine.propose()
    await engine.close()

    print(f"NEW WAY: Generated {len(proposals)} proposals")


# =============================================================================
# EVEN SIMPLER - with decorators
# =============================================================================

async def decorator_example():
    """Track agents with just a decorator."""

    @track_agent(agent_id="my_agent", model="gpt-4")
    async def my_agent(query: str):
        # Your agent logic here
        if "error" in query.lower():
            raise ValueError("Simulated error")
        return f"Response to: {query}"

    # Use the agent normally - tracking happens automatically
    try:
        result = await my_agent("error case")  # Error gets tracked
    except ValueError:
        pass

    result = await my_agent("normal query")  # Success gets tracked


# =============================================================================
# CONTEXT MANAGER EXAMPLE
# =============================================================================

async def context_manager_example():
    """Use autoflow as a context manager for auto-cleanup."""

    async with autoflow(in_memory=True) as engine:
        # Auto-tracks a workflow
        async with track_workflow(workflow_id="data_pipeline"):
            # Your workflow steps here
            await track_error("step1", Exception("Simulated error"))

        # AutoFlow can now propose fixes
        proposals = await engine.propose()
        print(f"Generated {len(proposals)} proposals for workflow issues")


# =============================================================================
# PRESET EXAMPLES
# =============================================================================

async def preset_examples():
    """Use presets for common cases."""

    # For testing
    engine = autoflow(in_memory=True)

    # For production
    engine = autoflow(db_path="./production.db")

    # For shadow evaluation (no applying)
    engine = autoflow(in_memory=True, enable_apply=False)

    # For auto-apply
    engine = autoflow(
        in_memory=True,
        enable_apply=True,
        allowed_paths=["config/", "prompts/"]
    )


# =============================================================================
# DEMO
# =============================================================================

async def main():
    print("=" * 70)
    print("AutoFlow API Comparison")
    print("=" * 70)

    print("\n1. OLD WAY (required ~30 lines of boilerplate):")
    old_way_example()

    print("\n2. NEW WAY (1 line!):")
    await new_way_example()

    print("\n3. DECORATOR TRACKING:")
    await decorator_example()

    print("\n4. CONTEXT MANAGER:")
    await context_manager_example()

    print("\n5. PRESETS:")
    await preset_examples()

    print("\n" + "=" * 70)
    print("The new API is MUCH simpler!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
