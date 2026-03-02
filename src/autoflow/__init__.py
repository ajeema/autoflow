"""AutoFlow: Policy-gated, observable, evaluation-driven auto-improvement engine for AI workflows."""

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.orchestrator.engine_async import AsyncAutoImproveEngine
from autoflow.factory import (
    autoflow,
    autoflow_dbos,
    autoflow_dbos_pr,
    autoflow_testing,
    autoflow_persistent,
    autoflow_shadow,
    autoflow_auto_apply,
    autoflow_with_rules,
    autoflow_with_evaluators,
    DBOS_AVAILABLE,
)
from autoflow.types import ChangeProposal, ObservationEvent, EvaluationResult, RiskLevel
from autoflow.config import get_config, AutoFlowConfig, DatabaseConfig, ObservabilityConfig, PolicyConfig, DBOSConfig
from autoflow.apply.backend import NoOpBackend, LoggingBackend, CallbackBackend
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy

__all__ = [
    "AutoImproveEngine",
    "AsyncAutoImproveEngine",
    "autoflow",
    "autoflow_dbos",
    "autoflow_dbos_pr",
    "autoflow_testing",
    "autoflow_persistent",
    "autoflow_shadow",
    "autoflow_auto_apply",
    "autoflow_with_rules",
    "autoflow_with_evaluators",
    "DBOS_AVAILABLE",
    "ChangeProposal",
    "ObservationEvent",
    "EvaluationResult",
    "RiskLevel",
    "get_config",
    "AutoFlowConfig",
    "DatabaseConfig",
    "ObservabilityConfig",
    "PolicyConfig",
    "DBOSConfig",
    "NoOpBackend",
    "LoggingBackend",
    "CallbackBackend",
    "ProposalApplier",
    "ApplyPolicy",
]

# Conditional DBOS exports
try:
    from autoflow.apply.dbos_backend import DBOSBackend, DBOSScheduler, DBOSQueues
    __all__.extend(["DBOSBackend", "DBOSScheduler", "DBOSQueues"])
except ImportError:
    pass
