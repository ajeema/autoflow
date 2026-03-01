"""
Graph visualization for AutoFlow.

Generates visual representations of:
- Context graphs with nodes and edges
- Issues and problems highlighted
- Proposed optimizations and changes
- Before/after comparisons

Supports multiple output formats:
- Mermaid diagrams (for Markdown/documentation)
- Graphviz DOT (for images)
- HTML with interactive elements
"""

import re
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from autoflow.types_pyantic import GraphNode, GraphEdge, ContextGraphDelta
from autoflow.types import ChangeProposal


@dataclass
class VisualizationConfig:
    """Configuration for graph visualization."""

    # Output format
    format: str = "mermaid"  # mermaid, dot, html

    # Styling
    show_labels: bool = True
    show_edge_labels: bool = True
    group_by_type: bool = True
    layout_direction: str = "TB"  # TB (top-bottom), LR (left-right), TD, RL

    # Highlighting
    highlight_issues: bool = True
    highlight_proposals: bool = True
    color_scheme: str = "default"  # default, muted, vibrant

    # Content filters
    max_nodes: Optional[int] = None  # Limit nodes for large graphs
    node_types: Optional[Set[str]] = None  # Only show specific node types
    exclude_patterns: List[str] = field(default_factory=list)  # Regex patterns to exclude


@dataclass
class GraphVisualization:
    """A generated visualization."""

    format: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        if self.format == "mermaid":
            return f"```mermaid\n{self.content}\n```"
        elif self.format == "dot":
            return f"```dot\n{self.content}\n```"
        else:
            return self.content

    def save(self, path: str) -> None:
        """Save visualization to file."""
        with open(path, "w") as f:
            f.write(self.content)


class MermaidGenerator:
    """Generate Mermaid diagrams from graphs."""

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        proposals: Optional[List[ChangeProposal]] = None,
        issue_node_ids: Optional[Set[str]] = None,
    ) -> GraphVisualization:
        """
        Generate a Mermaid diagram visualization.

        Args:
            nodes: Graph nodes
            edges: Graph edges
            proposals: Proposed changes (for highlighting)
            issue_node_ids: Node IDs with issues (for highlighting)

        Returns:
            GraphVisualization with Mermaid content
        """
        # Filter nodes if needed
        filtered_nodes, filtered_edges = self._filter_graph(nodes, edges)

        # Generate node definitions
        node_defs = self._generate_node_definitions(filtered_nodes, issue_node_ids, proposals)

        # Generate edge definitions
        edge_defs = self._generate_edge_definitions(filtered_edges, filtered_nodes)

        # Generate subgraphs for grouping
        subgraphs = self._generate_subgraphs(filtered_nodes) if self.config.group_by_type else []

        # Combine all parts
        mermaid_content = self._assemble_diagram(node_defs, edge_defs, subgraphs)

        return GraphVisualization(
            format="mermaid",
            content=mermaid_content,
            metadata={
                "node_count": len(filtered_nodes),
                "edge_count": len(filtered_edges),
                "grouped": self.config.group_by_type,
            }
        )

    def _filter_graph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Filter nodes and edges based on configuration."""
        filtered_nodes = nodes

        # Filter by node type
        if self.config.node_types:
            filtered_nodes = [n for n in filtered_nodes if n.node_type in self.config.node_types]

        # Filter by exclude patterns
        if self.config.exclude_patterns:
            patterns = [re.compile(p) for p in self.config.exclude_patterns]
            filtered_nodes = [
                n for n in filtered_nodes
                if not any(p.search(n.node_id) for p in patterns)
            ]

        # Limit node count
        if self.config.max_nodes and len(filtered_nodes) > self.config.max_nodes:
            filtered_nodes = filtered_nodes[:self.config.max_nodes]

        # Get valid node IDs
        valid_node_ids = {n.node_id for n in filtered_nodes}

        # Filter edges to only include connections between valid nodes
        filtered_edges = [
            e for e in edges
            if e.from_node_id in valid_node_ids and e.to_node_id in valid_node_ids
        ]

        return filtered_nodes, filtered_edges

    def _generate_node_definitions(
        self,
        nodes: List[GraphNode],
        issue_node_ids: Optional[Set[str]],
        proposals: Optional[List[ChangeProposal]],
    ) -> List[str]:
        """Generate Mermaid node definitions with styling."""
        # Collect affected nodes from proposals
        proposal_nodes = set()
        if proposals and self.config.highlight_proposals:
            for proposal in proposals:
                if proposal.target_paths:
                    for path in proposal.target_paths:
                        proposal_nodes.add(path)

        definitions = []

        for node in nodes:
            # Determine node shape and style
            shape, style = self._get_node_style(node, issue_node_ids, proposal_nodes)

            # Create node ID (Mermaid requires valid IDs)
            safe_id = self._safe_id(node.node_id)

            # Generate node definition
            if self.config.show_labels and node.properties.get("name"):
                label = node.properties.get("name", node.node_id)
                # Truncate long labels
                if len(label) > 30:
                    label = label[:27] + "..."
                definition = f"{safe_id}{shape}[\"{label}\"]"
            else:
                definition = f"{safe_id}{shape}[\"{node.node_type}\"]"

            # Add style if needed
            if style:
                definition = f"{definition}:::{style}"

            definitions.append(definition)

        return definitions

    def _get_node_style(
        self,
        node: GraphNode,
        issue_node_ids: Optional[Set[str]],
        proposal_nodes: Set[str],
    ) -> Tuple[str, str]:
        """Get node shape and CSS class based on state."""
        # Default
        shape = ""
        style = ""

        # Check for issues
        if self.config.highlight_issues and issue_node_ids and node.node_id in issue_node_ids:
            style = "issueNode"

        # Check for proposals
        elif self.config.highlight_proposals and node.node_id in proposal_nodes:
            style = "proposalNode"

        # Style by node type
        elif node.node_type == "file":
            style = "fileNode"
        elif node.node_type == "function":
            style = "functionNode"
        elif node.node_type == "class":
            style = "classNode"
        elif node.node_type == "decision":
            style = "decisionNode"
        else:
            style = "defaultNode"

        # Use special shapes for certain types
        if node.node_type == "decision":
            shape = "{"
        elif node.node_type == "context":
            shape = "["

        return shape, style

    def _generate_edge_definitions(
        self,
        edges: List[GraphEdge],
        nodes: List[GraphNode],
    ) -> List[str]:
        """Generate Mermaid edge definitions."""
        definitions = []

        for edge in edges:
            from_id = self._safe_id(edge.from_node_id)
            to_id = self._safe_id(edge.to_node_id)

            # Determine edge style based on type
            arrow_style = self._get_arrow_style(edge.edge_type)

            # Add label if enabled
            if self.config.show_edge_labels:
                label = edge.edge_type.replace("_", " ").title()
                definition = f"{from_id} {arrow_style}|{label}| {to_id}"
            else:
                definition = f"{from_id} {arrow_style} {to_id}"

            definitions.append(definition)

        return definitions

    def _get_arrow_style(self, edge_type: str) -> str:
        """Get Mermaid arrow style for edge type."""
        styles = {
            "calls": "-->",
            "imports": "-.->",
            "defines": "==>",
            "uses": "-->",
            "related_to": "-...-",
            "context_for": "----",
        }
        return styles.get(edge_type, "-->")

    def _generate_subgraphs(self, nodes: List[GraphNode]) -> List[str]:
        """Generate subgraph groupings by node type."""
        subgraphs = []

        # Group nodes by type
        nodes_by_type = defaultdict(list)
        for node in nodes:
            nodes_by_type[node.node_type].append(node)

        # Generate subgraph for each type
        for node_type, type_nodes in sorted(nodes_by_type.items()):
            if len(type_nodes) > 1:  # Only group if multiple nodes
                node_ids = " ".join([self._safe_id(n.node_id) for n in type_nodes])
                subgraph = f"    subgraph {node_type.title()}\n        {node_ids}\n    end"
                subgraphs.append(subgraph)

        return subgraphs

    def _assemble_diagram(
        self,
        node_defs: List[str],
        edge_defs: List[str],
        subgraphs: List[str],
    ) -> str:
        """Assemble the complete Mermaid diagram."""
        lines = []

        # Header
        lines.append(f"graph {self.config.layout_direction}")

        # Styles (CSS classes)
        lines.append("")
        lines.extend(self._get_styles())

        # Subgraphs (if grouping)
        if subgraphs:
            lines.append("")
            lines.extend(subgraphs)

        # Node definitions
        if node_defs:
            lines.append("")
            # Only add nodes if not using subgraphs
            if not subgraphs:
                lines.extend([f"    {node_def}" for node_def in node_defs])

        # Edge definitions
        if edge_defs:
            lines.append("")
            lines.extend([f"    {edge_def}" for edge_def in edge_defs])

        # Legend
        if self.config.highlight_issues or self.config.highlight_proposals:
            lines.append("")
            lines.extend(self._get_legend())

        return "\n".join(lines)

    def _get_styles(self) -> List[str]:
        """Get CSS style definitions for Mermaid."""
        styles = []

        if self.config.color_scheme == "default":
            styles.extend([
                "    classDef defaultNode fill:#e1e5e9,stroke:#363636,stroke-width:1px;",
                "    classDef fileNode fill:#ebf3ff,stroke:#2196f3,stroke-width:2px;",
                "    classDef functionNode fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;",
                "    classDef classNode fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px;",
                "    classDef decisionNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px;",
                "    classDef issueNode fill:#ffebee,stroke:#f44336,stroke-width:3px,stroke-dasharray: 5 5;",
                "    classDef proposalNode fill:#e0f2f1,stroke:#009688,stroke-width:3px;",
            ])
        elif self.config.color_scheme == "muted":
            styles.extend([
                "    classDef defaultNode fill:#f5f5f5,stroke:#666,stroke-width:1px;",
                "    classDef fileNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;",
                "    classDef functionNode fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;",
                "    classDef classNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;",
                "    classDef decisionNode fill:#fff8e1,stroke:#f57c00,stroke-width:2px;",
                "    classDef issueNode fill:#ffebee,stroke:#d32f2f,stroke-width:3px,stroke-dasharray: 5 5;",
                "    classDef proposalNode fill:#e0f2f1,stroke:#00796b,stroke-width:3px;",
            ])
        else:  # vibrant
            styles.extend([
                "    classDef defaultNode fill:#ffecd2,stroke:#fc6a03,stroke-width:1px;",
                "    classDef fileNode fill:#a8edea,stroke:#2980b9,stroke-width:2px;",
                "    classDef functionNode fill:#d299c2,stroke:#8e44ad,stroke-width:2px;",
                "    classDef classNode fill:#fef9d7,stroke:#f39c12,stroke-width:2px;",
                "    classDef decisionNode fill:#89f7fe,stroke:#27ae60,stroke-width:2px;",
                "    classDef issueNode fill:#ff6b6b,stroke:#c0392b,stroke-width:3px,stroke-dasharray: 5 5;",
                "    classDef proposalNode fill:#51cf66,stroke:#27ae60,stroke-width:3px;",
            ])

        return styles

    def _get_legend(self) -> List[str]:
        """Get legend for the diagram."""
        legend = []

        legend.append("    %% Legend")
        legend.append("    subgraph Legend")
        legend.append("        direction TB")
        legend.append("        L1[Normal Node]")
        legend.append("        L2[File/Function/Class]")
        legend.append("        L3[Issue Detected]")
        legend.append("        L4[Proposed Change]")
        legend.append("        L1:::defaultNode")
        legend.append("        L2:::fileNode")
        legend.append("        L3:::issueNode")
        legend.append("        L4:::proposalNode")
        legend.append("    end")

        return legend

    def _safe_id(self, node_id: str) -> str:
        """Convert node ID to safe Mermaid ID."""
        # Replace special characters with underscores
        safe = re.sub(r'[^a-zA-Z0-9]', '_', node_id)
        # Ensure it starts with a letter
        if safe and safe[0].isdigit():
            safe = "N_" + safe
        return safe


class GraphVisualizer:
    """Main interface for graph visualization."""

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.mermaid_generator = MermaidGenerator(config)

    def visualize_graph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        proposals: Optional[List[ChangeProposal]] = None,
        issue_node_ids: Optional[Set[str]] = None,
    ) -> GraphVisualization:
        """Visualize a graph with optional highlights."""
        if self.config.format == "mermaid":
            return self.mermaid_generator.generate(nodes, edges, proposals, issue_node_ids)
        else:
            raise ValueError(f"Unsupported format: {self.config.format}")

    def visualize_proposals(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        proposals: List[ChangeProposal],
    ) -> Dict[str, GraphVisualization]:
        """
        Generate before/after visualizations for proposals.

        Returns:
            Dict with 'before', 'after', and 'diff' visualizations
        """
        # Before: current state
        before = self.visualize_graph(nodes, edges, proposals=None, issue_node_ids=None)

        # After: with proposals applied (highlight affected nodes)
        affected_nodes = self._get_affected_nodes(proposals)
        after = self.visualize_graph(nodes, edges, proposals, issue_node_ids=affected_nodes)

        # Diff: show only affected nodes
        diff_nodes = [n for n in nodes if n.node_id in affected_nodes]
        diff_edges = [
            e for e in edges
            if e.from_node_id in affected_nodes or e.to_node_id in affected_nodes
        ]
        diff = self.visualize_graph(diff_nodes, diff_edges, proposals, affected_nodes)

        return {
            "before": before,
            "after": after,
            "diff": diff,
        }

    def _get_affected_nodes(self, proposals: List[ChangeProposal]) -> Set[str]:
        """Get set of node IDs affected by proposals."""
        affected = set()
        for proposal in proposals:
            if proposal.target_paths:
                affected.update(proposal.target_paths)
        return affected


def visualize_context_graph(
    nodes: List[GraphNode],
    edges: List[GraphEdge],
    format: str = "mermaid",
    proposals: Optional[List[ChangeProposal]] = None,
    issue_node_ids: Optional[Set[str]] = None,
    **kwargs
) -> GraphVisualization:
    """
    Convenience function to visualize a context graph.

    Args:
        nodes: Graph nodes
        edges: Graph edges
        format: Output format (mermaid, dot, html)
        proposals: Optional list of proposals to highlight
        issue_node_ids: Optional set of node IDs with issues to highlight
        **kwargs: Additional configuration options

    Returns:
        GraphVisualization instance
    """
    config = VisualizationConfig(format=format, **kwargs)
    visualizer = GraphVisualizer(config)
    return visualizer.visualize_graph(nodes, edges, proposals, issue_node_ids)


def visualize_proposals(
    nodes: List[GraphNode],
    edges: List[GraphEdge],
    proposals: List[ChangeProposal],
    format: str = "mermaid",
    **kwargs
) -> Dict[str, GraphVisualization]:
    """
    Convenience function to visualize proposals with before/after.

    Args:
        nodes: Graph nodes
        edges: Graph edges
        proposals: Proposed changes
        format: Output format
        **kwargs: Additional configuration options

    Returns:
        Dict with 'before', 'after', 'diff' visualizations
    """
    config = VisualizationConfig(format=format, **kwargs)
    visualizer = GraphVisualizer(config)
    return visualizer.visualize_proposals(nodes, edges, proposals)


__all__ = [
    "VisualizationConfig",
    "GraphVisualization",
    "MermaidGenerator",
    "GraphVisualizer",
    "visualize_context_graph",
    "visualize_proposals",
]
