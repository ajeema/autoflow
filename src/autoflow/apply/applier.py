from autoflow.apply.policy import ApplyPolicy
from autoflow.types import ChangeProposal


class ProposalApplier:
    def __init__(self, policy: ApplyPolicy, backend: object) -> None:
        self.policy = policy
        self.backend = backend

    def apply(self, proposal: ChangeProposal) -> None:
        self.policy.assert_allowed(proposal)
        self.backend.apply(proposal)