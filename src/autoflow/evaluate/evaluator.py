from typing import Sequence

from autoflow.types import ChangeProposal, EvaluationResult


class CompositeEvaluator:
    def __init__(self, evaluators: Sequence[object]) -> None:
        self.evaluators = evaluators

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        results = [e.evaluate(proposal) for e in self.evaluators]
        passed = all(r.passed for r in results)
        # Handle empty evaluators case
        score = sum(r.score for r in results) / len(results) if results else 0.0
        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            score=score,
            metrics={"avg_score": score},
        )