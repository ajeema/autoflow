# AutoFlow API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [API Reference](#api-reference)
   - [Observation Events](observation_events.md)
   - [Context Graph](context_graph.md)
   - [Decision Graph](decision_graph.md)
   - [Proposals](proposals.md)
   - [Evaluation](evaluation.md)
   - [Apply (Policy & Backend)](apply.md)
   - [Workflow Module](workflow.md)
6. [Extension Guide](extension_guide.md)
7. [Examples](examples.md)

---

## Overview

AutoFlow is a **policy-gated, observable, evaluation-driven auto-improvement engine** for AI systems and workflows. It enables proactive, iterative optimization through structured observation, context graphs, decision logic, and safe application of changes.

### Key Features

- ✅ **Structured Observation** - Track system events with rich metadata
- ✅ **Context Graphs** - Build graphs that capture relationships and patterns
- ✅ **Decision Graphs** - Analyze patterns and generate improvement proposals
- ✅ **Evaluation Gates** - Validate changes before applying (shadow, replay)
- ✅ **Policy-Gated Application** - Apply changes only when safe
- ✅ **Full Auditability** - Every decision and action is tracked

### Design Philosophy

AutoFlow does **not** mutate your system freely. It:

1. **Observes** what your system is doing
2. **Builds** a graph of events and outcomes
3. **Detects** optimization opportunities
4. **Proposes** typed, auditable proposals
5. **Evaluates** them (shadow and/or replay)
6. **Applies** them only if policy allows

**The system remains in control.**

---

## Core Concepts

### ObservationEvent

The fundamental unit of data in AutoFlow. All context comes from events.

```python
from autoflow.observe.events import make_event

event = make_event(
    source="my_app",
    name="user_action",
    attributes={
        "user_id": "user_123",
        "action": "login",
        "success": True,
        "latency_ms": 150,
    },
)
```

### Context Graph

A graph representation of your system's events and relationships.

- **Nodes** - Represent events, steps, metrics
- **Edges** - Represent relationships (flow, causality, dependencies)

### Decision Graph

A set of rules that analyze the context graph and generate proposals.

### Change Proposal

A typed, auditable suggestion for improvement.

```python
ChangeProposal(
    proposal_id="prop_123",
    kind=ProposalKind.CONFIG_EDIT,
    title="Increase retry limit",
    description="Observed repeated timeouts",
    risk=RiskLevel.LOW,
    target_paths=("config/workflows.yaml",),
    payload={"max_retries": 3},
)
```

### Evaluation

Validating proposals before applying.

- **Shadow Evaluation** - Dry-run, always passes
- **Replay Evaluation** - Test on historical data with gates
- **Composite Evaluation** - Combine multiple evaluators

### Apply

Applying approved changes to your system.

- **Policy** - What changes are allowed (paths, risk levels)
- **Backend** - How to apply (git patch, PR, etc.)

---

## Quick Start

### Basic Usage

```python
from autoflow import AutoImproveEngine
from autoflow.observe.events import make_event
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.types import RiskLevel

# Setup
store = SQLiteGraphStore(db_path="autoflow.db")
engine = AutoImproveEngine(
    store=store,
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(rules=[
        HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3)
    ]),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)

# Observe
events = [
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
]
engine.ingest(events)

# Analyze
proposals = engine.propose()

# Evaluate
results = [engine.evaluator.evaluate(p) for p in proposals]

# Apply
for proposal, result in zip(proposals, results):
    if result.passed:
        engine.applier.apply(proposal)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                         │
│                  (emits ObservationEvent)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  AutoImproveEngine                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ingest(events)                                       │  │
│  │   ↓                                                  │  │
│  │ ContextGraphBuilder.build_delta(events)             │  │
│  │   ↓                                                  │  │
│  │ ContextGraphStore.upsert(delta)                     │  │
│  │   ↓                                                  │  │
│  │ propose()                                            │  │
│  │   ↓                                                  │  │
│  │ DecisionGraph.run(nodes, edges)                     │  │
│  │   ↓                                                  │  │
│  │ Evaluator.evaluate(proposal)                         │  │
│  │   ↓                                                  │  │
│  │ Applier.apply(proposal)                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## API Reference

See individual API documentation files:

- [Observation Events](observation_events.md) - Creating and tracking events
- [Context Graph](context_graph.md) - Building and querying graphs
- [Decision Graph](decision_graph.md) - Rules and proposal generation
- [Proposals](proposals.md) - Proposal types and creation
- [Evaluation](evaluation.md) - Shadow, replay, and composite evaluation
- [Apply](apply.md) - Policies and backends
- [Workflow Module](workflow.md) - Multi-step workflow support
- [Extension Guide](extension_guide.md) - Customizing and extending AutoFlow
- [Examples](examples.md) - Complete usage examples

---

## Versioning

API version: 1.0.0

Stability: The core APIs are considered stable. Minor additions may occur in future versions.

---

## Support

- GitHub Issues: https://github.com/your-org/autoflow/issues
- Documentation: See individual API pages
- Examples: See `examples.md`
