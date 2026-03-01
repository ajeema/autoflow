from uuid import uuid4

from autoflow.types import ChangeProposal, ProposalKind, RiskLevel, GraphNode


class HighErrorRateRetryRule:
    def __init__(self, workflow_id: str, threshold: int = 3) -> None:
        self.workflow_id = workflow_id
        self.threshold = threshold

    def propose(self, nodes: list[GraphNode]) -> list[ChangeProposal]:
        exceptions = [
            n for n in nodes
            if n.properties.get("workflow_id") == self.workflow_id
            and n.properties.get("name") == "exception"
        ]

        if len(exceptions) < self.threshold:
            return []

        return [
            ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title="Increase retry policy",
                description="Observed repeated exceptions.",
                risk=RiskLevel.LOW,
                target_paths=("config/workflows.yaml",),
                payload={"retry": {"max_retries": 3}},
            )
        ]