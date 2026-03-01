# AutoFlow - Simple API Guide

## 🎯 Overview

AutoFlow now has a **minimal-boilerplate API** while maintaining all its power and flexibility.

### Before (30+ lines of boilerplate):
```python
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.apply.git_backend import GitApplyBackend
from pathlib import Path

# 1. Create store
store = SQLiteGraphStore(db_path="autoflow.db")

# 2. Create graph builder
builder = ContextGraphBuilder()

# 3. Create decision graph with rules
graph = DecisionGraph(
    rules=[HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3)]
)

# 4. Create evaluator
evaluator = CompositeEvaluator(evaluators=[ShadowEvaluator()])

# 5. Create applier
applier = ProposalApplier(
    policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
    backend=GitApplyBackend(repo_path=Path(".")),
)

# 6. Create engine
engine = AutoImproveEngine(
    store=store,
    graph_builder=builder,
    decision_graph=graph,
    evaluator=evaluator,
    applier=applier,
)

# 7. Use it
engine.ingest(events)
proposals = engine.propose()
```

### After (1 line!):
```python
from autoflow.factory import autoflow

# Just create and use
engine = autoflow()
engine.ingest(events)
proposals = engine.propose()
```

## 🚀 Quick Start

### Minimal Usage (No Configuration)
```python
from autoflow.factory import autoflow
from autoflow.observe.events import make_event

# Create engine with defaults (in-memory store)
engine = autoflow(in_memory=True)

# Track events
events = [
    make_event(
        source="my_agent",
        name="execution_failed",
        attributes={"agent_id": "agent_123", "error": "timeout"}
    ),
]
engine.ingest(events)

# Get proposals
proposals = engine.propose()
for p in proposals:
    print(f"{p.title}: {p.description}")
```

### With Async Support
```python
from autoflow.factory import autoflow

# Create async engine
engine = autoflow(in_memory=True, async_mode=True)

# Use in async context
async with engine:
    await engine.ingest(events)
    proposals = await engine.propose()
    # Auto-closes on exit
```

### With Persistence
```python
# SQLite storage
engine = autoflow(db_path="./my_autoflow.db")

# Or via environment variable
# AUTOFLOW_DB_PATH=./production.db
engine = autoflow()
```

## 🎨 Presets for Common Cases

### For Testing
```python
from autoflow.factory import autoflow_testing

engine = autoflow_testing()  # In-memory, no persistence
```

### For Shadow Evaluation (No Applying)
```python
from autoflow.factory import autoflow_shadow

engine = autoflow_shadow()  # Evaluate only, don't apply
```

### For Auto-Apply (with Safety Rails)
```python
from autoflow.factory import autoflow_auto_apply

engine = autoflow_auto_apply(
    allowed_paths=["config/", "prompts/"]
)
# Will automatically apply proposals to allowed paths
```

### With Custom Rules
```python
from autoflow.factory import autoflow_with_rules
from autoflow.decide.rules import HighErrorRateRetryRule

engine = autoflow_with_rules(
    rules=[
        HighErrorRateRetryRule(workflow_id="api", threshold=3),
        HighErrorRateRetryRule(workflow_id="database", threshold=5),
    ],
    db_path="./production.db"
)
```

## 🎯 Tracking Agents & Tools (Minimal Code)

### Decorator-Based Agent Tracking
```python
from autoflow.track import track_agent

@track_agent(agent_id="search_agent", model="gpt-4")
async def search_agent(query: str):
    # Your agent logic
    return await search(query)

# That's it! Execution is automatically tracked
result = await search_agent("test query")
```

### Workflow Tracking
```python
from autoflow.track import track_workflow

async with track_workflow(workflow_id="data_pipeline"):
    await step1()
    await step2()
    await step3()
# Errors automatically tracked and trigger proposals
```

### Tool Call Tracking
```python
from autoflow.track import track_tool_call

await track_tool_call(
    tool_name="search",
    agent_id="my_agent",
    parameters={"query": "test"},
    result=search_results,
)
```

### Quick Error Tracking
```python
from autoflow.track import track_error

try:
    await risky_operation()
except Exception as e:
    await track_error("my_component", e, {"context": "value"})
```

## 🔧 Advanced Usage (Still Simple)

### Custom Store
```python
from autoflow.factory import autoflow
from my_custom_store import MyPostgresStore

engine = autoflow(store=MyPostgresStore())
```

### Custom Evaluators
```python
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.factory import autoflow

class MyEvaluator:
    def evaluate(self, proposal):
        # Your evaluation logic
        return EvaluationResult(...)

engine = autoflow(evaluators=[MyEvaluator()])
```

### Factory Pattern Integration
```python
from autoflow.factory import autoflow
from autoflow.track import track_agent, track_workflow

class AgentFactory:
    """Factory for creating AutoFlow-instrumented agents"""

    def __init__(self):
        # One-time setup
        self.autoflow = autoflow(
            in_memory=True,
            rules=[my_custom_rules],
        )

    def create_agent(self, config):
        @track_agent(agent_id=config.id)
        async def instrumented_agent(query):
            return await config.handler(query)

        return instrumented_agent
```

## 📊 Comparison: Code Required

| Task | Before | After |
|------|--------|-------|
| Basic setup | 30+ lines | 1 line |
| Track agent execution | Manual event emission | 1 decorator |
| Track workflow | Manual event emission | 1 context manager |
| Track errors | Manual try/emit | 1 function call |
| Custom rules | Wire up manually | Add to list |
| Async support | Not available | Add `async_mode=True` |

## ✅ Key Features Maintained

- ✅ **Full power**: All original capabilities available
- ✅ **Async support**: First-class async/await support
- ✅ **Flexible**: Still fully customizable via parameters
- ✅ **Type-safe**: Full Pydantic model support
- ✅ **Factory-ready**: Works great with factory patterns
- ✅ **Zero-config**: Works out of the box with defaults
- ✅ **Explicit**: All imports are top-level and explicit

## 🎓 Best Practices

1. **Start Simple**: Use `autoflow(in_memory=True)` for development
2. **Add Persistence**: Switch to `autoflow(db_path="./prod.db")` for production
3. **Use Decorators**: Prefer `@track_agent` over manual event emission
4. **Set Rules**: Add rules once during engine creation
5. **Async When Needed**: Use `async_mode=True` for async workflows

## 📦 What's New

### New Files:
- `src/autoflow/factory.py` - Simple factory functions
- `src/autoflow/track.py` - High-level tracking decorators
- `src/autoflow/graph/store_async.py` - Async store interface + in-memory store
- `src/autoflow/orchestrator/engine_async.py` - Async engine implementation
- `src/autoflow/apply/backend.py` - Built-in backends (NoOp, Logging, Callback)

### Improvements:
- ✨ **1-line engine creation**: `autoflow()`
- ✨ **Async/await support**: `async_mode=True`
- ✨ **Decorator-based tracking**: `@track_agent`
- ✨ **Context managers**: `async with autoflow()`
- ✨ **Presets**: Common configurations built-in
- ✨ **In-memory store**: For testing and ephemeral use
- ✨ **Zero boilerplate**: Works out of the box
