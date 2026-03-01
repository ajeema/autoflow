# Decision Graph API

## Overview

The Decision Graph orchestrates **rules** that analyze the context graph and generate **proposals** for system improvements.

---

## Core Components

### DecisionGraph

```python
class DecisionGraph:
    def __init__(self, rules: Sequence[object]) -> None:
        self.rules = rules

    def run(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> list[ChangeProposal]:
        """Run all rules and collect proposals."""
```

**Key Features:**
- Orchestrates multiple rules
- Each rule generates proposals independently
- Supports rules that need graph edges (for relationship analysis)
- Aggregates all proposals into a single list

---

## Creating Rules

### Basic Rule Structure

```python
from autoflow.types import ChangeProposal, GraphNode, ProposalKind, RiskLevel
from uuid import uuid4

class MyRule:
    def propose(self, nodes: list[GraphNode]) -> list[ChangeProposal]:
        """Analyze nodes and generate proposals."""
        proposals = []

        # Your analysis logic here
        for node in nodes:
            if self.should_propose(node):
                proposals.append(self.create_proposal(node))

        return proposals

    def should_propose(self, node: GraphNode) -> bool:
        """Check if this node triggers a proposal."""
        # Your logic here
        return node.properties.get("error_count", 0) > 5

    def create_proposal(self, node: GraphNode) -> ChangeProposal:
        """Create a proposal for this node."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Fix high error rate",
            description=f"Node {node.node_id} has too many errors",
            risk=RiskLevel.LOW,
            target_paths=("config/app.yaml",),
            payload={"max_retries": 3},
        )
```

### Rule With Edge Analysis

```python
class MyRule:
    def propose(self, nodes: list[GraphNode], edges: list[GraphEdge] = None):
        """Rule that analyzes relationships."""
        proposals = []

        if edges:
            # Analyze error propagation
            causality_edges = [e for e in edges if e.edge_type == "caused_by"]

            for edge in causality_edges:
                # Find nodes involved
                from_node = next(n for n in nodes if n.node_id == edge.from_node_id)
                to_node = next(n for n in nodes if n.node_id == edge.to_node_id)

                # Check if this triggers a proposal
                if self.is_cascading_failure(from_node, to_node):
                    proposals.append(self.create_resilience_proposal(from_node))

        return proposals

    def is_cascading_failure(self, from_node: GraphNode, to_node: GraphNode) -> bool:
        """Check if this is a problematic cascade."""
        # Count how many failures this step causes
        caused_count = sum(
            1 for e in edges
            if e.edge_type == "caused_by"
            and e.from_node_id == from_node.node_id
        )
        return caused_count >= 3
```

---

## Built-in Rules

### HighErrorRateRetryRule (Core)

Detects repeated exceptions and proposes retry policy changes.

```python
from autoflow.decide.rules import HighErrorRateRetryRule

rule = HighErrorRateRetryRule(
    workflow_id="my_workflow",
    threshold=3,  # Trigger after 3 exceptions
)

# When 3+ exceptions occur for the workflow:
# Proposes: Increase retry policy from 1 to 3
```

### Workflow Rules (Workflow Module)

#### FailingStepRule

```python
from autoflow.workflow.rules import FailingStepRule

rule = FailingStepRule(
    workflow_id="data_pipeline",
    failure_threshold=0.15,  # 15% failure rate
)

# Generates targeted proposals based on error type:
# - timeout → Increase timeout
# - rate_limit → Add rate limiting
# - validation_error → Improve validation
```

#### SlowStepRule

```python
from autoflow.workflow.rules import SlowStepRule

rule = SlowStepRule(
    workflow_id="data_pipeline",
    slowness_threshold_ms=5000,  # P95 latency threshold
)

# Proposes optimizations for slow steps:
# - Enable caching
# - Add batch processing
# - Enable parallelization
```

#### ErrorPropagationRule

```python
from autoflow.workflow.rules import ErrorPropagationRule

rule = ErrorPropagationRule(
    workflow_id="data_pipeline",
    cascade_threshold=3,  # 3+ downstream failures
)

# Proposes resilience improvements:
# - Add retry policy
# - Add circuit breaker
# - Add fallback mechanism
```

---

## Advanced Rule Patterns

### Pattern 1: Threshold-Based Rule

```python
class HighLatencyRule:
    """Detects high latency and proposes optimizations."""

    def __init__(self, service_name: str, threshold_ms: float = 5000):
        self.service_name = service_name
        self.threshold_ms = threshold_ms

    def propose(self, nodes):
        proposals = []

        # Filter nodes for this service
        service_nodes = [
            n for n in nodes
            if n.properties.get("service") == self.service_name
        ]

        if len(service_nodes) < 5:
            return []

        # Calculate P95 latency
        latencies = [
            n.properties.get("latency_ms", 0)
            for n in service_nodes
            if n.properties.get("latency_ms")
        ]

        if not latencies:
            return []

        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(len(latencies) * 0.95)]

        if p95_latency > self.threshold_ms:
            proposals.append(ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title=f"Reduce latency for {self.service_name}",
                description=f"P95 latency is {p95_latency:.0f}ms (threshold: {self.threshold_ms}ms)",
                risk=RiskLevel.LOW,
                target_paths=(f"config/services/{self.service_name}.yaml",),
                payload={
                    "optimization": "enable_caching",
                    "cache_ttl_seconds": 300,
                },
            ))

        return proposals
```

### Pattern 2: Comparison-Based Rule

```python
class ABOptimizationRule:
    """A/B testing rule that proposes winning variant."""

    def __init__(self, experiment_name: str, min_samples=100):
        self.experiment_name = experiment_name
        self.min_samples = min_samples

    def propose(self, nodes):
        proposals = []

        # Group by variant
        variants = {}
        for node in nodes:
            if node.properties.get("experiment") == self.experiment_name:
                variant = node.properties.get("variant", "control")
                if variant not in variants:
                    variants[variant] = []
                variants[variant].append(node)

        # Need at least 2 variants
        if len(variants) < 2:
            return []

        # Check sample sizes
        for variant, nodes in variants.items():
            if len(nodes) < self.min_samples:
                return []

        # Calculate metrics for each variant
        variant_metrics = {}
        for variant, variant_nodes in variants.items():
            successes = sum(
                1 for n in variant_nodes
                if n.properties.get("success")
            )
            variant_metrics[variant] = successes / len(variant_nodes)

        # Find winner
        best_variant = max(variant_metrics, key=variant_metrics.get)

        # If control is not best, propose switching
        if best_variant != "control":
            control_rate = variant_metrics["control"]
            best_rate = variant_metrics[best_variant]
            improvement = best_rate - control_rate

            if improvement > 0.05:  # 5% improvement
                proposals.append(ChangeProposal(
                    proposal_id=str(uuid4()),
                    kind=ProposalKind.CONFIG_EDIT,
                    title=f"Switch {self.experiment_name} to {best_variant}",
                    description=(
                        f"Variant {best_variant} has {best_rate:.1%} success rate "
                        f"vs {control_rate:.1%} for control ({improvement:+.1%} improvement)"
                    ),
                    risk=RiskLevel.LOW,
                    target_paths=(f"config/experiments/{self.experiment_name}.yaml",),
                    payload={
                        "default_variant": best_variant,
                    },
                ))

        return proposals
```

### Pattern 3: Time-Series Analysis Rule

```python
from datetime import datetime, timedelta

class TrendAnalysisRule:
    """Analyzes trends over time and proposes actions."""

    def __init__(self, metric_name: str, window_hours=24):
        self.metric_name = metric_name
        self.window_hours = window_hours

    def propose(self, nodes):
        proposals = []

        # Group by hour
        from collections import defaultdict

        hourly_values = defaultdict(list)
        cutoff = datetime.now() - timedelta(hours=self.window_hours)

        for node in nodes:
            if node.properties.get("metric") == self.metric_name:
                ts = node.properties.get("timestamp")
                if ts and ts > cutoff:
                    hour = ts.replace(minute=0, second=0, microsecond=0)
                    hourly_values[hour].append(node.properties.get("value"))

        # Analyze trend
        if len(hourly_values) < 2:
            return []

        hours = sorted(hourly_values.keys())
        values = [sum(hourly_values[h]) / len(hourly_values[h]) for h in hours]

        # Simple linear regression
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xx = sum(i*i for i in range(n))
        sum_xy = sum(i * values[i] for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)

        # If trend is bad, propose action
        if slope < -0.5:  # Declining
            proposals.append(ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title=f"Reverse declining {self.metric_name}",
                description=f"{self.metric_name} is trending down (slope: {slope:.2f}/hour)",
                risk=RiskLevel.MEDIUM,
                target_paths=(f"config/metrics/{self.metric_name}.yaml",),
                payload={
                    "alert_threshold": values[-1] * 0.9,  # Alert if drops below current * 0.9
                },
            ))

        return proposals
```

### Pattern 4: Machine Learning Enhanced Rule

```python
class MLPoweredRule:
    """Rule that uses ML to detect anomalies."""

    def __init__(self, model_path: str):
        import joblib
        self.model = joblib.load(model_path)

    def propose(self, nodes):
        proposals = []

        # Extract features
        features = self.extract_features(nodes)

        if not features:
            return []

        # Predict anomalies
        anomalies = self.model.predict(features)

        for i, is_anomaly in enumerate(anomalies):
            if is_anomaly:
                node = features[i]
                proposals.append(self.create_anomaly_proposal(node))

        return proposals

    def extract_features(self, nodes):
        """Extract ML features from nodes."""
        # Group by workflow_run_id
        from collections import defaultdict
        runs = defaultdict(list)

        for node in nodes:
            run_id = node.properties.get("workflow_run_id")
            if run_id:
                runs[run_id].append(node)

        # For each run, extract features
        features = []
        for run_id, run_nodes in runs.items():
            feature = {
                "total_latency_ms": sum(
                    n.properties.get("latency_ms", 0)
                    for n in run_nodes
                ),
                "error_count": sum(
                    1 for n in run_nodes
                    if n.properties.get("status") == "failure"
                ),
                "step_count": len(run_nodes),
            }
            features.append((run_nodes, feature))

        return features

    def create_anomaly_proposal(self, run_nodes):
        """Create proposal for anomalous run."""
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.TEXT_PATCH,
            title="Investigate anomalous workflow run",
            description=f"Workflow run {run_nodes[0].properties.get('workflow_run_id')} detected as anomalous",
            risk=RiskLevel.LOW,
            target_paths=("logs/anomalies.log",),
            payload={
                "run_id": run_nodes[0].properties.get("workflow_run_id"),
                "investigation": "required",
            },
        )
```

---

## Rule Composition

### Chained Rules

```python
class ChainedRule:
    """Combines multiple rules in sequence."""

    def __init__(self, rules: list):
        self.rules = rules

    def propose(self, nodes, edges=None):
        all_proposals = []

        for rule in self.rules:
            proposals = rule.propose(nodes, edges)
            all_proposals.extend(proposals)

        # Optionally filter or rank proposals
        return self.rank_proposals(all_proposals)

    def rank_proposals(self, proposals):
        """Rank proposals by priority."""
        # Simple example: prioritize by risk level
        risk_order = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2}

        return sorted(
            proposals,
            key=lambda p: risk_order.get(p.risk, 3),
        )
```

### Conditional Rules

```python
class ConditionalRule:
    """Applies rule only if conditions are met."""

    def __init__(self, condition, rule):
        self.condition = condition
        self.rule = rule

    def propose(self, nodes, edges=None):
        # Check condition
        if not self.condition(nodes, edges):
            return []

        # Apply rule
        return self.rule.propose(nodes, edges)


# Usage
rule = ConditionalRule(
    condition=lambda nodes: len(nodes) > 100,  # Only if enough data
    rule=HighErrorRateRetryRule(workflow_id="my_workflow", threshold=5),
)
```

---

## API Reference

### DecisionGraph

```python
class DecisionGraph:
    def __init__(self, rules: Sequence[object]) -> None:
        """Initialize with a list of rules."""

    def run(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> list[ChangeProposal]:
        """
        Run all rules and collect proposals.

        Args:
            nodes: Graph nodes to analyze
            edges: Optional graph edges for relationship analysis

        Returns:
            List of proposals from all rules
        """
```

### Base Rule Protocol

```python
from typing import Protocol

class Rule(Protocol):
    def propose(
        self,
        nodes: Sequence[GraphNode],
        edges: Optional[Sequence[GraphEdge]] = None,
    ) -> Sequence[ChangeProposal]:
        """Generate proposals from graph analysis."""
```

---

## See Also

- [Proposals API](proposals.md) - Proposal structure and types
- [Observation Events](observation_events.md) - Creating events for rules
- [Context Graph](context_graph.md) - Graph structure that rules analyze
- [Examples](examples.md) - Complete rule examples
