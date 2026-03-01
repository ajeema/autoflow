"""
Human-in-the-loop workflow for AutoFlow proposals.

Manages the lifecycle of proposals from generation to approval/rejection,
with support for automatic and manual approval modes.
"""

import json
import asyncio
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from autoflow.types import ChangeProposal, EvaluationResult, ObservationEvent
from autoflow.notify.notifier import (
    NotificationChannel,
    ProposalNotification,
    ProposalStatus,
    create_notifier,
)


class ApprovalMode(str, Enum):
    """How proposals should be approved."""
    AUTO = "auto"                      # Auto-approve if evaluator passes
    MANUAL = "manual"                  # Require human approval
    HYBRID = "hybrid"                  # Auto-approve low-risk, manual for high-risk
    LLM_JUDGE = "llm_judge"            # Use LLM judge instead of human


@dataclass
class ApprovalDecision:
    """Human approval decision for a proposal."""
    proposal_id: str
    approved: bool
    reviewer: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feedback: Optional[str] = None
    changes_requested: Optional[Dict[str, Any]] = None


class ProposalStore:
    """
    Storage for proposal lifecycle tracking.

    Can be backed by file, database, or in-memory.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self._proposals: Dict[str, ProposalNotification] = {}
        self._decisions: Dict[str, ApprovalDecision] = {}

        if self.storage_path:
            self._load()

    def save_proposal(self, notification: ProposalNotification) -> None:
        """Save a proposal notification."""
        self._proposals[notification.proposal.proposal_id] = notification
        self._persist()

    def get_proposal(self, proposal_id: str) -> Optional[ProposalNotification]:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        limit: int = 100,
    ) -> List[ProposalNotification]:
        """List proposals with optional filtering."""
        proposals = list(self._proposals.values())

        if status:
            proposals = [p for p in proposals if p.status == status]

        # Sort by creation time, newest first
        proposals.sort(key=lambda p: p.created_at, reverse=True)

        return proposals[:limit]

    def save_decision(self, decision: ApprovalDecision) -> None:
        """Save an approval decision."""
        self._decisions[decision.proposal_id] = decision

        # Update proposal status
        proposal = self._proposals.get(decision.proposal_id)
        if proposal:
            proposal.status = ProposalStatus.APPROVED if decision.approved else ProposalStatus.REJECTED
            proposal.evaluation_result = EvaluationResult(
                proposal_id=decision.proposal_id,
                passed=decision.approved,
                score=1.0 if decision.approved else 0.0,
                metrics={"evaluator": "human"},
                notes=decision.feedback or "",
            )

        self._persist()

    def get_decision(self, proposal_id: str) -> Optional[ApprovalDecision]:
        """Get a decision by proposal ID."""
        return self._decisions.get(proposal_id)

    def _persist(self) -> None:
        """Persist to storage if configured."""
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "proposals": {
                    pid: notif.model_dump()
                    for pid, notif in self._proposals.items()
                },
                "decisions": {
                    pid: dec.model_dump()
                    for pid, dec in self._decisions.items()
                },
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        """Load from storage if exists."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            # Load proposals
            for pid, notif_data in data.get("proposals", {}).items():
                self._proposals[pid] = ProposalNotification(**notif_data)

            # Load decisions
            for pid, dec_data in data.get("decisions", {}).items():
                self._decisions[pid] = ApprovalDecision(**dec_data)
        except Exception as e:
            print(f"⚠️  Failed to load proposal store: {e}")


class HumanInTheLoopWorkflow:
    """
    Manages human-in-the-loop workflow for AutoFlow proposals.

    Features:
    - Proposal generation and notification
    - Approval workflow (auto/manual/hybrid/llm_judge)
    - Proposal tracking and persistence
    - Integration with any notification channel
    """

    def __init__(
        self,
        approval_mode: ApprovalMode = ApprovalMode.MANUAL,
        notifier: Optional[NotificationChannel] = None,
        proposal_store: Optional[ProposalStore] = None,
        auto_approve_threshold: float = 0.8,  # For LLM judge
    ):
        self.approval_mode = approval_mode
        self.notifier = notifier or create_notifier("console")
        self.store = proposal_store
        self.auto_approve_threshold = auto_approve_threshold

    async def propose(
        self,
        proposals: List[ChangeProposal],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ProposalNotification]:
        """
        Generate proposals and handle notifications/approvals.

        Args:
            proposals: List of proposals to process
            context: Additional context (triggering events, graph state, etc.)

        Returns:
            List of ProposalNotification objects
        """
        context = context or {}
        notifications = []

        for proposal in proposals:
            # Create notification
            notification = ProposalNotification(
                proposal=proposal,
                status=ProposalStatus.PENDING,
                triggering_events=context.get("triggering_events", []),
                graph_context=context.get("graph_context", {}),
            )

            # Evaluate based on approval mode
            if self.approval_mode == ApprovalMode.AUTO:
                notification = await self._auto_approve(notification)

            elif self.approval_mode == ApprovalMode.HYBRID:
                notification = await self._hybrid_approve(notification)

            elif self.approval_mode == ApprovalMode.LLM_JUDGE:
                notification = await self._llm_judge_approve(notification)

            # Save to store
            if self.store:
                self.store.save_proposal(notification)

            # Notify
            await self.notifier.notify_proposals([proposal], context)

            notifications.append(notification)

        return notifications

    async def _auto_approve(self, notification: ProposalNotification) -> ProposalNotification:
        """Auto-approve (no evaluation)."""
        notification.status = ProposalStatus.APPROVED
        notification.evaluator = "auto"
        return notification

    async def _hybrid_approve(self, notification: ProposalNotification) -> ProposalNotification:
        """Auto-approve low-risk, manual for high-risk."""
        if notification.proposal.risk.lower() == "low":
            notification.status = ProposalStatus.APPROVED
            notification.evaluator = "auto"
        else:
            notification.status = ProposalStatus.PENDING
            notification.evaluator = "pending_human"
        return notification

    async def _llm_judge_approve(self, notification: ProposalNotification) -> ProposalNotification:
        """Use LLM judge to evaluate."""
        try:
            from autoflow.evaluate.llm_judge import LLMJudgeEvaluator

            evaluator = LLMJudgeEvaluator()
            result = evaluator.evaluate(notification.proposal)

            notification.evaluation_result = result
            notification.evaluator = "llm_judge"

            if result.score >= self.auto_approve_threshold:
                notification.status = ProposalStatus.APPROVED
            else:
                notification.status = ProposalStatus.PENDING
                notification.summary = result.notes

        except Exception as e:
            print(f"⚠️  LLM judge evaluation failed: {e}")
            notification.status = ProposalStatus.PENDING
            notification.evaluator = "evaluation_failed"

        return notification

    async def submit_decision(
        self,
        proposal_id: str,
        approved: bool,
        reviewer: str,
        feedback: Optional[str] = None,
    ) -> None:
        """
        Submit a human approval decision.

        Args:
            proposal_id: ID of the proposal
            approved: Whether the proposal is approved
            reviewer: Name/ID of the reviewer
            feedback: Optional feedback/comments
        """
        decision = ApprovalDecision(
            proposal_id=proposal_id,
            approved=approved,
            reviewer=reviewer,
            feedback=feedback,
        )

        if self.store:
            self.store.save_decision(decision)

        # Notify about decision
        proposal = self.store.get_proposal(proposal_id) if self.store else None
        if proposal:
            await self.notifier.notify_evaluation(
                proposal.proposal,
                decision.approved,
            )

    async def list_pending(self) -> List[ProposalNotification]:
        """List all pending proposals awaiting human review."""
        if self.store:
            return self.store.list_proposals(status=ProposalStatus.PENDING)
        return []

    async def approve_all(
        self,
        reviewer: str,
        proposal_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Approve one or more proposals.

        Args:
            reviewer: Name/ID of the reviewer
            proposal_ids: Specific proposals to approve, or None for all pending
        """
        if self.store:
            if proposal_ids:
                proposals = [self.store.get_proposal(pid) for pid in proposal_ids]
            else:
                proposals = self.store.list_proposals(status=ProposalStatus.PENDING)

            for proposal in proposals:
                await self.submit_decision(
                    proposal.proposal.proposal_id,
                    approved=True,
                    reviewer=reviewer,
                )

    async def reject_all(
        self,
        reviewer: str,
        proposal_ids: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> None:
        """
        Reject one or more proposals.

        Args:
            reviewer: Name/ID of the reviewer
            proposal_ids: Specific proposals to reject, or None for all pending
            reason: Reason for rejection
        """
        if self.store:
            if proposal_ids:
                proposals = [self.store.get_proposal(pid) for pid in proposal_ids]
            else:
                proposals = self.store.list_proposals(status=ProposalStatus.PENDING)

            for proposal in proposals:
                await self.submit_decision(
                    proposal.proposal.proposal_id,
                    approved=False,
                    reviewer=reviewer,
                    feedback=reason,
                )


# =============================================================================
# Convenience functions
# =============================================================================

async def review_pending_proposals(
    workflow: HumanInTheLoopWorkflow,
    interactive: bool = True,
) -> None:
    """
    Interactive review of pending proposals.

    Args:
        workflow: The workflow instance
        interactive: If True, prompt user for each proposal
    """
    pending = await workflow.list_pending()

    if not pending:
        print("✅ No pending proposals to review")
        return

    print(f"\n📋 {len(pending)} pending proposal(s) to review\n")

    for i, proposal_notif in enumerate(pending, 1):
        proposal = proposal_notif.proposal

        print(f"\n[{i}] {proposal.title}")
        print(f"    ID: {proposal.proposal_id}")
        print(f"    Risk: {proposal.risk}")
        print(f"    Description: {proposal.description}")
        if proposal_notif.summary:
            print(f"    Summary: {proposal_notif.summary}")

        if interactive:
            # Simple CLI prompt
            while True:
                response = input(f"\n    Approve? [y/n/a=skip] ").strip().lower()
                if response in ['y', 'yes']:
                    await workflow.submit_decision(
                        proposal.proposal_id,
                        approved=True,
                        reviewer="cli-user",
                        feedback="Approved via CLI",
                    )
                    print("    ✅ Approved")
                    break
                elif response in ['n', 'no']:
                    feedback = input("    Reason (optional): ").strip()
                    await workflow.submit_decision(
                        proposal.proposal_id,
                        approved=False,
                        reviewer="cli-user",
                        feedback=feedback or None,
                    )
                    print("    ❌ Rejected")
                    break
                elif response in ['a', 'skip']:
                    print("    ⏭️  Skipped")
                    break
                else:
                    print("    Please enter y, n, or a")


__all__ = [
    # Enums
    "ApprovalMode",
    # Classes
    "ApprovalDecision",
    "ProposalStore",
    "HumanInTheLoopWorkflow",
    # Convenience
    "review_pending_proposals",
]
