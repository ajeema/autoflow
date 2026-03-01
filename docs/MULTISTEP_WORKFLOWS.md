# Multi-Step Workflow Analysis with AutoFlow

## Can AutoFlow Handle Multi-Step Workflows?

### Short Answer
**Yes, but requires some enhancement.** The core architecture supports it, but you need to add workflow-aware tracking.

---

## Current Capabilities vs Gaps

### ✅ What's Already Supported

| Capability | Status | Notes |
|------------|--------|-------|
| Track arbitrary events via `ObservationEvent` | ✅ Built-in | Can add step_id, parent_step_id, etc. as attributes |
| Store events in graph database | ✅ Built-in | SQLiteGraphStore queries work |
| Write custom rules for analysis | ✅ Built-in | Rules can analyze patterns in events |
| Generate targeted proposals | ✅ Built-in | Can target specific files/configs |
| Query nodes by type | ✅ Built-in | `store.query_nodes("workflow_step")` |

### ❌ What's Missing / Needs Enhancement

| Capability | Status | Solution |
|------------|--------|----------|
| Workflow-aware event types | ❌ Missing | Add `StepEvent` wrapper (shown in demo) |
| Build edges between steps | ❌ Missing | Enhance `ContextGraphBuilder` (shown in demo) |
| Track causal relationships | ❌ Missing | Add `WorkflowAwareGraphBuilder` |
| Step-level proposal helpers | ❌ Missing | Add domain-specific rules |
| Query by workflow relationships | ❌ Missing | Add graph traversal queries |

---

## The Demo: What's Possible Now

The `multistep_demo.py` shows a complete working example:

```bash
python3 multistep_demo.py
```

### What It Demonstrates

1. **Step-Level Tracking**
   ```python
   StepEvent(
       workflow_run_id="pipeline_123",
       step_name="extract",
       step_id="pipeline_123_step_1",
       parent_step_id=None,  # First step
       status=StepStatus.SUCCESS,
       latency_ms=850,
   )
   ```

2. **Enhanced Context Graph**
   ```python
   WorkflowAwareGraphBuilder()
   # Creates:
   # - Nodes for each step execution
   # - Edges: step → next_step (workflow flow)
   # - Edges: error → caused_failure (causality)
   ```

3. **Targeted Analysis Rules**
   ```python
   FailingStepRule()      # Finds which steps fail most
   SlowStepRule()         # Identifies bottlenecks
   ErrorPropagationRule() # Tracks error cascades
   ```

4. **Step-Level Proposals**
   ```json
   {
     "title": "Increase timeout for 'extract' step",
     "description": "Step 'extract' has 25% timeout rate...",
     "payload": {
       "step": "extract",
       "setting": "timeout_ms",
       "value": 8500
     }
   }
   ```

---

## How to Implement Multi-Step Analysis

### 1. Define Your Event Schema

```python
@dataclass
class StepEvent:
    workflow_run_id: str
    step_name: str
    step_id: str
    parent_step_id: str | None
    status: StepStatus
    latency_ms: float
    error_type: str | None
    metadata: dict

    def to_observation_event(self) -> ObservationEvent:
        return make_event(
            source="workflow_engine",
            name="step_execution",
            attributes=asdict(self),
        )
```

### 2. Track Workflow Executions

```python
def run_my_workflow():
    events = []

    # Step 1
    step1 = execute_step_1()
    events.append(StepEvent(
        workflow_run_id="run_123",
        step_name="extract",
        step_id="run_123_step_1",
        status=StepStatus.SUCCESS if step1.success else StepStatus.FAILURE,
        latency_ms=step1.latency_ms,
        error_type=step1.error,
    ).to_observation_event())

    # Step 2 (depends on Step 1)
    if step1.success:
        step2 = execute_step_2(depends_on=step1)
        events.append(StepEvent(
            workflow_run_id="run_123",
            step_name="transform",
            step_id="run_123_step_2",
            parent_step_id="run_123_step_1",
            status=...,
        ).to_observation_event())

    return events
```

### 3. Build Enhanced Context Graph

```python
class WorkflowAwareGraphBuilder:
    def build_delta(self, events):
        nodes = []
        edges = []

        # Group by workflow run
        runs = group_by_workflow(events)

        for run_id, run_events in runs.items():
            # Create sequential edges (step → next_step)
            sorted_steps = sort_by_step_id(run_events)
            for i in range(len(sorted_steps) - 1):
                edges.append(GraphEdge(
                    edge_type="next_step",
                    from_node_id=sorted_steps[i].node_id,
                    to_node_id=sorted_steps[i+1].node_id,
                ))

            # Create causality edges (error → caused_failure)
            for step in sorted_steps:
                if step.failed:
                    for downstream in find_dependent_steps(step):
                        edges.append(GraphEdge(
                            edge_type="caused_by",
                            from_node_id=step.node_id,
                            to_node_id=downstream.node_id,
                        ))

        return ContextGraphDelta(nodes, edges)
```

### 4. Write Analysis Rules

```python
class FailingStepRule:
    def propose(self, nodes):
        # Group by step_name
        steps_by_name = group_nodes_by(nodes, "step_name")

        for step_name, executions in steps_by_name.items():
            failure_rate = calc_failure_rate(executions)

            if failure_rate > threshold:
                # Create targeted proposal
                return ChangeProposal(
                    title=f"Fix step: {step_name}",
                    payload={"step": step_name, "fix": "..."},
                    target_paths=(f"config/steps/{step_name}.yaml",),
                )
```

---

## What Enhancements Would Make This Easier?

### 1. Built-in Workflow Types

**Add to core types:**
```python
@dataclass
class WorkflowStepEvent(ObservationEvent):
    workflow_id: str
    workflow_run_id: str
    step_name: str
    step_id: str
    parent_step_id: str | None = None
    step_status: str  # success, failure, skipped
    step_order: int
```

### 2. Enhanced Graph Builder

**Add to core:**
```python
class WorkflowGraphBuilder(ContextGraphBuilder):
    """
    Automatically builds workflow graphs from events.
    Creates edges for:
    - Sequential flow (step → step)
    - Dependencies (parent → child)
    - Error propagation
    """
```

### 3. Graph Query Helpers

**Add to store:**
```python
class ContextGraphStore:
    def get_workflow_runs(self, workflow_id: str) -> list[WorkflowRun]: ...
    def get_step_history(self, step_name: str) -> list[StepExecution]: ...
    def find_failure_cascades(self) -> list[FailureChain]: ...
    def get_step_dependencies(self) -> dict[str, list[str]]: ...
```

### 4. Workflow Analysis Helpers

**New module: `autoflow/workflow/`**
```python
# Step-level metrics
def step_success_rate(step_name: str) -> float
def step_latency_p95(step_name: str) -> float
def step_error_types(step_name: str) -> Counter

# Workflow-level metrics
def workflow_throughput(workflow_id: str) -> float
def workflow_bottlenecks(workflow_id: str) -> list[str]
def critical_path_analysis(workflow_id: str) -> list[str]

# Failure analysis
def error_propagation_graph() -> DiGraph
def root_cause_analysis(workflow_run_id: str) -> str
```

---

## Real-World Use Cases

### 1. Data Pipeline Monitoring
```
Extract → Transform → Validate → Load
    ↓           ↓          ↓        ↓
  track      track      track    track
```
- Find which transformations fail most
- Detect bottlenecks (slow validate step)
- Track error cascades (extract fails → all downstream skipped)

### 2. ML Model Pipeline
```
Preprocess → Feature Eng → Train → Evaluate → Deploy
    ↓            ↓          ↓        ↓         ↓
  proposals for each step independently
```
- Optimize slow feature engineering
- Fix preprocessing validation errors
- Tune training hyperparameters per step

### 3. ETL Workflow
```
Ingest → Clean → Dedupe → Aggregate → Store
```
- Add caching to slow ingest step
- Fix dedupe validation logic
- Parallelize independent aggregate steps

### 4. CI/CD Pipeline
```
Build → Test → Scan → Deploy
```
- Fix flaky tests
- Optimize slow build step
- Add retry logic for deployment failures

---

## Quick Reference

### To Track Multi-Step Workflows NOW:

| Task | Approach |
|------|----------|
| **Track steps** | Add step_id, parent_step_id to event attributes |
| **Build relationships** | Create custom `WorkflowAwareGraphBuilder` |
| **Analyze steps** | Write rules that filter/group by step_name |
| **Target proposals** | Use step-specific file paths in target_paths |
| **Query by step** | Filter nodes by `properties.step_name` |

### To Get Better Support:

1. **Use the demo** as a template for your workflow
2. **Extend the graph builder** for your relationship patterns
3. **Write domain-specific rules** for your analysis needs
4. **Contribute** workflow types/helpers to core AutoFlow

---

## Summary

| Question | Answer |
|----------|--------|
| Can it track multi-step workflows? | **Yes**, with custom event attributes |
| Can it analyze individual steps? | **Yes**, with custom rules |
| Can it target specific steps? | **Yes**, via targeted proposals |
| Does it have workflow-aware graph? | **No**, but you can build it |
| Does it have workflow helpers? | **No**, but you can add them |

**Bottom line**: AutoFlow's architecture is flexible enough to support multi-step workflow analysis today. The demo shows a complete working implementation. Core enhancements would make it more polished and easier to use.
