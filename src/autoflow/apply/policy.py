from autoflow.errors import PolicyViolation
from autoflow.types import ChangeProposal, RiskLevel


class ApplyPolicy:
    def __init__(self, allowed_paths_prefixes: tuple[str, ...], max_risk: RiskLevel = RiskLevel.LOW) -> None:
        self.allowed_paths_prefixes = allowed_paths_prefixes
        self.max_risk = max_risk

    def assert_allowed(self, proposal: ChangeProposal) -> None:
        if proposal.risk != self.max_risk:
            raise PolicyViolation("Risk exceeds policy.")

        for path in proposal.target_paths:
            if not any(path.startswith(p) for p in self.allowed_paths_prefixes):
                raise PolicyViolation(f"Path not allowed: {path}")