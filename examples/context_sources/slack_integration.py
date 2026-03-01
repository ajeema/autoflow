#!/usr/bin/env python3
"""
AutoFlow Context Source: Slack Integration

This example demonstrates how to integrate AutoFlow with Slack for:
- Notifying teams about proposed improvements
- Getting human approval for changes
- Retrieving context from Slack messages/conversations
- Posting execution results to channels

Setup:
    pip install slack-sdk

Create a Slack App:
    1. Go to https://api.slack.com/apps
    2. Create new app → "From scratch"
    3. Add OAuth scopes:
       - chat:write (post messages)
       - channels:read (list channels)
       - channels:history (read messages)
       - reactions:write (add reactions)
    4. Install app to workspace
    5. Copy Bot User OAuth Token

Environment variables:
    export SLACK_BOT_TOKEN=xoxb-your-token-here
    export SLACK_SIGNING_SECRET=your-signing-secret
    export SLACK_CHANNEL=#autoflow-improvements
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# =============================================================================
# Slack Integration Types
# =============================================================================

class ApprovalStatus(Enum):
    """Approval status for proposals."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class SlackProposal:
    """A proposal awaiting Slack approval."""
    proposal_id: str
    title: str
    description: str
    risk_level: str
    target_paths: tuple[str, ...]
    message_ts: str  # Slack message timestamp for thread
    channel: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    comments: list[str] = None

    def __post_init__(self):
        if self.comments is None:
            self.comments = []


# =============================================================================
# Slack Client Wrapper
# =============================================================================

class SlackClient:
    """Simplified Slack client for AutoFlow integration."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        default_channel: Optional[str] = None,
    ):
        """
        Initialize Slack client.

        Args:
            bot_token: Slack Bot User OAuth Token (xoxb-...)
            default_channel: Default channel for messages
        """
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.default_channel = default_channel or os.getenv("SLACK_CHANNEL", "#autoflow")

        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN must be set")

        try:
            from slack_sdk.web import WebClient
            from slack_sdk.socket_mode import SocketModeClient

            self.web_client = WebClient(token=self.bot_token)
            self.socket_client = None

        except ImportError:
            raise ImportError("slack-sdk required: pip install slack-sdk")

    async def post_message(
        self,
        channel: Optional[str] = None,
        text: str = "",
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> dict[str, Any]:
        """Post a message to Slack."""

        channel = channel or self.default_channel

        response = self.web_client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts,
        )

        return {
            "channel": response["channel"],
            "ts": response["ts"],
            "message": response["message"],
        }

    async def post_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str,
    ) -> bool:
        """Add a reaction to a message."""

        try:
            self.web_client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction,
            )
            return True
        except Exception as e:
            print(f"Error adding reaction: {e}")
            return False

    async def get_channel_messages(
        self,
        channel: str,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent messages from a channel."""

        try:
            response = self.web_client.conversations_history(
                channel=channel,
                limit=limit,
            )
            return response["messages"]

        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    async def get_thread_replies(
        self,
        channel: str,
        thread_ts: str,
    ) -> list[dict]:
        """Get replies in a thread."""

        try:
            response = self.web_client.conversations_replies(
                channel=channel,
                ts=thread_ts,
            )
            return response["messages"]

        except Exception as e:
            print(f"Error getting thread replies: {e}")
            return []

    def start_socket_mode(self, app: "SlackApp"):
        """Start Socket Mode for interactive features."""

        try:
            from slack_sdk.socket_mode import SocketModeClient

            self.socket_client = SocketModeClient(
                app_token=os.getenv("SLACK_APP_TOKEN"),
                web_client=self.web_client,
            )

            # Set up event handlers
            self.socket_client.socket_mode_request_listeners.append(
                app.socket_event_handler
            )

            self.socket_client.connect()

        except Exception as e:
            print(f"Error starting Socket Mode: {e}")


# =============================================================================
# Slack-Based Proposal Approval
# =============================================================================

class SlackApprovalApplier:
    """
    Proposal applier that requires Slack approval before applying changes.

    Workflow:
    1. AutoFlow generates a proposal
    2. Post proposal to Slack with approval buttons
    3. Wait for human to approve/reject
    4. Apply only if approved
    """

    def __init__(
        self,
        slack_client: SlackClient,
        channel: str,
        timeout_seconds: int = 3600,  # 1 hour
        on_apply: Optional[Callable] = None,
        on_reject: Optional[Callable] = None,
    ):
        self.slack_client = slack_client
        self.channel = channel
        self.timeout = timeout_seconds
        self.on_apply = on_apply
        self.on_reject = on_reject
        self._pending_proposals: dict[str, SlackProposal] = {}

    async def propose(self, proposal: dict) -> SlackProposal:
        """Send proposal to Slack for approval."""

        from uuid import uuid4

        # Create Slack proposal
        slack_proposal = SlackProposal(
            proposal_id=proposal.get("proposal_id", str(uuid4())),
            title=proposal.get("title", "Untitled Proposal"),
            description=proposal.get("description", ""),
            risk_level=proposal.get("risk", "UNKNOWN"),
            target_paths=proposal.get("target_paths", ()),
        )

        # Create message with approval buttons
        blocks = self._create_proposal_blocks(proposal)

        # Post to Slack
        response = await self.slack_client.post_message(
            channel=self.channel,
            blocks=blocks,
        )

        slack_proposal.message_ts = response["ts"]
        slack_proposal.channel = response["channel"]

        # Store for later approval
        self._pending_proposals[slack_proposal.proposal_id] = slack_proposal

        return slack_proposal

    def _create_proposal_blocks(self, proposal: dict) -> list[dict]:
        """Create Slack message blocks for proposal."""

        from autoflow.types import RiskLevel

        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴",
        }.get(proposal.get("risk"), "⚪")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{risk_emoji} AutoFlow Proposal",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{proposal.get('title', 'N/A')}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk:*\n{proposal.get('risk', 'N/A')}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{proposal.get('description', 'N/A')}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Target Paths:*\n```{', '.join(proposal.get('target_paths', []))}```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve",
                        },
                        "style": "primary",
                        "value": f"approve:{proposal.get('proposal_id')}",
                        "action_id": "approve_proposal",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject",
                        },
                        "style": "danger",
                        "value": f"reject:{proposal.get('proposal_id')}",
                        "action_id": "reject_proposal",
                    },
                ],
            },
        ]

        return blocks

    async def handle_approval_response(
        self,
        proposal_id: str,
        approved: bool,
        user_id: str,
    ):
        """Handle approval/rejection from Slack."""

        proposal = self._pending_proposals.get(proposal_id)
        if not proposal:
            print(f"Unknown proposal: {proposal_id}")
            return

        if approved:
            proposal.status = ApprovalStatus.APPROVED
            proposal.approved_by = user_id

            # Post confirmation
            await self.slack_client.post_message(
                channel=proposal.channel,
                text=f"✅ Proposal *{proposal.title}* approved by <@{user_id}>",
                thread_ts=proposal.message_ts,
            )

            # Apply the proposal
            if self.on_apply:
                await self.on_apply(proposal)

        else:
            proposal.status = ApprovalStatus.REJECTED

            # Post confirmation
            await self.slack_client.post_message(
                channel=proposal.channel,
                text=f"❌ Proposal *{proposal.title}* rejected by <@{user_id}>",
                thread_ts=proposal.message_ts,
            )

            if self.on_reject:
                await self.on_reject(proposal)

        # Remove from pending
        del self._pending_proposals[proposal_id]


# =============================================================================
# Slack Context Source
# =============================================================================

class SlackContextSource:
    """
    Pull context from Slack messages and conversations.

    Use cases:
    - Get historical discussions about issues
    - Retrieve team decisions and rationale
    - Find similar past incidents from channels
    """

    def __init__(
        self,
        slack_client: SlackClient,
        channels: list[str],
        lookback_days: int = 30,
    ):
        self.slack_client = slack_client
        self.channels = channels
        self.lookback_days = lookback_days

    async def search_context(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search Slack for relevant context."""

        all_messages = []

        for channel in self.channels:
            try:
                # Get recent messages from channel
                messages = await self.slack_client.get_channel_messages(
                    channel=channel,
                    limit=100,
                )

                # Filter by query
                for msg in messages:
                    if "text" in msg and query.lower() in msg["text"].lower():
                        all_messages.append({
                            "channel": channel,
                            "text": msg["text"],
                            "timestamp": msg.get("ts"),
                            "user": msg.get("user"),
                            "reactions": msg.get("reactions", []),
                        })

            except Exception as e:
                print(f"Error searching channel {channel}: {e}")

        # Sort by relevance (number of reactions)
        all_messages.sort(
            key=lambda m: len(m.get("reactions", [])),
            reverse=True,
        )

        return all_messages[:limit]

    async def get_thread_context(
        self,
        channel: str,
        thread_ts: str,
    ) -> list[dict]:
        """Get full context from a thread."""

        messages = await self.slack_client.get_thread_replies(
            channel=channel,
            thread_ts=thread_ts,
        )

        return [
            {
                "text": msg.get("text", ""),
                "user": msg.get("user"),
                "timestamp": msg.get("ts"),
            }
            for msg in messages
        ]


# =============================================================================
# Slack Notification for AutoFlow Events
# =============================================================================

class SlackNotificationSink:
    """
    Send AutoFlow events as Slack notifications.

    Features:
    - Real-time event notifications
    - Formatted messages with color coding
    - Thread grouping for related events
    """

    def __init__(
        self,
        slack_client: SlackClient,
        channel: str,
        min_level: str = "INFO",  # INFO, WARNING, ERROR
    ):
        self.slack_client = slack_client
        self.channel = channel
        self.min_level = min_level
        self._threads: dict[str, str] = {}  # workflow_id -> thread_ts

    async def write(self, events: list) -> None:
        """Write events to Slack."""

        from autoflow.observe.events import ObservationEvent

        for event in events:
            # Convert to ObservationEvent if needed
            if isinstance(event, dict):
                event = ObservationEvent(**event)

            # Check level
            if not self._should_notify(event):
                continue

            # Post notification
            await self._post_event(event)

    def _should_notify(self, event) -> bool:
        """Check if event should be notified."""

        name = event.name or ""
        source = event.source or ""

        # Always notify on errors
        if "error" in name.lower() or "fail" in name.lower():
            return True

        # Notify on warnings
        if "warn" in name.lower():
            return True

        # Check level
        if self.min_level == "ERROR":
            return "error" in name.lower()
        elif self.min_level == "WARNING":
            return "error" in name.lower() or "warn" in name.lower()

        return True

    async def _post_event(self, event) -> None:
        """Post event notification to Slack."""

        from autoflow.types import StepStatus

        # Determine emoji and color based on event
        emoji = "ℹ️"
        if "error" in event.name.lower():
            emoji = "❌"
        elif "fail" in event.name.lower():
            emoji = "❌"
        elif "warn" in event.name.lower():
            emoji = "⚠️"
        elif event.attributes.get("status") == StepStatus.COMPLETED:
            emoji = "✅"

        # Get or create thread for workflow
        workflow_id = event.attributes.get("workflow_id", "")
        thread_ts = self._threads.get(workflow_id)

        # Build message
        text = f"{emoji} *{event.name}*"
        if event.source:
            text += f" from `{event.source}`"

        # Add attributes
        if event.attributes:
            attrs_text = "\n".join(
                f"• *{k}*: `{v}`"
                for k, v in event.attributes.items()
                if k != "workflow_id" and isinstance(v, (str, int, float, bool))
            )
            if attrs_text:
                text += f"\n\n{attrs_text}"

        # Post to Slack
        response = await self.slack_client.post_message(
            channel=self.channel,
            text=text,
            thread_ts=thread_ts,
        )

        # Store thread for workflow
        if workflow_id and not thread_ts:
            self._threads[workflow_id] = response["ts"]


# =============================================================================
# Slack Interactive App
# =============================================================================

class SlackApp:
    """Slack app for handling AutoFlow interactions."""

    def __init__(self, slack_client: SlackClient):
        self.slack_client = slack_client
        self.approval_applier: Optional[SlackApprovalApplier] = None

    def set_approval_applier(self, applier: SlackApprovalApplier):
        """Set the approval applier for button handling."""
        self.approval_applier = applier

    async def socket_event_handler(self, event: dict):
        """Handle Socket Mode events."""

        type_ = event.get("type", "")
        payload = event.get("payload", {})

        if type_ == "interactive":
            await self._handle_interaction(payload)

    async def _handle_interaction(self, payload: dict):
        """Handle button clicks."""

        action_id = payload.get("action_id", "")
        value = payload.get("value", "")
        user = payload.get("user", {})

        if action_id == "approve_proposal":
            proposal_id = value.split(":", 1)[1]
            await self.approval_applier.handle_approval_response(
                proposal_id=proposal_id,
                approved=True,
                user_id=user.get("id", ""),
            )

        elif action_id == "reject_proposal":
            proposal_id = value.split(":", 1)[1]
            await self.approval_applier.handle_approval_response(
                proposal_id=proposal_id,
                approved=False,
                user_id=user.get("id", ""),
            )


# =============================================================================
# Example Usage
# =============================================================================

async def example_slack_approval_workflow():
    """Example of Slack-based approval workflow."""

    print("=" * 70)
    print("AutoFlow Slack Approval Workflow Example")
    print("=" * 70)
    print()

    # Check for required env vars
    if not os.getenv("SLACK_BOT_TOKEN"):
        print("⚠️  SLACK_BOT_TOKEN not set")
        print("   To run this example:")
        print("   1. Create a Slack app (see file header)")
        print("   2. Set environment variables:")
        print("      export SLACK_BOT_TOKEN=xoxb-your-token")
        print("      export SLACK_CHANNEL=#your-channel")
        return

    # Initialize Slack client
    print("1. Initializing Slack client...")
    slack_client = SlackClient(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        default_channel=os.getenv("SLACK_CHANNEL", "#autoflow-test"),
    )
    print("   ✓ Slack client initialized")

    # Create approval applier
    approval_applier = SlackApprovalApplier(
        slack_client=slack_client,
        channel=os.getenv("SLACK_CHANNEL", "#autoflow-test"),
        timeout_seconds=3600,
        on_apply=lambda p: print(f"   → Applying proposal: {p.title}"),
        on_reject=lambda p: print(f"   → Rejecting proposal: {p.title}"),
    )
    print("   ✓ Approval applier created")

    # Create sample proposal
    print("\n2. Creating sample proposal...")
    sample_proposal = {
        "proposal_id": "prop_001",
        "title": "Increase database connection pool",
        "description": (
            "Based on historical analysis, the database connection pool "
            "is frequently exhausted during peak hours. Increasing the pool "
            "size from 10 to 20 connections should reduce timeouts."
        ),
        "risk": "LOW",
        "target_paths": ("config/database.yaml",),
    }
    print(f"   Proposal: {sample_proposal['title']}")

    # Send to Slack for approval
    print("\n3. Sending proposal to Slack for approval...")
    slack_proposal = await approval_applier.propose(sample_proposal)
    print(f"   ✓ Proposal posted to Slack")
    print(f"   Channel: {slack_proposal.channel}")
    print(f"   Timestamp: {slack_proposal.message_ts}")
    print(f"\n   → Check Slack to approve or reject")
    print(f"   → Proposal will timeout in {approval_applier.timeout} seconds")


async def example_slack_context_search():
    """Example of searching Slack for context."""

    if not os.getenv("SLACK_BOT_TOKEN"):
        return

    print("\n" + "=" * 70)
    print("Slack Context Search Example")
    print("=" * 70)
    print()

    slack_client = SlackClient()

    context_source = SlackContextSource(
        slack_client=slack_client,
        channels=["#general", "#engineering"],
        lookback_days=30,
    )

    print("Searching Slack for context about 'database timeout'...")
    context = await context_source.search_context(
        query="database timeout",
        limit=5,
    )

    print(f"\nFound {len(context)} relevant messages:")
    for i, msg in enumerate(context, 1):
        print(f"\n[{i}] {msg['channel']}")
        print(f"    {msg['text'][:100]}...")
        print(f"    Reactions: {len(msg.get('reactions', []))}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run Slack integration examples."""

    await example_slack_approval_workflow()
    await example_slack_context_search()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nTo use Slack integration in production:")
    print("  1. Create a Slack app at https://api.slack.com/apps")
    print("  2. Configure OAuth scopes:")
    print("     - chat:write")
    print("     - channels:read")
    print("     - channels:history")
    print("     - reactions:write")
    print("  3. Install app to workspace")
    print("  4. Set environment variables:")
    print("     export SLACK_BOT_TOKEN=xoxb-your-token")
    print("     export SLACK_CHANNEL=#your-channel")
    print("  5. For interactive buttons:")
    print("     - Enable Socket Mode")
    print("     - export SLACK_APP_TOKEN=xapp-your-token")


if __name__ == "__main__":
    asyncio.run(main())
