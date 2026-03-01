from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import uuid4

from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from autoflow.types import GraphNode


@dataclass(frozen=True)
class RetryTuningRule:
    workflow_id: str
    exception_threshold: int = 5

    def propose(self, nodes: Sequence[GraphNode]) -> Sequence[ChangeProposal]:
        exceptions = [
            n for n in nodes
            if n.node_type == "event"
            and n.properties.get("name") == "exception"
            and n.properties.get("workflow_id") == self.workflow_id
        ]
        if len(exceptions) < self.exception_threshold:
            return []

        return [
            ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title=f"Tune retry policy for {self.workflow_id}",
                description="Repeated exceptions observed; propose bounded retry/backoff to improve reliability.",
                risk=RiskLevel.LOW,
                target_paths=("config/workflows.yaml",),
                payload={
                    "op": "set",
                    "path": f"workflows.{self.workflow_id}.retry_policy",
                    "value": {"max_retries": 3, "backoff_ms": [250, 1000, 5000], "jitter": True},
                },
            )
        ]