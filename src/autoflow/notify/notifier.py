"""
Notification channels for AutoFlow proposals.

Supports multiple notification methods:
- Console output
- File-based logging
- Webhook callbacks
- LLM-as-Judge evaluation
- Future: Email, Slack, Discord, etc.
"""

import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from autoflow.types import ChangeProposal, EvaluationResult


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def notify_proposals(
        self,
        proposals: List[ChangeProposal],
        context: Dict[str, Any],
    ) -> None:
        """Send notification about new proposals."""
        ...

    @abstractmethod
    async def notify_evaluation(
        self,
        proposal: ChangeProposal,
        result: EvaluationResult,
    ) -> None:
        """Send notification about evaluation result."""
        ...


class ProposalStatus(str, Enum):
    """Status of a proposal in human-in-the-loop workflow."""
    PENDING = "pending"           # Awaiting human review
    APPROVED = "approved"         # Approved by human or auto-approved
    REJECTED = "rejected"         # Rejected by human or evaluator
    APPLIED = "applied"           # Successfully applied
    FAILED = "failed"            # Application failed


@dataclass
class ProposalNotification:
    """Rich notification about proposals with full context."""
    proposal: ChangeProposal
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluated_at: Optional[datetime] = None
    evaluator: Optional[str] = None  # "human", "llm_judge", etc.
    evaluation_result: Optional[EvaluationResult] = None
    human_feedback: Optional[str] = None

    # Context that led to this proposal
    triggering_events: List[Dict[str, Any]] = field(default_factory=list)
    graph_context: Dict[str, Any] = field(default_factory=dict)

    # Human-readable summary
    summary: str = field(default="")
    risk_explanation: str = field(default="")
    implementation_plan: str = field(default="")


# =============================================================================
# Notification Channels
# =============================================================================

class ConsoleNotificationChannel(NotificationChannel):
    """Print proposals to console with formatting."""

    def __init__(
        self,
        verbose: bool = True,
        show_context: bool = True,
        color_output: bool = True,
        include_visualizations: bool = False,
    ):
        self.verbose = verbose
        self.show_context = show_context
        self.color_output = color_output
        self.include_visualizations = include_visualizations

    async def notify_proposals(
        self,
        proposals: List[ChangeProposal],
        context: Dict[str, Any],
    ) -> None:
        """Print proposals to console."""
        if not proposals:
            if self.verbose:
                self._print("ℹ️  No proposals generated", color="blue")
            return

        self._print(f"\n{'='*70}", color="white")
        self._print(f"📋 {len(proposals)} New Proposal(s) Generated", color="cyan")
        self._print(f"{'='*70}\n", color="white")

        for i, proposal in enumerate(proposals, 1):
            self._print_proposal(proposal, i)
            if self.show_context and context:
                self._print_context(context, proposal)

            # Add visualization if enabled and graph data is available
            if self.include_visualizations:
                self._print_visualization(context, proposal)

    async def notify_evaluation(
        self,
        proposal: ChangeProposal,
        result: EvaluationResult,
    ) -> None:
        """Print evaluation result."""
        status_emoji = "✅" if result.passed else "❌"
        self._print(f"\n{status_emoji} Evaluation: {proposal.title}")
        self._print(f"   Passed: {result.passed}")
        self._print(f"   Score: {result.score:.2f}")
        if result.notes:
            self._print(f"   Notes: {result.notes}")
        if result.metrics:
            self._print(f"   Metrics: {json.dumps(result.metrics, indent=2)}")

    def _print_proposal(self, proposal: ChangeProposal, index: int) -> None:
        """Print a single proposal with formatting."""
        self._print(f"\n[{index}] {proposal.title}", color="yellow")
        self._print(f"    ID: {proposal.proposal_id}")
        self._print(f"    Kind: {proposal.kind}")
        self._print(f"    Risk: {proposal.risk}", color="red" if proposal.risk == "high" else "green")
        if proposal.target_paths:
            self._print(f"    Paths: {', '.join(proposal.target_paths)}")
        self._print(f"    Description: {proposal.description}")
        if proposal.payload:
            self._print(f"    Payload: {json.dumps(dict(proposal.payload), indent=6)}")

    def _print_context(self, context: Dict[str, Any], proposal: ChangeProposal) -> None:
        """Print relevant context for the proposal."""
        self._print("\n    📊 Context:", color="blue")

        if "triggering_events" in context:
            events = context["triggering_events"][-5:]  # Last 5 events
            self._print(f"    Recent events ({len(events)}):")
            for event in events:
                self._print(f"      - {event.get('name')} from {event.get('source')}")

        if "related_nodes" in context:
            nodes = context["related_nodes"][:3]
            self._print(f"    Related graph nodes: {len(nodes)}")
            for node in nodes:
                self._print(f"      - {node.get('node_type')}: {node.get('node_id')}")

    def _print_visualization(self, context: Dict[str, Any], proposal: ChangeProposal) -> None:
        """Print graph visualization if available."""
        try:
            # Check if graph nodes/edges are in context
            nodes = context.get("graph_nodes")
            edges = context.get("graph_edges")

            if not nodes or not edges:
                return

            # Import visualization module
            from autoflow.viz.mermaid import visualize_context_graph

            # Generate visualization
            viz = visualize_context_graph(
                nodes=nodes,
                edges=edges,
                format="mermaid",
                max_nodes=50,  # Limit for readability
            )

            # Print visualization header
            self._print("\n    📈 Graph Visualization:", color="blue")
            self._print("    " + "-" * 66)

            # Print mermaid diagram
            mermaid_lines = viz.to_markdown().split("\n")
            for line in mermaid_lines[1:-1]:  # Skip ```mermaid and ``` markers
                self._print("    " + line)

            # Print legend
            self._print("\n    Legend:")
            self._print("      🔴 Red dashed = Issue detected")
            self._print("      🟢 Green thick = Proposed change")
            self._print("      🔵 Blue = File/Function/Class")
            self._print("      ⚪ Gray = Normal node")

        except Exception as e:
            # Silently fail if visualization fails
            if self.verbose:
                self._print(f"\n    ⚠️  Could not generate visualization: {e}", color="yellow")

    def _print(self, message: str, color: str = None) -> None:
        """Print with optional color."""
        if self.color_output and color:
            # Simple ANSI color codes
            colors = {
                "red": "\033[91m",
                "green": "\033[92m",
                "yellow": "\033[93m",
                "blue": "\033[94m",
                "cyan": "\033[96m",
                "white": "\033[97m",
                "reset": "\033[0m",
            }
            code = colors.get(color, "")
            reset = colors["reset"]
            print(f"{code}{message}{reset}")
        else:
            print(message)


class FileNotificationChannel(NotificationChannel):
    """Write proposals to a file (JSONL or markdown)."""

    def __init__(
        self,
        output_path: str = "autoflow_proposals.jsonl",
        format: str = "jsonl",  # jsonl or markdown
        include_visualizations: bool = True,
        visualization_dir: str = "autoflow_viz",
    ):
        self.output_path = Path(output_path)
        self.format = format
        self.include_visualizations = include_visualizations
        self.visualization_dir = Path(visualization_dir)

    async def notify_proposals(
        self,
        proposals: List[ChangeProposal],
        context: Dict[str, Any],
    ) -> None:
        """Write proposals to file."""
        if not proposals:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.format == "jsonl":
            with open(self.output_path, "a") as f:
                for proposal in proposals:
                    notification = ProposalNotification(
                        proposal=proposal,
                        triggering_events=context.get("triggering_events", []),
                        graph_context=context.get("graph_context", {}),
                    )
                    f.write(notification.model_dump_json() + "\n")
        elif self.format == "markdown":
            with open(self.output_path, "a") as f:
                for proposal in proposals:
                    f.write(f"\n# {proposal.title}\n\n")
                    f.write(f"**ID:** {proposal.proposal_id}\n")
                    f.write(f"**Kind:** {proposal.kind}\n")
                    f.write(f"**Risk:** {proposal.risk}\n")
                    f.write(f"**Description:** {proposal.description}\n\n")
                    if proposal.target_paths:
                        f.write(f"**Affected Files:**\n")
                        for path in proposal.target_paths:
                            f.write(f"  - `{path}`\n")
                        f.write("\n")

                    # Add visualization if enabled
                    if self.include_visualizations:
                        viz_content = self._generate_visualization(context, proposal)
                        if viz_content:
                            f.write(viz_content)
                            f.write("\n")

                    f.write("---\n")

    def _generate_visualization(self, context: Dict[str, Any], proposal: ChangeProposal) -> Optional[str]:
        """Generate visualization content for proposal."""
        try:
            nodes = context.get("graph_nodes")
            edges = context.get("graph_edges")

            if not nodes or not edges:
                return None

            from autoflow.viz.mermaid import visualize_context_graph

            viz = visualize_context_graph(
                nodes=nodes,
                edges=edges,
                format="mermaid",
                max_nodes=100,
            )

            # Save visualization to separate file
            self.visualization_dir.mkdir(parents=True, exist_ok=True)
            viz_filename = f"{proposal.proposal_id}.mmd"
            viz_path = self.visualization_dir / viz_filename
            viz.save(str(viz_path))

            # Return markdown reference
            return f"**Graph Visualization:** [View Mermaid Diagram](./{self.visualization_dir}/{viz_filename})\n"

        except Exception:
            return None

    async def notify_evaluation(self, proposal: ChangeProposal, result: EvaluationResult) -> None:
        """Append evaluation to file."""
        if self.format == "jsonl":
            with open(self.output_path, "a") as f:
                f.write(json.dumps({
                    "proposal_id": proposal.proposal_id,
                    "evaluation": result.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }) + "\n")


class WebhookNotificationChannel(NotificationChannel):
    """Send proposals to a webhook endpoint."""

    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 5.0,
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {}
        self.timeout = timeout

    async def notify_proposals(
        self,
        proposals: List[ChangeProposal],
        context: Dict[str, Any],
    ) -> None:
        """Send proposals to webhook."""
        import httpx

        payload = {
            "proposals": [p.model_dump() for p in proposals],
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
        except Exception as e:
            print(f"⚠️  Webhook notification failed: {e}")

    async def notify_evaluation(self, proposal: ChangeProposal, result: EvaluationResult) -> None:
        """Send evaluation to webhook."""
        import httpx

        payload = {
            "proposal_id": proposal.proposal_id,
            "evaluation": result.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                )
        except Exception as e:
            print(f"⚠️  Webhook evaluation notification failed: {e}")


class CompositeNotificationChannel(NotificationChannel):
    """Send notifications to multiple channels."""

    def __init__(self, channels: List[NotificationChannel]):
        self.channels = channels

    async def notify_proposals(
        self,
        proposals: List[ChangeProposal],
        context: Dict[str, Any],
    ) -> None:
        """Send to all channels."""
        tasks = [ch.notify_proposals(proposals, context) for ch in self.channels]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_evaluation(self, proposal: ChangeProposal, result: EvaluationResult) -> None:
        """Send evaluation to all channels."""
        tasks = [ch.notify_evaluation(proposal, result) for ch in self.channels]
        await asyncio.gather(*tasks, return_exceptions=True)


# =============================================================================
# Factory function
# =============================================================================

def create_notifier(
    channels: str | List[str] = "console",
    **kwargs,
) -> NotificationChannel:
    """
    Create a notification channel from simple specification.

    Args:
        channels: Channel name(s) - "console", "file", "webhook", or list
        **kwargs: Additional config for channels

    Returns:
        NotificationChannel instance

    Examples:
        # Console only
        notifier = create_notifier("console")

        # Console + file
        notifier = create_notifier(["console", "file"], output_path="proposals.jsonl")

        # Webhook
        notifier = create_notifier("webhook", webhook_url="https://...")
    """
    if isinstance(channels, str):
        channels = [channels]

    channel_instances = []

    for ch in channels:
        if ch == "console":
            channel_instances.append(ConsoleNotificationChannel(
                verbose=kwargs.get("verbose", True),
                show_context=kwargs.get("show_context", True),
                color_output=kwargs.get("color_output", True),
                include_visualizations=kwargs.get("include_visualizations", False),
            ))
        elif ch == "file":
            channel_instances.append(FileNotificationChannel(
                output_path=kwargs.get("output_path", "autoflow_proposals.jsonl"),
                format=kwargs.get("format", "jsonl"),
                include_visualizations=kwargs.get("include_visualizations", True),
                visualization_dir=kwargs.get("visualization_dir", "autoflow_viz"),
            ))
        elif ch == "webhook":
            channel_instances.append(WebhookNotificationChannel(
                webhook_url=kwargs.get("webhook_url"),
                headers=kwargs.get("headers"),
                timeout=kwargs.get("timeout", 5.0),
            ))
        else:
            raise ValueError(f"Unknown channel: {ch}")

    if len(channel_instances) == 1:
        return channel_instances[0]
    else:
        return CompositeNotificationChannel(channel_instances)


__all__ = [
    # Classes
    "NotificationChannel",
    "ConsoleNotificationChannel",
    "FileNotificationChannel",
    "WebhookNotificationChannel",
    "CompositeNotificationChannel",
    # Data
    "ProposalStatus",
    "ProposalNotification",
    # Factory
    "create_notifier",
]
