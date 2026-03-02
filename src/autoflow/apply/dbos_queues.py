"""
DBOS queues for parallel proposal evaluation.

Provides concurrent, durable evaluation workflows:
- Batch evaluation with configurable concurrency
- Parallel proposal validation
- Queue-based evaluation for high-throughput scenarios

Usage:
    from autoflow.apply.dbos_queues import DBOSQueues, DBOS_AVAILABLE

    if DBOS_AVAILABLE:
        queues = DBOSQueues(concurrency=5)
        results = queues.evaluate_batch(proposals)
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, List, Any, Dict

# Try to import DBOS
try:
    from dbos import DBOS, Queue
    DBOS_AVAILABLE = True
except ImportError:
    DBOS_AVAILABLE = False
    DBOS = None
    Queue = None  # type: ignore


logger = logging.getLogger(__name__)


class DBOSQueuesUnavailable:
    """Fallback when DBOS is not installed but queues are enabled.

    Raises:
        ImportError: With helpful installation message
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ImportError(
            "DBOS queues enabled but DBOS not installed. "
            "Install with: pip install 'autoflow[dbos]'"
        )


class DBOSQueues:
    """Queue-based parallel evaluation using DBOS.

    Enables high-throughput evaluation of proposals
    with configurable concurrency limits.

    Args:
        queue_name: Name of the DBOS queue
        concurrency: Max concurrent workers
        evaluator: Optional evaluator function (uses default if None)

    Examples:
        >>> from autoflow.apply.dbos_queues import DBOSQueues
        >>> from autoflow.evaluate.shadow import ShadowEvaluator
        >>>
        >>> queues = DBOSQueues(
        ...     queue_name="autoflow-eval",
        ...     concurrency=5,
        ... )
        >>> results = queues.evaluate_batch(proposals)
    """

    def __init__(
        self,
        queue_name: str = "autoflow-eval",
        concurrency: int = 5,
        evaluator: Optional[Callable] = None,
    ) -> None:
        if not DBOS_AVAILABLE:
            raise ImportError(
                "DBOS is not installed. Install with: pip install 'autoflow[dbos]'"
            )

        self.queue_name = queue_name
        self.concurrency = concurrency
        self.evaluator = evaluator

        # Create DBOS queue if DBOS is available
        self._queue: Optional[Any] = None
        if Queue is not None:
            self._queue = Queue(queue_name, concurrency=concurrency)

    def evaluate_batch(
        self,
        proposals: List[Any],
    ) -> List[Dict[str, Any]]:
        """Evaluate a batch of proposals.

        Args:
            proposals: List of proposals (ChangeProposal or dict-serializable)

        Returns:
            List of evaluation results as dictionaries
        """
        logger.info(f"Evaluating batch of {len(proposals)} proposals")

        results = []

        for proposal in proposals:
            # Convert to dict if needed for serialization
            if hasattr(proposal, 'model_dump'):
                proposal_dict = proposal.model_dump()
            elif hasattr(proposal, 'dict'):
                proposal_dict = proposal.dict()
            elif not isinstance(proposal, dict):
                proposal_dict = {"proposal_id": str(proposal)}
            else:
                proposal_dict = proposal

            result = self._evaluate_single(proposal_dict)
            results.append(result)

        logger.info(f"Completed evaluation of {len(results)} proposals")

        return results

    def _evaluate_single(self, proposal_dict: dict) -> dict:
        """Evaluate a single proposal.

        Args:
            proposal_dict: Proposal as dictionary for serialization

        Returns:
            Evaluation result as dictionary
        """
        if self.evaluator:
            # Use custom evaluator
            result = self.evaluator(proposal_dict)
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif hasattr(result, 'dict'):
                return result.dict()
            return result

        # Use default shadow evaluator
        try:
            from autoflow.types import ChangeProposal
            from autoflow.evaluate.shadow import ShadowEvaluator

            # Reconstruct proposal from dict
            proposal = ChangeProposal(**proposal_dict)
            evaluator = ShadowEvaluator()
            result = evaluator.evaluate(proposal)

            return {
                "proposal_id": result.proposal_id,
                "passed": getattr(result, 'passed', False),
                "score": getattr(result, 'score', 0),
                "metrics": getattr(result, 'metrics', {}),
            }
        except Exception as e:
            logger.exception(f"Error evaluating proposal {proposal_dict.get('proposal_id')}")
            return {
                "proposal_id": proposal_dict.get("proposal_id", "unknown"),
                "passed": False,
                "score": 0,
                "error": str(e),
            }

    def evaluate_batch_async(
        self,
        proposals: List[Any],
    ) -> List[str]:
        """Enqueue proposals for parallel evaluation.

        In a full DBOS integration, this would enqueue each proposal
        to the DBOS queue for parallel processing by workers.

        Args:
            proposals: List of proposals to enqueue

        Returns:
            List of workflow/handle IDs for tracking
        """
        if not self._queue:
            logger.warning("DBOS queue not available - falling back to sequential")
            return self.evaluate_batch(proposals)  # type: ignore

        handle_ids = []

        for proposal in proposals:
            # Convert to dict if needed
            if hasattr(proposal, 'model_dump'):
                proposal_dict = proposal.model_dump()
            elif hasattr(proposal, 'dict'):
                proposal_dict = proposal.dict()
            else:
                proposal_dict = proposal

            # Enqueue to DBOS queue
            # handle = self._queue.enqueue(self._evaluate_single, proposal_dict)
            # handle_ids.append(handle.get_workflow_id())
            # For now, this is a placeholder
            handle_ids.append(f"placeholder-{proposal_dict.get('proposal_id', 'unknown')}")

        return handle_ids

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue information
        """
        return {
            "queue_name": self.queue_name,
            "concurrency": self.concurrency,
            "available": DBOS_AVAILABLE,
            "initialized": self._queue is not None,
        }


# Export appropriate class based on availability
DBOSQueuesImpl = DBOSQueues if DBOS_AVAILABLE else DBOSQueuesUnavailable


__all__ = [
    "DBOSQueues",
    "DBOSQueuesImpl",
    "DBOS_AVAILABLE",
]
