"""
Simplified AutoFlow factory for minimal boilerplate.

This module provides high-level functions that create AutoFlow engines
with sensible defaults, while still allowing full customization.

Usage:
    # Zero configuration - just works
    from autoflow.factory import autoflow

    async with autoflow() as engine:
        await engine.ingest(events)
        proposals = await engine.propose()

    # With custom store
    from autoflow.factory import autoflow

    engine = autoflow(store=my_custom_store)

    # With custom rules
    from autoflow.factory import autoflow
    from autoflow.decide.rules import HighErrorRateRetryRule

    engine = autoflow(rules=[HighErrorRateRetryRule(workflow_id="my_wf")])

    # Async context manager
    async with autoflow() as engine:
        await engine.ingest(events)
"""

import os
from pathlib import Path
from typing import Optional, Sequence, Any, Union

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.orchestrator.engine_async import AsyncAutoImproveEngine
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.store import ContextGraphStore
from autoflow.graph.store_async import AsyncContextGraphStore, InMemoryGraphStore
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.apply.backend import NoOpBackend

# Try to import DBOS backend
try:
    from autoflow.apply.dbos_backend import DBOSBackend, DBOS_AVAILABLE
except ImportError:
    DBOSBackend = None  # type: ignore
    DBOS_AVAILABLE = False


def autoflow(
    # Store configuration
    store: Union[ContextGraphStore, AsyncContextGraphStore, str, Path, None] = None,
    db_path: Union[str, Path, None] = None,
    in_memory: bool = False,
    async_mode: bool = False,  # Force async mode

    # Behavior configuration
    rules: Optional[Sequence] = None,
    evaluators: Optional[Sequence] = None,
    enable_apply: bool = False,
    allowed_paths: Optional[Sequence[str]] = None,

    # DBOS configuration
    enable_dbos: bool = False,
    dbos_apply_mode: str = "patch",
    dbos_pr_repository: Optional[str] = None,
    dbos_pr_branch_prefix: str = "autoflow/",

    # Advanced
    graph_builder: Optional[ContextGraphBuilder] = None,
    applier: Optional[ProposalApplier] = None,

) -> Union[AutoImproveEngine, AsyncAutoImproveEngine]:
    """
    Create an AutoFlow engine with sensible defaults.

    This is the simplest way to get started with AutoFlow. Just call autoflow()
    and you're ready to ingest events and generate proposals.

    Args:
        store: Custom store instance, or path to database, or None for default
        db_path: Path to SQLite database (default: "autoflow.db" in current dir)
        in_memory: Use in-memory store (ephemeral, good for testing)
        async_mode: Force async mode (default: auto-detect from store type)
        rules: List of decision rules to use
        evaluators: List of evaluators to use
        enable_apply: Whether to enable applying proposals (default: False for safety)
        allowed_paths: Paths that proposals are allowed to modify
        enable_dbos: Enable DBOS durable backend (requires: pip install 'autoflow[dbos]')
        dbos_apply_mode: DBOS apply mode: "patch" (git apply), "pr" (create PR), or "custom"
        dbos_pr_repository: GitHub repo for PR mode (e.g., "owner/repo")
        dbos_pr_branch_prefix: Branch name prefix for PRs
        graph_builder: Custom graph builder
        applier: Custom proposal applier

    Returns:
        AutoFlow engine (sync or async depending on store type or async_mode)

    Examples:
        # Easiest - in-memory store (sync)
        engine = autoflow(in_memory=True)
        engine.ingest(events)
        proposals = engine.propose()

        # Async mode
        engine = autoflow(in_memory=True, async_mode=True)
        await engine.ingest(events)
        proposals = await engine.propose()

        # With persistent storage
        engine = autoflow(db_path="./my_autoflow.db")

        # With custom rules
        from autoflow.decide.rules import HighErrorRateRetryRule
        engine = autoflow(rules=[
            HighErrorRateRetryRule(workflow_id="api", threshold=3)
        ])

        # Enable auto-apply
        engine = autoflow(
            enable_apply=True,
            allowed_paths=["config/", "prompts/"]
        )

        # With DBOS durable backend
        engine = autoflow(
            enable_apply=True,
            enable_dbos=True,
            allowed_paths=["config/", "prompts/"]
        )

        # With DBOS PR workflow
        engine = autoflow(
            enable_apply=True,
            enable_dbos=True,
            dbos_apply_mode="pr",
            dbos_pr_repository="myorg/myrepo",
        )
    """
    # Determine store
    if store is not None:
        # User provided a store instance
        final_store = store
    elif in_memory:
        # In-memory store (supports both sync and async)
        final_store = InMemoryGraphStore()
    else:
        # SQLite store (sync only)
        if db_path is None:
            db_path = os.environ.get("AUTOFLOW_DB_PATH", "autoflow.db")
        final_store = SQLiteGraphStore(db_path=str(db_path))

    # Detect if async mode requested
    if async_mode:
        is_async = True
    elif isinstance(final_store, InMemoryGraphStore):
        # InMemoryGraphStore supports both - default to sync for backward compat
        is_async = False
    else:
        # Other stores: check if they have async methods
        is_async = hasattr(final_store, 'aupsert') and callable(getattr(final_store, 'aupsert', None))

    # Build components with defaults
    builder = graph_builder or ContextGraphBuilder()
    graph = DecisionGraph(rules or [])
    evaluator = CompositeEvaluator(evaluators or [])

    # Build applier only if enabled
    if enable_apply:
        policy = ApplyPolicy(allowed_paths_prefixes=tuple(allowed_paths or ()))

        if enable_dbos:
            if not DBOS_AVAILABLE:
                raise ImportError(
                    "DBOS enabled but not installed. Install with: pip install 'autoflow[dbos]'"
                )
            backend = DBOSBackend(  # type: ignore
                repo_path=Path.cwd(),
                apply_mode=dbos_apply_mode,
                pr_repository=dbos_pr_repository,
                pr_branch_prefix=dbos_pr_branch_prefix,
            )
        else:
            backend = applier.backend if applier else NoOpBackend()

        final_applier = applier or ProposalApplier(policy=policy, backend=backend)
    else:
        final_applier = applier

    # Create engine
    if is_async:
        return AsyncAutoImproveEngine(
            store=final_store,
            graph_builder=builder,
            decision_graph=graph,
            evaluator=evaluator,
            applier=final_applier,
        )
    else:
        return AutoImproveEngine(
            store=final_store,
            graph_builder=builder,
            decision_graph=graph,
            evaluator=evaluator,
            applier=final_applier,
        )


# Presets for common use cases

def autoflow_testing():
    """Preset: In-memory store for testing."""
    return autoflow(in_memory=True)


def autoflow_persistent(db_path: Union[str, Path] = "autoflow.db"):
    """Preset: Persistent SQLite store."""
    return autoflow(db_path=db_path)


def autoflow_shadow():
    """Preset: Shadow evaluation (no applying)."""
    return autoflow(in_memory=True, enable_apply=False)


def autoflow_auto_apply(allowed_paths: Sequence[str] = ("config/", "prompts/")):
    """Preset: Auto-apply proposals to allowed paths."""
    return autoflow(
        in_memory=True,
        enable_apply=True,
        allowed_paths=allowed_paths
    )


def autoflow_with_rules(rules: Sequence, db_path: Union[str, Path, None] = None):
    """Preset: Custom rules with default store."""
    return autoflow(rules=rules, db_path=db_path)


def autoflow_with_evaluators(evaluators: Sequence, db_path: Union[str, Path, None] = None):
    """Preset: Custom evaluators with default store."""
    return autoflow(evaluators=evaluators, db_path=db_path)


# DBOS presets

def autoflow_dbos(allowed_paths: Sequence[str] = ("config/", "prompts/"), apply_mode: str = "patch"):
    """Preset: DBOS durable apply backend.

    Args:
        allowed_paths: Paths that proposals are allowed to modify
        apply_mode: DBOS apply mode ("patch", "pr", or "custom")

    Returns:
        AutoFlow engine with DBOS backend

    Examples:
        >>> engine = autoflow_dbos()
        >>> engine.ingest(events)
        >>> proposals = engine.propose()
    """
    return autoflow(
        in_memory=True,
        enable_apply=True,
        enable_dbos=True,
        allowed_paths=allowed_paths,
        dbos_apply_mode=apply_mode,
    )


def autoflow_dbos_pr(repository: str, allowed_paths: Sequence[str] = ("config/", "prompts/")):
    """Preset: DBOS with PR-based apply workflow.

    Creates pull requests instead of directly applying patches.

    Args:
        repository: GitHub repository (e.g., "owner/repo")
        allowed_paths: Paths that proposals are allowed to modify

    Returns:
        AutoFlow engine with DBOS PR workflow

    Examples:
        >>> engine = autoflow_dbos_pr("myorg/myrepo")
        >>> engine.ingest(events)
        >>> proposals = engine.propose()
    """
    return autoflow(
        in_memory=True,
        enable_apply=True,
        enable_dbos=True,
        dbos_apply_mode="pr",
        dbos_pr_repository=repository,
        allowed_paths=allowed_paths,
    )


__all__ = [
    "autoflow",
    "autoflow_testing",
    "autoflow_persistent",
    "autoflow_shadow",
    "autoflow_auto_apply",
    "autoflow_with_rules",
    "autoflow_with_evaluators",
    "autoflow_dbos",
    "autoflow_dbos_pr",
    "DBOS_AVAILABLE",
]
