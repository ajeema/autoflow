"""
Demo: Human-in-the-loop proposal notifications and approval

This shows how proposals are generated, notified, and approved.
"""

import asyncio
from autoflow.factory import autoflow
from autoflow.human_in_the_loop import (
    HumanInTheLoopWorkflow,
    ApprovalMode,
    review_pending_proposals,
)
from autoflow.notify.notifier import create_notifier
from autoflow.observe.events import make_event


async def demo_notification():
    """Demo basic proposal notification."""
    print("\n" + "="*70)
    print("DEMO 1: Basic Proposal Notification")
    print("="*70)

    # Create engine with human-in-the-loop
    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    workflow = HumanInTheLoopWorkflow(
        approval_mode=ApprovalMode.MANUAL,
        notifier=create_notifier("console"),
    )

    # Simulate proposal generation
    proposals = [
        ChangeProposal(
            kind=ProposalKind.CONFIG_EDIT,
            title="Increase retry threshold for API workflow",
            description="The API workflow is failing frequently. Increasing max_retries from 3 to 5 and adding backoff should improve reliability.",
            risk=RiskLevel.LOW,
            target_paths=["config/workflows.yaml"],
            payload={
                "op": "set",
                "path": "workflows.api.retry_policy",
                "value": {"max_retries": 5, "backoff_ms": [100, 200, 400]}
            }
        ),
    ]

    context = {
        "triggering_events": [
            {"source": "agent", "name": "execution_failed", "workflow_id": "api"},
            {"source": "agent", "name": "execution_failed", "workflow_id": "api"},
            {"source": "agent", "name": "execution_failed", "workflow_id": "api"},
        ],
        "graph_context": {"error_rate": 0.15},
    }

    # Propose and notify
    notifications = await workflow.propose(proposals, context)

    print(f"\n✅ Generated {len(notifications)} proposal(s)")
    print("Check console output above for details")


async def demo_llm_judge():
    """Demo LLM-as-Judge evaluation."""
    print("\n" + "="*70)
    print("DEMO 2: LLM-as-Judge Evaluation")
    print("="*70)

    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    workflow = HumanInTheLoopWorkflow(
        approval_mode=ApprovalMode.LLM_JUDGE,
        notifier=create_notifier("console"),
        auto_approve_threshold=0.7,
    )

    proposals = [
        ChangeProposal(
            kind=ProposalKind.CONFIG_EDIT,
            title="Add rate limiting to API endpoint",
            description="Add rate limiting of 100 requests/min to the /api/search endpoint to prevent abuse.",
            risk=RiskLevel.LOW,
            target_paths=["config/api.yaml"],
            payload={
                "op": "set",
                "path": "api.rate_limits",
                "value": {"requests_per_minute": 100}
            }
        ),
    ]

    notifications = await workflow.propose(proposals)

    print("\n✅ LLM Judge evaluation complete")
    for notif in notifications:
        print(f"   Status: {notif.status.value}")
        print(f"   Evaluator: {notif.evaluator}")
        if notif.summary:
            print(f"   Summary: {notif.summary[:100]}...")


async def demo_hybrid_mode():
    """Demo hybrid approval mode."""
    print("\n" + "="*70)
    print("DEMO 3: Hybrid Mode (Auto low-risk, Manual high-risk)")
    print("="*70)

    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    workflow = HumanInTheLoopWorkflow(
        approval_mode=ApprovalMode.HYBRID,
        notifier=create_notifier("console"),
    )

    proposals = [
        ChangeProposal(
            kind=ProposalKind.TEXT_PATCH,
            title="Fix typo in README",
            description="Fix a typo in the README.md file.",
            risk=RiskLevel.LOW,
            target_paths=["README.md"],
            payload={"diff": "- old text\n+ new text"}
        ),
        ChangeProposal(
            kind=ProposalKind.REFACTORING,
            title="Refactor authentication module",
            description="Restructure the entire authentication module to improve maintainability. This is a significant change affecting multiple files.",
            risk=RiskLevel.HIGH,
            target_paths=["src/auth/", "src/api/auth.py"],
            payload={}
        ),
    ]

    notifications = await workflow.propose(proposals)

    print("\n✅ Processed proposals:")
    for notif in notifications:
        auto_approved = notif.status.value == "approved"
        print(f"   - {notif.proposal.title}")
        print(f"     Risk: {notif.proposal.risk}, Status: {notif.status.value}")
        print(f"     Auto-approved: {auto_approved}")


async def demo_file_notifications():
    """Demo file-based notifications."""
    print("\n" + "="*70)
    print("DEMO 4: File-Based Notifications")
    print("="*70)

    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    workflow = HumanInTheLoopWorkflow(
        approval_mode=ApprovalMode.MANUAL,
        notifier=create_notifier(
            ["console", "file"],
            output_path="proposals_demo.jsonl",
        ),
    )

    proposals = [
        ChangeProposal(
            kind=ProposalKind.CONFIG_EDIT,
            title="Demo proposal",
            description="This is a test proposal.",
            risk=RiskLevel.MEDIUM,
            target_paths=["config/test.yaml"],
            payload={}
        ),
    ]

    await workflow.propose(proposals)

    print("\n✅ Proposals saved to: proposals_demo.jsonl")
    print("   Check the file to see the notification format")


async def demo_interactive_review():
    """Demo interactive proposal review."""
    print("\n" + "="*70)
    print("DEMO 5: Interactive Review (Simulated)")
    print("="*70)

    from autoflow.human_in_the_loop import ProposalStore
    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    # Create workflow with persistent store
    workflow = HumanInTheLoopWorkflow(
        approval_mode=ApprovalMode.MANUAL,
        notifier=create_notifier("console", verbose=False),
        proposal_store=ProposalStore("demo_proposals.json"),
    )

    # Create multiple proposals
    proposals = [
        ChangeProposal(
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Proposal {i}",
            description=f"Test proposal {i}",
            risk=RiskLevel.LOW if i % 2 == 0 else RiskLevel.HIGH,
            target_paths=[f"config/test{i}.yaml"],
            payload={}
        )
        for i in range(1, 4)
    ]

    await workflow.propose(proposals)

    # Show pending
    pending = await workflow.list_pending()
    print(f"\n📋 {len(pending)} pending proposal(s)")

    # Simulate approving some
    print("\n✅ Approving proposal 1...")
    await workflow.submit_decision(
        pending[0].proposal.proposal_id,
        approved=True,
        reviewer="demo-user",
        feedback="Looks good, go ahead",
    )

    print("❌ Rejecting proposal 2...")
    await workflow.submit_decision(
        pending[1].proposal.proposal_id,
        approved=False,
        reviewer="demo-user",
        feedback="Not needed right now",
    )

    print("\n✅ Decisions saved")


async def main():
    """Run all demos."""
    await demo_notification()
    await demo_llm_judge()
    await demo_hybrid_mode()
    await demo_file_notifications()
    await demo_interactive_review()

    print("\n" + "="*70)
    print("All demos complete!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
