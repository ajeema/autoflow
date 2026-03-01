# Workflow Module API

## Overview

The **Workflow Module** provides specialized tools for analyzing and optimizing multi-step workflows. It extends the core AutoFlow functionality with:

- **Workflow-Aware Graph Builder** - Builds graphs with workflow relationships
- **Query Helpers** - High-level queries for workflow analysis
- **Metrics** - Step-level and workflow-level calculations
- **Rules** - Pre-built rules for common workflow patterns

---

## Core Components

### WorkflowAwareGraphBuilder

Enhanced graph builder that creates workflow relationships between steps.

```python
from autoflow.workflow import WorkflowAwareGraphBuilder

builder = WorkflowAwareGraphBuilder()
delta = builder.build_delta(events)

# Creates:
# - Nodes for each workflow step
# - Edges: next_step (sequential flow)
# - Edges: depends_on (parent-child)
# - Edges: caused_by (error propagation)
```

**Supported Event Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `workflow_id` | `str` | Workflow identifier |
| `workflow_run_id` | `str` | Unique run identifier |
| `step_name` | `str` | Step name (e.g., "extract", "transform") |
| `step_id` | `str` | Unique step identifier |
| `step_order` | `int` | Step order in workflow |
| `parent_step_id` | `str` | Parent step ID (for nested steps) |
| `status` | `str` | Step status (success, failure, skipped, etc.) |
| `latency_ms` | `float` | Step execution time |
| `error_type` | `str` | Error type (if failed) |

**Edge Types Created:**

| Edge Type | Description | Example |
|-----------|-------------|---------|
| `next_step` | Sequential flow between steps | extract → transform → load |
| `depends_on` | Parent-child relationships | parent step → child step |
| `caused_by` | Error propagation | failed step → downstream failure |

---

### WorkflowQueryHelpers

High-level query methods for workflow analysis.

```python
from autoflow.workflow import WorkflowQueryHelpers

q = WorkflowQueryHelpers()

# Filter nodes
pipeline_nodes = q.filter_by_workflow(nodes, "data_pipeline")
extract_nodes = q.filter_by_step(nodes, "extract")
failed_nodes = q.filter_by_status(nodes, "failure")

# Group nodes
by_step = q.group_by_step(nodes)
by_run = q.group_by_workflow_run(nodes)

# Status analysis
status_counts = q.count_by_status(nodes)

# Error analysis
propagations = q.find_error_propagation(nodes, edges)
root_causes = q.find_root_cause_failures(nodes, edges)

# Execution tracing
path = q.trace_execution_path(nodes, run_id="run_001")
```

---

## Workflow Metrics

### Step-Level Metrics

```python
from autoflow.workflow import (
    step_success_rate,
    step_failure_rate,
    step_latency_stats,
    step_error_types,
)

# Success rate
success_rate = step_success_rate(
    nodes,
    workflow_id="data_pipeline",
    step_name="extract",
)
# Returns: 0.95 (95% success)

# Failure rate
failure_rate = step_failure_rate(nodes, step_name="transform")

# Latency statistics
latency_stats = step_latency_stats(
    nodes,
    workflow_id="data_pipeline",
    step_name="load",
)
# Returns: {"min": 100, "max": 5000, "mean": 850, "p50": 700, "p95": 1200, "p99": 2000}

# Error types
error_types = step_error_types(nodes, step_name="validate")
# Returns: {"ValidationError": 15, "SchemaError": 5}
```

### Workflow-Level Metrics

```python
from autoflow.workflow import (
    workflow_throughput,
    workflow_bottlenecks,
    critical_path_analysis,
)

# Throughput (runs per hour)
throughput = workflow_throughput(nodes, workflow_id="data_pipeline")
# Returns: 45.2 (runs per hour)

# Bottlenecks (slowest steps)
bottlenecks = workflow_bottlenecks(nodes, workflow_id="data_pipeline")
# Returns: [
#   {"step_name": "transform", "avg_latency_ms": 2500},
#   {"step_name": "load", "avg_latency_ms": 1800},
# ]

# Critical path (longest execution path)
critical_path = critical_path_analysis(nodes, edges, workflow_id="data_pipeline")
# Returns: {
#   "path": ["extract", "transform", "validate", "load"],
#   "total_latency_ms": 5500,
# }
```

---

## Workflow Rules

### FailingStepRule

Detects steps with high failure rates and generates targeted proposals.

```python
from autoflow.workflow.rules import FailingStepRule

rule = FailingStepRule(
    workflow_id="data_pipeline",
    failure_threshold=0.15,  # 15% failure rate
)

proposals = rule.propose(nodes, edges)

# Example proposals:
# - "Add retry policy for validate step"
# - "Fix validation logic for transform step"
# - "Increase timeout for load step"
```

**Generated Proposals:**

| Error Type | Proposal |
|------------|----------|
| `timeout` | Increase timeout for step |
| `rate_limit` | Add rate limiting |
| `validation_error` | Improve validation logic |
| `schema_error` | Fix schema handling |
| `connection_error` | Add connection pooling |

### SlowStepRule

Identifies performance bottlenecks and proposes optimizations.

```python
from autoflow.workflow.rules import SlowStepRule

rule = SlowStepRule(
    workflow_id="data_pipeline",
    slowness_threshold_ms=5000,  # P95 latency threshold
)

proposals = rule.propose(nodes)

# Example proposals:
# - "Enable caching for transform step"
# - "Add batch processing for load step"
# - "Enable parallelization for extract step"
```

**Generated Proposals:**

| Pattern | Proposal |
|---------|----------|
| High latency | Enable caching |
| Repetitive calls | Add batching |
| Independent operations | Enable parallelization |
| External API calls | Add async processing |

### ErrorPropagationRule

Tracks cascading failures and proposes resilience improvements.

```python
from autoflow.workflow.rules import ErrorPropagationRule

rule = ErrorPropagationRule(
    workflow_id="data_pipeline",
    cascade_threshold=3,  # 3+ downstream failures
)

proposals = rule.propose(nodes, edges)

# Example proposals:
# - "Add retry policy for extract step (causes 5 downstream failures)"
# - "Add circuit breaker for transform step"
# - "Add fallback mechanism for load step"
```

**Generated Proposals:**

| Cascade Pattern | Proposal |
|-----------------|----------|
| Parent causes child failures | Add retry policy |
| Failure propagates through pipeline | Add circuit breaker |
| Step blocks downstream progress | Add fallback mechanism |

---

## Complete Workflow Usage

### Example 1: Building Workflow Graphs

```python
from autoflow.observe.events import make_event
from autoflow.workflow import WorkflowAwareGraphBuilder
from autoflow.types import StepStatus

# Create workflow events
events = [
    make_event(
        source="workflow_engine",
        name="step_execution",
        attributes={
            "workflow_id": "etl_pipeline",
            "workflow_run_id": "run_001",
            "step_name": "extract",
            "step_id": "run_001_step_1",
            "step_order": 1,
            "status": StepStatus.SUCCESS.value,
            "latency_ms": 500,
        },
    ),
    make_event(
        source="workflow_engine",
        name="step_execution",
        attributes={
            "workflow_id": "etl_pipeline",
            "workflow_run_id": "run_001",
            "step_name": "transform",
            "step_id": "run_001_step_2",
            "step_order": 2,
            "status": StepStatus.SUCCESS.value,
            "latency_ms": 1200,
        },
    ),
    make_event(
        source="workflow_engine",
        name="step_execution",
        attributes={
            "workflow_id": "etl_pipeline",
            "workflow_run_id": "run_001",
            "step_name": "load",
            "step_id": "run_001_step_3",
            "step_order": 3,
            "status": StepStatus.FAILURE.value,
            "latency_ms": 800,
            "error_type": "timeout",
        },
    ),
]

# Build graph
builder = WorkflowAwareGraphBuilder()
delta = builder.build_delta(events)

print(f"Created {len(delta.nodes)} nodes")
print(f"Created {len(delta.edges)} edges")
```

### Example 2: Querying Workflow Data

```python
from autoflow.workflow import WorkflowQueryHelpers

q = WorkflowQueryHelpers()

# Assume we have nodes from the graph
nodes = store.query_nodes("workflow_step", limit=1000)

# Filter by workflow
pipeline_nodes = q.filter_by_workflow(nodes, "etl_pipeline")
print(f"Found {len(pipeline_nodes)} steps in etl_pipeline")

# Filter by step
load_nodes = q.filter_by_step(nodes, "load")
print(f"Found {len(load_nodes)} load steps")

# Group by step
steps = q.group_by_step(nodes)
for step_name, step_nodes in steps.items():
    print(f"{step_name}: {len(step_nodes)} executions")

# Status breakdown
status_counts = q.count_by_status(pipeline_nodes)
print(f"Status breakdown: {status_counts}")
# Output: {"success": 80, "failure": 15, "skipped": 5}

# Find error propagation
propagations = q.find_error_propagation(nodes, edges)
for prop in propagations:
    print(f"{prop['from_step']} failed → caused {prop['to_step']} to fail")

# Trace execution path
path = q.trace_execution_path(nodes, run_id="run_001")
for step_info in path:
    print(f"{step_info['step_order']}. {step_info['step_name']}")
    print(f"   Status: {step_info['status']}")
    print(f"   Latency: {step_info['latency_ms']}ms")
```

### Example 3: Calculating Workflow Metrics

```python
from autoflow.workflow import (
    step_success_rate,
    step_failure_rate,
    step_latency_stats,
    workflow_bottlenecks,
    critical_path_analysis,
)

nodes = store.query_nodes("workflow_step", limit=1000)

# Step success rate
extract_success = step_success_rate(nodes, workflow_id="etl_pipeline", step_name="extract")
print(f"Extract success rate: {extract_success:.1%}")

# Step latency
load_latency = step_latency_stats(nodes, step_name="load")
print(f"Load latency P95: {load_latency['p95']}ms")

# Workflow bottlenecks
bottlenecks = workflow_bottlenecks(nodes, workflow_id="etl_pipeline")
print("Bottlenecks:")
for b in bottlenecks[:3]:
    print(f"  - {b['step_name']}: {b['avg_latency_ms']}ms avg")

# Critical path
critical_path = critical_path_analysis(nodes, edges, workflow_id="etl_pipeline")
print(f"Critical path: {' → '.join(critical_path['path'])}")
print(f"Total latency: {critical_path['total_latency_ms']}ms")
```

### Example 4: Using Workflow Rules

```python
from autoflow.workflow import WorkflowAwareGraphBuilder
from autoflow.workflow.rules import FailingStepRule, SlowStepRule, ErrorPropagationRule
from autoflow.orchestrator.engine import AutoImproveEngine

# Setup engine with workflow-aware builder
engine = AutoImproveEngine(
    store=store,
    graph_builder=WorkflowAwareGraphBuilder(),
    decision_graph=DecisionGraph(rules=[
        FailingStepRule(workflow_id="etl_pipeline", failure_threshold=0.10),
        SlowStepRule(workflow_id="etl_pipeline", slowness_threshold_ms=3000),
        ErrorPropagationRule(workflow_id="etl_pipeline", cascade_threshold=2),
    ]),
    evaluator=evaluator,
    applier=applier,
)

# Ingest workflow events
events = [
    make_event(source="workflow_engine", name="step_execution", attributes={
        "workflow_id": "etl_pipeline",
        "workflow_run_id": "run_123",
        "step_name": "extract",
        "step_id": "run_123_step_1",
        "step_order": 1,
        "status": StepStatus.SUCCESS.value,
        "latency_ms": 850,
    }),
    # ... more events
]

engine.ingest(events)

# Generate proposals (workflow-aware)
proposals = engine.propose_with_edges()

for proposal in proposals:
    print(f"Proposal: {proposal.title}")
    print(f"Description: {proposal.description}")
    print(f"Risk: {proposal.risk}")
    print()
```

---

## Custom Workflow Rules

### Pattern 1: Custom Metric Rule

```python
from autoflow.workflow.rules import WorkflowRule

class HighMemoryUsageRule(WorkflowRule):
    """Detects steps with high memory usage."""

    def __init__(self, workflow_id: str, memory_threshold_mb: float = 1000):
        super().__init__(workflow_id)
        self.memory_threshold_mb = memory_threshold_mb

    def propose(self, nodes, edges=None):
        proposals = []

        # Filter workflow nodes
        workflow_nodes = self.q.filter_by_workflow(nodes, self.workflow_id)

        # Group by step
        steps = self.q.group_by_step(workflow_nodes)

        for step_name, step_nodes in steps.items():
            # Calculate average memory
            memory_values = [
                n.properties.get("memory_mb", 0)
                for n in step_nodes
                if n.properties.get("memory_mb")
            ]

            if memory_values:
                avg_memory = sum(memory_values) / len(memory_values)

                if avg_memory > self.memory_threshold_mb:
                    proposals.append(self.create_proposal(
                        title=f"Reduce memory usage for {step_name}",
                        description=f"Average memory usage is {avg_memory:.0f}MB (threshold: {self.memory_threshold_mb}MB)",
                        risk=RiskLevel.MEDIUM,
                        target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
                        payload={
                            "step": step_name,
                            "setting": "memory_limit_mb",
                            "value": int(avg_memory * 0.8),  # Reduce by 20%
                            "old_value": int(avg_memory),
                        },
                    ))

        return proposals
```

### Pattern 2: Custom Validation Rule

```python
class DataQualityRule(WorkflowRule):
    """Detects data quality issues in workflow steps."""

    def __init__(self, workflow_id: str, quality_threshold: float = 0.95):
        super().__init__(workflow_id)
        self.quality_threshold = quality_threshold

    def propose(self, nodes, edges=None):
        proposals = []

        workflow_nodes = self.q.filter_by_workflow(nodes, self.workflow_id)
        steps = self.q.group_by_step(workflow_nodes)

        for step_name, step_nodes in steps.items():
            # Calculate quality score
            quality_scores = [
                n.properties.get("quality_score", 1.0)
                for n in step_nodes
                if n.properties.get("quality_score") is not None
            ]

            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)

                if avg_quality < self.quality_threshold:
                    proposals.append(self.create_proposal(
                        title=f"Improve data quality for {step_name}",
                        description=f"Quality score is {avg_quality:.2%} (threshold: {self.quality_threshold:.2%})",
                        risk=RiskLevel.LOW,
                        target_paths=(f"prompts/{step_name}.txt",),
                        payload={
                            "prompt_name": step_name,
                            "setting": "validation_rules",
                            "value": "strict",
                        },
                    ))

        return proposals
```

### Pattern 3: Custom Cost Rule

```python
class CostOptimizationRule(WorkflowRule):
    """Detects expensive workflow steps."""

    def __init__(self, workflow_id: str, cost_threshold_usd: float = 1.0):
        super().__init__(workflow_id)
        self.cost_threshold_usd = cost_threshold_usd

    def propose(self, nodes, edges=None):
        proposals = []

        workflow_nodes = self.q.filter_by_workflow(nodes, self.workflow_id)
        steps = self.q.group_by_step(workflow_nodes)

        for step_name, step_nodes in steps.items():
            # Calculate total cost
            costs = [
                n.properties.get("cost_usd", 0.0)
                for n in step_nodes
                if n.properties.get("cost_usd")
            ]

            if costs:
                total_cost = sum(costs)
                avg_cost = total_cost / len(costs)

                if avg_cost > self.cost_threshold_usd:
                    proposals.append(self.create_proposal(
                        title=f"Reduce cost for {step_name}",
                        description=f"Average cost is ${avg_cost:.4f} per execution (threshold: ${self.cost_threshold_usd:.4f})",
                        risk=RiskLevel.LOW,
                        target_paths=(f"config/workflows/{self.workflow_id}.yaml",),
                        payload={
                            "step": step_name,
                            "setting": "model",
                            "value": "gpt-3.5-turbo",  # Cheaper model
                            "old_value": "gpt-4",
                        },
                    ))

        return proposals
```

---

## Workflow Best Practices

### DO ✅

**1. Use Consistent Step Names**

```python
# Good - consistent naming
make_event(..., attributes={
    "step_name": "extract",
    ...
})

make_event(..., attributes={
    "step_name": "transform",
    ...
})

# Avoid - inconsistent
make_event(..., attributes={
    "step_name": "ExtractData",
    ...
})

make_event(..., attributes={
    "step_name": "transform_data",
    ...
})
```

**2. Include All Workflow Attributes**

```python
# Good - complete attributes
make_event(..., attributes={
    "workflow_id": "etl_pipeline",
    "workflow_run_id": "run_001",
    "step_name": "extract",
    "step_id": "run_001_step_1",
    "step_order": 1,
    "parent_step_id": None,
    "status": StepStatus.SUCCESS.value,
    "latency_ms": 500,
    "error_type": None,
})

# Avoid - missing attributes
make_event(..., attributes={
    "step_name": "extract",
    "status": "success",
})
```

**3. Use WorkflowAwareGraphBuilder for Workflows**

```python
# Good - uses workflow builder
engine = AutoImproveEngine(
    graph_builder=WorkflowAwareGraphBuilder(),
    ...
)

# Avoid - basic builder misses relationships
engine = AutoImproveEngine(
    graph_builder=ContextGraphBuilder(),
    ...
)
```

**4. Leverage Pre-Built Rules**

```python
# Good - use existing rules
rules = [
    FailingStepRule(...),
    SlowStepRule(...),
    ErrorPropagationRule(...),
]

# Avoid - reinventing the wheel
# (unless you need custom behavior)
```

### DON'T ❌

**1. Don't Mix Workflow Runs**

```python
# Avoid - mixing runs in same workflow_id
make_event(..., attributes={
    "workflow_id": "pipeline_v1_and_v2",
    "workflow_run_id": "mixed_run",
    ...
})

# Good - separate workflows
make_event(..., attributes={
    "workflow_id": "pipeline_v1",
    "workflow_run_id": "run_001",
    ...
})

make_event(..., attributes={
    "workflow_id": "pipeline_v2",
    "workflow_run_id": "run_001",
    ...
})
```

**2. Don't Skip Status Field**

```python
# Avoid - missing status
make_event(..., attributes={
    "step_name": "extract",
    # No status!
})

# Good - always include status
make_event(..., attributes={
    "step_name": "extract",
    "status": StepStatus.SUCCESS.value,
})
```

**3. Don't Ignore Errors**

```python
# Avoid - generic failure
make_event(..., attributes={
    "status": StepStatus.FAILURE.value,
    # No error details!
})

# Good - include error context
make_event(..., attributes={
    "status": StepStatus.FAILURE.value,
    "error_type": "timeout",
    "error_message": "API request timed out after 30000ms",
})
```

---

## API Reference

### WorkflowAwareGraphBuilder

```python
class WorkflowAwareGraphBuilder:
    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        """
        Build workflow graph with relationships.

        Args:
            events: Workflow step events

        Returns:
            ContextGraphDelta with nodes and edges
        """
```

### WorkflowQueryHelpers

```python
class WorkflowQueryHelpers:
    def filter_by_workflow(self, nodes, workflow_id: str) -> list[GraphNode]:
        """Filter nodes by workflow ID."""

    def filter_by_step(self, nodes, step_name: str) -> list[GraphNode]:
        """Filter nodes by step name."""

    def filter_by_status(self, nodes, status: str) -> list[GraphNode]:
        """Filter nodes by status."""

    def group_by_step(self, nodes) -> dict[str, list[GraphNode]]:
        """Group nodes by step name."""

    def group_by_workflow_run(self, nodes) -> dict[str, list[GraphNode]]:
        """Group nodes by workflow run ID."""

    def count_by_status(self, nodes) -> dict[str, int]:
        """Count nodes by status."""

    def find_error_propagation(self, nodes, edges) -> list[dict]:
        """Find error propagation chains."""

    def find_root_cause_failures(self, nodes, edges) -> list[GraphNode]:
        """Find root cause failures."""

    def trace_execution_path(self, nodes, run_id: str) -> list[dict]:
        """Trace execution path for a workflow run."""
```

### Workflow Metrics

```python
def step_success_rate(nodes, workflow_id: str = None, step_name: str = None) -> float:
    """Calculate success rate for steps."""

def step_failure_rate(nodes, workflow_id: str = None, step_name: str = None) -> float:
    """Calculate failure rate for steps."""

def step_latency_stats(nodes, workflow_id: str = None, step_name: str = None) -> dict:
    """Calculate latency statistics for steps."""

def step_error_types(nodes, step_name: str) -> dict[str, int]:
    """Count error types for a step."""

def workflow_throughput(nodes, workflow_id: str) -> float:
    """Calculate workflow throughput (runs per hour)."""

def workflow_bottlenecks(nodes, workflow_id: str) -> list[dict]:
    """Identify workflow bottlenecks."""

def critical_path_analysis(nodes, edges, workflow_id: str) -> dict:
    """Analyze critical path in workflow."""
```

---

## See Also

- [Observation Events API](observation_events.md) - Creating workflow events
- [Context Graph API](context_graph.md) - Graph structure
- [Decision Graph API](decision_graph.md) - Creating workflow rules
- [Evaluation API](evaluation.md) - Evaluating workflow proposals
- [Examples](examples.md) - Complete workflow examples
