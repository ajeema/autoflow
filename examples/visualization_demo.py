"""
Demo: Graph Visualization with Mermaid Diagrams

This demonstrates how AutoFlow can generate visual representations of:
- Current context graphs
- Issues and problems highlighted
- Proposed optimizations
- Before/after comparisons
"""

from autoflow.types_pyantic import GraphNode, GraphEdge, NodeType
from autoflow.viz.mermaid import (
    visualize_context_graph,
    visualize_proposals,
    VisualizationConfig,
)
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel


def create_sample_graph():
    """Create a sample context graph for demonstration."""
    nodes = [
        GraphNode(
            node_id="main.py",
            node_type="file",
            properties={"name": "main.py", "path": "src/main.py"},
        ),
        GraphNode(
            node_id="process_data",
            node_type="function",
            properties={"name": "process_data", "file": "main.py"},
        ),
        GraphNode(
            node_id="api_client",
            node_type="class",
            properties={"name": "APIClient", "file": "api.py"},
        ),
        GraphNode(
            node_id="api.py",
            node_type="file",
            properties={"name": "api.py", "path": "src/api.py"},
        ),
        GraphNode(
            node_id="fetch_data",
            node_type="function",
            properties={"name": "fetch_data", "file": "api.py"},
        ),
        GraphNode(
            node_id="database",
            node_type="decision",
            properties={"name": "Database", "type": "PostgreSQL"},
        ),
        GraphNode(
            node_id="config.json",
            node_type="file",
            properties={"name": "config.json", "path": "config.json"},
        ),
    ]

    edges = [
        GraphEdge(
            edge_type="calls",
            from_node_id="process_data",
            to_node_id="fetch_data",
        ),
        GraphEdge(
            edge_type="defines",
            from_node_id="main.py",
            to_node_id="process_data",
        ),
        GraphEdge(
            edge_type="defines",
            from_node_id="api.py",
            to_node_id="api_client",
        ),
        GraphEdge(
            edge_type="defines",
            from_node_id="api.py",
            to_node_id="fetch_data",
        ),
        GraphEdge(
            edge_type="imports",
            from_node_id="main.py",
            to_node_id="api.py",
        ),
        GraphEdge(
            edge_type="uses",
            from_node_id="fetch_data",
            to_node_id="database",
        ),
        GraphEdge(
            edge_type="related_to",
            from_node_id="process_data",
            to_node_id="config.json",
        ),
    ]

    return nodes, edges


def demo_basic_visualization():
    """Demo basic graph visualization."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Graph Visualization")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Generate visualization
    viz = visualize_context_graph(nodes, edges, format="mermaid")

    # Print as markdown
    print("\nMermaid Diagram (Markdown):")
    print(viz.to_markdown())

    # Save to file
    viz.save("/tmp/demo_graph.mmd")
    print(f"\n✅ Saved to: /tmp/demo_graph.mmd")


def demo_with_issues():
    """Demo visualization with highlighted issues."""
    print("\n" + "=" * 70)
    print("DEMO 2: Visualization with Issues Highlighted")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Identify nodes with issues
    issue_nodes = {"fetch_data", "database"}  # These have problems

    # Generate visualization with issues highlighted
    viz = visualize_context_graph(
        nodes,
        edges,
        issue_node_ids=issue_nodes,
        format="mermaid",
    )

    print("\nGraph with Issues Highlighted:")
    print(viz.to_markdown())
    print("\n🔴 Issues detected in: fetch_data, database")


def demo_with_proposals():
    """Demo visualization with proposed changes."""
    print("\n" + "=" * 70)
    print("DEMO 3: Visualization with Proposed Changes")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Create a proposal
    proposal = ChangeProposal(
        kind=ProposalKind.CONFIG_EDIT,
        title="Add retry logic to API client",
        description="The fetch_data function is failing intermittently. Adding retry logic with exponential backoff will improve reliability.",
        risk=RiskLevel.LOW,
        target_paths=["fetch_data"],
        payload={
            "op": "add_retry",
            "max_retries": 3,
            "backoff_ms": [100, 200, 400],
        },
    )

    # Generate visualization with proposal highlighted
    viz = visualize_context_graph(
        nodes,
        edges,
        proposals=[proposal],
        format="mermaid",
    )

    print("\nGraph with Proposed Change:")
    print(viz.to_markdown())
    print("\n📝 Proposal: Add retry logic to fetch_data function")
    print("🟢 Affected node highlighted in green")


def demo_before_after():
    """Demo before/after visualization."""
    print("\n" + "=" * 70)
    print("DEMO 4: Before/After Visualization")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Create multiple proposals
    proposals = [
        ChangeProposal(
            kind=ProposalKind.CONFIG_EDIT,
            title="Optimize database queries",
            description="Add connection pooling and query optimization.",
            risk=RiskLevel.LOW,
            target_paths=["database", "fetch_data"],
            payload={"pool_size": 10},
        ),
        ChangeProposal(
            kind=ProposalKind.TEXT_PATCH,
            title="Fix configuration loading",
            description="Fix bug in config.json parsing.",
            risk=RiskLevel.MEDIUM,
            target_paths=["config.json"],
            payload={"fix": "add_error_handling"},
        ),
    ]

    # Generate before/after visualizations
    visualizations = visualize_proposals(nodes, edges, proposals)

    print("\n📊 BEFORE (Current State):")
    print(visualizations["before"].to_markdown())

    print("\n📊 AFTER (With Changes Applied):")
    print(visualizations["after"].to_markdown())

    print("\n📊 DIFF (Only Affected Nodes):")
    print(visualizations["diff"].to_markdown())


def demo_custom_styling():
    """Demo with custom styling options."""
    print("\n" + "=" * 70)
    print("DEMO 5: Custom Styling")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Custom configuration
    config = VisualizationConfig(
        format="mermaid",
        layout_direction="LR",  # Left-to-right
        show_edge_labels=True,
        group_by_type=True,
        color_scheme="vibrant",  # or "muted"
        max_nodes=20,
    )

    from autoflow.viz.mermaid import GraphVisualizer
    visualizer = GraphVisualizer(config)
    viz = visualizer.visualize_graph(nodes, edges)

    print("\nCustom Styled Graph (Vibrant colors, Left-to-Right):")
    print(viz.to_markdown())


def demo_notification_integration():
    """Demo integration with notification system."""
    print("\n" + "=" * 70)
    print("DEMO 6: Integration with Notifications")
    print("=" * 70)

    from autoflow.notify.notifier import create_notifier

    # Create notifier with visualizations enabled
    notifier = create_notifier(
        "console",
        include_visualizations=True,  # Enable visualizations
        verbose=True,
    )

    # Create sample graph and proposal
    nodes, edges = create_sample_graph()
    proposal = ChangeProposal(
        kind=ProposalKind.REFACTORING,
        title="Refactor API client for better error handling",
        description="The API client needs better error handling and retry logic.",
        risk=RiskLevel.MEDIUM,
        target_paths=["api_client", "fetch_data"],
        payload={"refactor": "add_error_handling"},
    )

    # Simulate notification
    import asyncio

    async def show_notification():
        context = {
            "graph_nodes": nodes,
            "graph_edges": edges,
            "triggering_events": [
                {"source": "monitor", "name": "api_timeout"},
                {"source": "monitor", "name": "api_timeout"},
            ],
            "graph_context": {"error_rate": 0.15},
        }

        print("\n📢 Notification with Visualization:")
        print("-" * 70)

        await notifier.notify_proposals([proposal], context)

    asyncio.run(show_notification())


def demo_export_formats():
    """Demo different export formats."""
    print("\n" + "=" * 70)
    print("DEMO 7: Export Formats")
    print("=" * 70)

    nodes, edges = create_sample_graph()

    # Generate Mermaid
    mermaid_viz = visualize_context_graph(nodes, edges, format="mermaid")

    print("\n1. Mermaid Format (for GitHub, GitLab, Notion, etc.):")
    print(mermaid_viz.to_markdown()[:500] + "...")

    # Save files
    mermaid_viz.save("/tmp/autoflow_demo.mmd")
    print("\n✅ Saved Mermaid: /tmp/autoflow_demo.mmd")

    # Can be rendered using:
    # - GitHub/GitLab markdown (native support)
    # - Mermaid Live Editor: https://mermaid.live
    # - VS Code: Mermaid Preview extension
    # - CLI: npx @mermaid-js/mermaid-cli -i input.mmd -o output.png


def main():
    """Run all visualization demos."""
    demo_basic_visualization()
    demo_with_issues()
    demo_with_proposals()
    demo_before_after()
    demo_custom_styling()
    demo_notification_integration()
    demo_export_formats()

    print("\n" + "=" * 70)
    print("All visualization demos complete!")
    print("=" * 70)

    print("\n🎯 Key Features:")
    print("  1. ✅ Generate Mermaid diagrams from context graphs")
    print("  2. ✅ Highlight issues (red dashed)")
    print("  3. ✅ Highlight proposed changes (green thick)")
    print("  4. ✅ Before/after comparisons")
    print("  5. ✅ Custom styling options")
    print("  6. ✅ Integration with notifications")
    print("  7. ✅ Export to multiple formats")

    print("\n📝 How to View Mermaid Diagrams:")
    print("  - GitHub/GitLab: Paste in markdown files")
    print("  - Mermaid Live Editor: https://mermaid.live")
    print("  - VS Code: Install 'Mermaid Preview' extension")
    print("  - Render to PNG: npx @mermaid-js/mermaid-cli -i input.mmd -o output.png")

    print("\n🚀 Using in Your Code:")
    print("  from autoflow.viz.mermaid import visualize_context_graph")
    print("  viz = visualize_context_graph(nodes, edges)")
    print("  print(viz.to_markdown())")


if __name__ == "__main__":
    main()
