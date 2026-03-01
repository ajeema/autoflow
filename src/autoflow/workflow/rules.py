"""
Workflow Rule Classes

Base classes and common patterns for workflow analysis rules.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Dict, Any
from uuid import uuid4

from autoflow.types import (
    ChangeProposal,
    ProposalKind,
    RiskLevel,
    GraphNode,
    GraphEdge,
    StepStatus,
)
from autoflow.workflow.queries import WorkflowQueryHelpers
from autoflow.workflow.metrics import (
    step_failure_rate,
    step_latency_stats,
    step_error_types,
)


class WorkflowRule(ABC):
    """
    Base class for workflow analysis rules.

    Provides common patterns for analyzing workflow executions
    and generating proposals.
    """

    def __init__(self, workflow_id: str):
        """
        Args:
            workflow_id: The workflow to analyze
        """
        self.workflow_id = workflow_id

    @abstractmethod
    def propose(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> List[ChangeProposal]:
        """
        Analyze workflow and generate proposals.

        Args:
            nodes: Graph nodes (workflow steps)
            edges: Optional graph edges (relationships)

        Returns:
            List of proposals
        """
        pass

    def filter_workflow_nodes(
        self,
        nodes: Sequence[GraphNode],
    ) -> List[GraphNode]:
        """Filter to only nodes from this workflow."""
        return WorkflowQueryHelpers.filter_by_workflow(nodes, self.workflow_id)


class FailingStepRule(WorkflowRule):
    """
    Identifies steps with high failure rates and proposes fixes.

    Generates targeted proposals based on the most common error type.
    """

    def __init__(
        self,
        workflow_id: str,
        failure_threshold: float = 0.15,
    ):
        """
        Args:
            workflow_id: Workflow to analyze
            failure_threshold: Alert if failure rate exceeds this (e.g., 0.15 = 15%)
        """
        super().__init__(workflow_id)
        self.failure_threshold = failure_threshold

    def propose(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> List[ChangeProposal]:
        """Find failing steps and propose fixes."""
        workflow_nodes = self.filter_workflow_nodes(nodes)

        if len(workflow_nodes) < 5:
            return []

        # Group by step name
        steps_by_name = WorkflowQueryHelpers.group_by_step(workflow_nodes)

        proposals = []

        for step_name, executions in steps_by_name.items():
            failure_rate = step_failure_rate(executions)

            if failure_rate >= self.failure_threshold:
                proposal = self._create_step_proposal(
                    step_name=step_name,
                    executions=executions,
                    failure_rate=failure_rate,
                )
                if proposal:
                    proposals.append(proposal)

        return proposals

    def _create_step_proposal(
        self,
        step_name: str,
        executions: List[GraphNode],
        failure_rate: float,
    ) -> Optional[ChangeProposal]:
        """Create a proposal for a failing step."""

        # Analyze error types
        error_counts = step_error_types(executions)

        if not error_counts:
            return None

        most_common_error = max(error_counts, key=error_counts.get)

        # Get latency stats for failed vs successful runs
        failed_executions = [n for n in executions if n.properties.get("status") == "failure"]
        successful_executions = [n for n in executions if n.properties.get("status") == "success"]

        failed_latency = step_latency_stats(failed_executions)
        success_latency = step_latency_stats(successful_executions)

        # Generate proposal based on error type
        if most_common_error == "timeout":
            return self._timeout_proposal(
                step_name, failure_rate, failed_latency, success_latency
            )
        elif most_common_error == "rate_limit":
            return self._rate_limit_proposal(step_name, failure_rate)
        elif most_common_error == "validation_error":
            return self._validation_proposal(step_name, failure_rate, error_counts)
        elif most_common_error == "auth_error":
            return self._auth_proposal(step_name, failure_rate)
        else:
            return self._generic_error_proposal(
                step_name, failure_rate, most_common_error, error_counts
            )

    def _timeout_proposal(
        self,
        step_name: str,
        failure_rate: float,
        failed_latency: Dict[str, float],
        success_latency: Dict[str, float],
    ) -> ChangeProposal:
        """Create proposal for timeout issues."""
        suggested_timeout = int(failed_latency["p95_ms"] * 1.5)

        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Increase timeout for '{step_name}' step",
            description=(
                f"Step '{step_name}' is failing due to timeouts "
                f"({failure_rate:.1%} failure rate). "
                f"Failed runs have P95 latency of {failed_latency['p95_ms']:.0f}ms vs "
                f"{success_latency['p95_ms']:.0f}ms for successful runs."
            ),
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "setting": "timeout_ms",
                "value": suggested_timeout,
                "old_value": int(success_latency["p95_ms"] * 1.2),
            },
        )

    def _rate_limit_proposal(
        self,
        step_name: str,
        failure_rate: float,
    ) -> ChangeProposal:
        """Create proposal for rate limit issues."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Add rate limiting for '{step_name}' step",
            description=(
                f"Step '{step_name}' is hitting rate limits "
                f"({failure_rate:.1%} failure rate). "
                f"Proposing backoff and retry configuration."
            ),
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "add_retry_policy": {
                    "max_retries": 3,
                    "backoff_ms": [1000, 2000, 5000],
                },
                "add_rate_limiter": {
                    "requests_per_second": 10,
                },
            },
        )

    def _validation_proposal(
        self,
        step_name: str,
        failure_rate: float,
        error_counts: Dict[str, int],
    ) -> ChangeProposal:
        """Create proposal for validation errors."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Improve validation in '{step_name}' step",
            description=(
                f"Step '{step_name}' has validation errors "
                f"({failure_rate:.1%} failure rate). "
                f"Error types: {error_counts}. "
                f"Proposing schema validation and error handling improvements."
            ),
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "add_validation": True,
                "error_handling": "strict",
                "schema_validation": True,
            },
        )

    def _auth_proposal(
        self,
        step_name: str,
        failure_rate: float,
    ) -> ChangeProposal:
        """Create proposal for authentication errors."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Fix authentication in '{step_name}' step",
            description=(
                f"Step '{step_name}' has authentication failures "
                f"({failure_rate:.1%} failure rate). "
                f"Check credentials, token refresh logic, and permissions."
            ),
            risk=RiskLevel.MEDIUM,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "fix_authentication": True,
                "add_token_refresh": True,
            },
        )

    def _generic_error_proposal(
        self,
        step_name: str,
        failure_rate: float,
        error_type: str,
        error_counts: Dict[str, int],
    ) -> ChangeProposal:
        """Create generic error proposal."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Improve error handling in '{step_name}' step",
            description=(
                f"Step '{step_name}' is failing "
                f"({failure_rate:.1%} failure rate, "
                f"most common error: {error_type}). "
                f"All errors: {error_counts}"
            ),
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "add_error_handling": True,
                "log_errors": True,
                "improve_resilience": True,
            },
        )


class SlowStepRule(WorkflowRule):
    """
    Identifies slow workflow steps that are bottlenecks.

    Proposes optimizations like caching, batching, or parallelization.
    """

    def __init__(
        self,
        workflow_id: str,
        slowness_threshold_ms: float = 5000,
    ):
        """
        Args:
            workflow_id: Workflow to analyze
            slowness_threshold_ms: Alert if P95 latency exceeds this
        """
        super().__init__(workflow_id)
        self.slowness_threshold_ms = slowness_threshold_ms

    def propose(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> List[ChangeProposal]:
        """Find slow steps and propose optimizations."""
        workflow_nodes = self.filter_workflow_nodes(nodes)

        if len(workflow_nodes) < 5:
            return []

        # Group by step name
        steps_by_name = WorkflowQueryHelpers.group_by_step(workflow_nodes)

        proposals = []

        for step_name, executions in steps_by_name.items():
            latency_stats = step_latency_stats(executions)

            if latency_stats["p95_ms"] >= self.slowness_threshold_ms:
                proposals.append(self._create_optimization_proposal(
                    step_name=step_name,
                    executions=executions,
                    latency_stats=latency_stats,
                ))

        return proposals

    def _create_optimization_proposal(
        self,
        step_name: str,
        executions: List[GraphNode],
        latency_stats: Dict[str, float],
    ) -> ChangeProposal:
        """Create optimization proposal for a slow step."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Optimize slow step: '{step_name}'",
            description=(
                f"Step '{step_name}' has P95 latency of {latency_stats['p95_ms']:.0f}ms "
                f"(threshold: {self.slowness_threshold_ms:.0f}ms, "
                f"avg: {latency_stats['avg_ms']:.0f}ms). "
                f"Proposing optimization strategies."
            ),
            risk=RiskLevel.LOW,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "optimization": "enable_caching",
                "config": {
                    "cache_ttl_seconds": 300,
                    "enable_batch_processing": True,
                    "batch_size": 100,
                    "enable_parallelization": True,
                    "max_concurrency": 5,
                },
            },
        )


class ErrorPropagationRule(WorkflowRule):
    """
    Analyzes how errors propagate through workflows.

    Identifies root cause failures that cause cascading downstream failures.
    """

    def __init__(
        self,
        workflow_id: str,
        cascade_threshold: int = 3,
    ):
        """
        Args:
            workflow_id: Workflow to analyze
            cascade_threshold: Alert if failure causes N+ downstream failures
        """
        super().__init__(workflow_id)
        self.cascade_threshold = cascade_threshold

    def propose(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> List[ChangeProposal]:
        """Find error propagation and propose resilience improvements."""
        if edges is None:
            return []

        workflow_nodes = self.filter_workflow_nodes(nodes)

        # Find error propagations
        propagations = WorkflowQueryHelpers.find_error_propagation(
            workflow_nodes, edges
        )

        if not propagations:
            return []

        # Count downstream failures per root cause
        from collections import Counter
        downstream_counts = Counter()

        for prop in propagations:
            from_step = prop["from_step"]
            downstream_counts[from_step] += 1

        proposals = []

        for step_name, downstream_failures in downstream_counts.items():
            if downstream_failures >= self.cascade_threshold:
                proposals.append(self._create_resilience_proposal(
                    step_name=step_name,
                    downstream_failures=downstream_failures,
                ))

        return proposals

    def _create_resilience_proposal(
        self,
        step_name: str,
        downstream_failures: int,
    ) -> ChangeProposal:
        """Create resilience proposal."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Add resilience to '{step_name}' step",
            description=(
                f"Step '{step_name}' failures are causing "
                f"{downstream_failures} downstream step failures. "
                f"Proposing retry logic, circuit breaker, and graceful degradation."
            ),
            risk=RiskLevel.MEDIUM,
            target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
            payload={
                "step": step_name,
                "add_retry_policy": {
                    "max_retries": 3,
                    "backoff_ms": [500, 1000, 2000],
                },
                "add_circuit_breaker": {
                    "failure_threshold": 5,
                    "reset_timeout_ms": 30000,
                },
                "add_fallback": True,
            },
        )
