"""
AutoFlow API with Notification and Human-in-the-Loop Support

This module provides a simplified API for AutoFlow with notifications
and human approval workflows.
"""

from typing import List, Optional, Union, Dict, Any

from autoflow.factory import autoflow as base_autoflow
from autoflow.human_in_the_loop import (
    HumanInTheLoopWorkflow,
    ApprovalMode,
)
from autoflow.notify.notifier import (
    NotificationChannel,
    create_notifier,
)


def autoflow_with_notifications(
    # Basic autoflow options
    store=None,
    db_path=None,
    in_memory=False,
    rules=None,
    evaluators=None,
    enable_apply=False,
    allowed_paths=None,

    # Notification options
    notify: Union[str, List[str], NotificationChannel] = "console",
    notification_config: Optional[Dict[str, Any]] = None,

    # Human-in-the-loop options
    approval_mode: str = "manual",
    proposal_store_path: Optional[str] = None,

):
    """
    Create AutoFlow with notifications and human-in-the-loop support.

    This is the simplest way to get started with AutoFlow that includes
    proposal notifications and human approval workflows.

    Args:
        notify: Notification channel(s) - "console", "file", "webhook", or list
        notification_config: Config for notification channels
        approval_mode: How to approve proposals
            - "auto": Auto-approve everything
            - "manual": Require human approval
            - "hybrid": Auto low-risk, manual high-risk
            - "llm_judge": Use LLM to evaluate
        proposal_store_path: Path to store proposal tracking data

    Returns:
        HumanInTheLoopWorkflow instance

    Examples:
        # Simple - console notifications, manual approval
        workflow = autoflow_with_notifications()

        # Console + file notifications
        workflow = autoflow_with_notifications(
            notify=["console", "file"],
            notification_config={"output_path": "proposals.jsonl"}
        )

        # LLM judge with console notifications
        workflow = autoflow_with_notifications(
            approval_mode="llm_judge",
            notify="console",
        )

        # Auto-approve low-risk, manual high-risk
        workflow = autoflow_with_notifications(
            approval_mode="hybrid",
        )
    """
    # Create notifier
    if isinstance(notify, str) or isinstance(notify, list):
        notifier = create_notifier(notify, **(notification_config or {}))
    else:
        notifier = notify

    # Convert approval_mode string to enum
    approval_enum = ApprovalMode(approval_mode)

    # Create workflow
    workflow = HumanInTheLoopWorkflow(
        approval_mode=approval_enum,
        notifier=notifier,
        proposal_store=proposal_store_path,
    )

    return workflow


# Convenience presets

def autoflow_llm_judge(
    model: str = "gpt-4",
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    region: Optional[str] = None,
    auto_approve_threshold: float = 0.8,
    notify: Union[str, List[str]] = "console",
):
    """
    Quick setup for LLM-as-Judge mode.

    Evaluates proposals using the specified LLM and auto-approves
    if confidence is high enough.

    Supports multiple providers:
    - OpenAI: model="gpt-4"
    - Anthropic: model="claude-3-5-sonnet-20241022"
    - AWS Bedrock: model="amazon.titan-text-express-v1"
    - xAI (Grok): model="grok-beta"
    - Ollama: model="llama3:8b"
    - Azure OpenAI: model="azure/gpt-4"

    Example:
        # OpenAI GPT-4
        workflow = autoflow_llm_judge(model="gpt-4")

        # Anthropic Claude
        workflow = autoflow_llm_judge(model="claude-3-5-sonnet-20241022")

        # Ollama local model
        workflow = autoflow_llm_judge(model="llama3:8b")

        # AWS Bedrock
        workflow = autoflow_llm_judge(
            model="amazon.titan-text-express-v1",
            region="us-east-1"
        )

        await workflow.propose(proposals, context)
    """
    import os

    # Set environment variables if provided
    if api_key:
        os.environ["AUTOFLOW_LLM_JUDGE_API_KEY"] = api_key
    if provider:
        os.environ["AUTOFLOW_LLM_JUDGE_PROVIDER"] = provider
    if base_url:
        os.environ["AUTOFLOW_LLM_JUDGE_BASE_URL"] = base_url
    if region:
        os.environ["AWS_DEFAULT_REGION"] = region

    # Set model
    os.environ["AUTOFLOW_LLM_JUDGE_MODEL"] = model

    workflow = autoflow_with_notifications(
        approval_mode="llm_judge",
        notify=notify,
    )

    # Update threshold if custom
    if auto_approve_threshold != 0.8:
        workflow.auto_approve_threshold = auto_approve_threshold

    return workflow


def autoflow_auto_approve(
    notify: Union[str, List[str]] = "console",
):
    """
    Quick setup for auto-approve mode.

    All proposals that pass evaluation are automatically approved.
    Useful for fully automated workflows.

    Example:
        workflow = autoflow_auto_approve()
        await workflow.propose(proposals, context)
    """
    return autoflow_with_notifications(
        approval_mode="auto",
        notify=notify,
    )


def autoflow_manual_review(
    notify: Union[str, List[str]] = "console",
    proposal_store_path: str = "proposals.json",
):
    """
    Quick setup for manual review mode.

    All proposals require human approval before being applied.
    This is the safest mode for production use.

    Example:
        workflow = autoflow_manual_review()
        await workflow.propose(proposals, context)

        # Later, review pending:
        pending = await workflow.list_pending()
        await workflow.approve_all(reviewer="admin")
    """
    return autoflow_with_notifications(
        approval_mode="manual",
        notify=notify,
        proposal_store_path=proposal_store_path,
    )


def autoflow_hybrid(
    notify: Union[str, List[str]] = "console",
    proposal_store_path: str = "proposals.json",
):
    """
    Quick setup for hybrid mode.

    Low-risk proposals are auto-approved, high-risk require manual review.
    Good balance of automation and safety.

    Example:
        workflow = autoflow_hybrid()
        await workflow.propose(proposals, context)
    """
    return autoflow_with_notifications(
        approval_mode="hybrid",
        notify=notify,
        proposal_store_path=proposal_store_path,
    )


__all__ = [
    "autoflow_with_notifications",
    "autoflow_llm_judge",
    "autoflow_auto_approve",
    "autoflow_manual_review",
    "autoflow_hybrid",
]
