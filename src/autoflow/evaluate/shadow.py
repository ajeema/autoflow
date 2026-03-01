from autoflow.types import ChangeProposal, EvaluationResult


class ShadowEvaluator:
    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=True,
            score=1.0,
            metrics={"shadow_pass": 1.0},
        )