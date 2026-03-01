# AutoFlow

> A policy-gated, observable, evaluation-driven auto-improvement engine for AI workflows.

AutoFlow enables safe, continuous improvement of AI systems—agents, prompts, routing, and tool orchestration—through structured observation, context graphs, and policy-controlled evaluation. Your AI systems get better over time, without breaking what works.

**Core Loop:** `Observe → Build Context Graph → Decide → Propose → Evaluate → Apply`

---

## Why AutoFlow?

AI workflows have many tunable levers (prompts, routing, retries, tool selection), but tuning them safely is hard. AutoFlow provides:

- **Safe by default** — No arbitrary mutation; all changes are typed, evaluated, and policy-gated
- **Observable** — OpenTelemetry-ready with full audit trails
- **Regression-gated** — Deterministic replay evaluation prevents breaking changes
- **Production-ready** — Async support, error tolerance, enterprise security
- **Incrementally adoptable** — Start small, add capabilities as needed

---

## Quick Start

```bash
pip install autoflow
```

```python
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.apply.policy import ApplyPolicy
from autoflow.evaluate.shadow import ShadowEvaluator

# Set up the engine with a simple rule
engine = AutoImproveEngine(
    decision_graph=DecisionGraph(rules=[
        HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3)
    ]),
    evaluator=ShadowEvaluator(),
    applier=ProposalApplier(
        policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
    ),
)

# Ingest events and generate proposals
engine.ingest(events)
proposals = engine.propose()
```

[See full examples](#minimal-working-example-shadow-evaluation) below.

---

## 📦 Modules

### Context Graph Framework

**NEW in v0.2.0:** A complete, production-ready knowledge graph framework for AI applications.

The Context Graph Framework provides:

- **Graph Operations:** Entities, relationships, multi-hop traversals
- **Multiple Backends:** InMemory (dev), Neo4j (production)
- **LLM Integration:** Graph-to-text, text-to-Cypher, entity extraction
- **Domain Modules:** Brand, Campaign, Publisher (extensible)
- **Enterprise Security:** Auth, authorization, audit logging

**Quick Start:**

```python
from autoflow.context_graph.core import ContextGraph, Entity, TraversalPattern
from autoflow.context_graph.backends import InMemoryBackend

# Initialize
graph = ContextGraph(backend=InMemoryBackend())

# Add entities
nike = Entity(type="brand", properties={"name": "Nike", "vertical": "Apparel"})
graph.add_entity(nike)

# Traverse for insights
subgraph = graph.traverse("brand:nike", TraversalPattern("-[*]->", max_hops=2))

# Get LLM-ready context
context = graph.get_context_for_llm("brand:nike", max_hops=2)
```

**Features:**

- 🧠 **AI-Native:** Designed for LLM integration from day one
- 🔒 **Secure by Default:** Input validation, sanitization, auth/audit
- 🎯 **Flexible:** Configurable validation, pluggable backends
- 📊 **Observable:** Comprehensive audit logging
- 🚀 **Production-Ready:** Async operations, error-tolerant

**Documentation:**
- [Context Graph Guide](docs/context_graph.md) - Overview and usage
- [API Reference](docs/api_reference.md) - Complete API documentation
- [Auth & Audit Guide](docs/auth_audit_guide.md) - Security deployment
- [Security Demo](examples/security_demo.py) - See protections in action
- [Auth/Audit Demo](examples/auth_audit_demo.py) - Full security example

---

## Philosophy

AutoFlow does **not** mutate your system freely. It:

1. **Observes** — Ingests structured telemetry from your system
2. **Builds** — Constructs a graph of events and outcomes
3. **Decides** — Detects optimization opportunities via rules
4. **Proposes** — Generates typed, auditable change proposals
5. **Evaluates** — Validates with shadow/replay evaluation
6. **Applies** — Mutates only when policy allows

**You remain in control.**

---

## Architecture

The core loop is modular and replaceable:

| Stage | Purpose | Swappable |
|-------|---------|-----------|
| Observe | Ingest telemetry | Collectors, event formats |
| Build | Context graph | SQLite, PostgreSQL, Neo4j |
| Decide | Generate proposals | Rules, ML policies |
| Evaluate | Validate | Shadow, replay, canary |
| Apply | Mutate safely | Git, PR backends |

---

## Packaging and Extras

AutoFlow ships as a publishable PyPI package with optional extras:

```bash
pip install autoflow
```

Recommended extras:

```bash
pip install "autoflow[dev]"      # ruff, mypy, pytest, build tooling
pip install "autoflow[otel]"     # OpenTelemetry API + SDK
pip install "autoflow[ai]"       # installs AI-domain module autoflow_ai
pip install "autoflow[neo4j]"    # Neo4j graph backend
pip install "autoflow[postgres]" # PostgreSQL graph backend
pip install "autoflow[ai,otel]"  # common production combo
pip install "autoflow[all]"      # install all runtime extras (otel, ai, neo4j, postgres)
```

### What autoflow_ai is

`autoflow_ai` is an AI-domain module that provides:

- A typed replay dataset format for AI workflows (tool calls, model calls, outcomes)
- Standard AI metrics (success rate, tool error rate, p95 latency, cost)
- AI-specific replay evaluation glue
- AI-focused rule examples (e.g., retry tuning)

AutoFlow core remains minimal and generic; autoflow_ai is "batteries included" for AI workflows.

---

## Repository Structure

```
autoflow/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── MANIFEST.in
├── src/
│   ├── autoflow/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── version.py
│   │   ├── errors.py
│   │   ├── types.py
│   │   ├── logging.py
│   │   ├── otel.py
│   │   │
│   │   ├── observe/
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   └── events.py
│   │   │
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── context_graph.py
│   │   │   ├── store.py
│   │   │   └── sqlite_store.py
│   │   │
│   │   ├── decide/
│   │   │   ├── __init__.py
│   │   │   ├── decision_graph.py
│   │   │   └── rules.py
│   │   │
│   │   ├── propose/
│   │   │   ├── __init__.py
│   │   │   └── proposals.py
│   │   │
│   │   ├── evaluate/
│   │   │   ├── __init__.py
│   │   │   ├── evaluator.py
│   │   │   ├── shadow.py
│   │   │   └── replay.py          # NEW: deterministic replay evaluator
│   │   │
│   │   ├── apply/
│   │   │   ├── __init__.py
│   │   │   ├── applier.py
│   │   │   ├── policy.py
│   │   │   └── git_backend.py
│   │   │
│   │   └── orchestrator/
│   │       ├── __init__.py
│   │       └── engine.py
│   │
│   └── autoflow_ai/
│       ├── __init__.py            # NEW: AI-domain module (optional extra)
│       ├── schemas.py             # typed AI run schema
│       ├── dataset.py             # JSONL dataset loader
│       ├── metrics.py             # standard AI metrics
│       ├── rules/
│       │   ├── __init__.py
│       │   └── retry_tuning.py    # example AI rule
│       └── eval/
│           ├── __init__.py
│           └── replay_ai.py       # glue: AI replay -> core replay evaluator
│
└── tests/
    └── test_engine_smoke.py
```

---

## Folder Breakdown

### autoflow/observe/

Responsible for ingestion of structured telemetry.

**events.py**

Creates structured observation events.

Why: Your system must emit structured events if you want deterministic improvement.

**collector.py**

Pluggable sink for storing events (file, DB, Kafka, etc.)

Why: Separation of concerns. Collection ≠ storage.

### autoflow/graph/

Builds and stores the Context Graph.

**context_graph.py**

Transforms events into nodes and edges.

Why: We reason about patterns and flows, not raw logs.

**store.py**

Graph storage interface.

Why: You may swap SQLite for Postgres, Neo4j, etc.

**sqlite_store.py**

Default embedded store.

Why: Zero dependency local persistence, good for local dev and small deployments.

### autoflow/decide/

The Decision Graph layer.

**rules.py**

Rule-based proposal generation (extensible).

Examples:
- Detect repeated tool failures
- Detect excessive retries
- Detect human overrides
- Detect high latency patterns

Why: Start deterministic before adding ML/LLM heuristics.

**decision_graph.py**

Orchestrates all rules into a unified proposal stream.

### autoflow/propose/

Defines structured change proposals.

**proposals.py**

Helpers to construct proposals in consistent conventions.

Why: Never return free-form text. Always return typed diffs/config edits with explicit targets.

### autoflow/evaluate/

Validation before change.

**shadow.py**

Validates structure and policy safety without applying.

Why: Always support non-destructive dry-run and fast CI checks.

**replay.py** (NEW)

Deterministic offline replay evaluator.

Why: Enables regression-gated iteration by comparing baseline vs candidate metrics on historical data.

**evaluator.py**

Composite evaluation orchestration.

Why: You can combine shadow + replay + future canary evaluators.

### autoflow/apply/

Responsible for safe mutation.

**policy.py**

Defines what is allowed:
- allowed paths
- allowed proposal types
- max risk level

Why: This is your blast-radius limiter.

**git_backend.py**

Applies text patches via git apply.

Why: Never mutate main directly. Prefer PR-based flows in production.

**applier.py**

Combines policy checks with a backend implementation.

### autoflow/orchestrator/

Main control plane.

**engine.py**

Coordinates the full loop:
- ingest
- propose
- evaluate
- apply

### AI-Domain Module: autoflow_ai (optional extra)

`autoflow_ai` is installed via:

```bash
pip install "autoflow[ai]"
```

It provides a standard replay dataset for AI workflows:
- Tool calls (latency, success, error type)
- Model calls (latency, tokens)
- Outcomes (success, override, cost, optional quality score)

It also includes:
- Standard AI metrics
- A replay evaluator wrapper that plugs into core replay evaluation
- AI-specific decision rules (starting with retry tuning)

Why: AI workflows have natural measurable levers (prompts, routing, retries, tool selection) that are reversible and evaluable offline. The AI module makes this easy.

---

## Installation

Local dev:

```bash
pip install -e ".[dev]"
```

Or after publishing:

```bash
pip install autoflow
```

Optional extras:

```bash
pip install "autoflow[ai]"
pip install "autoflow[otel]"
pip install "autoflow[neo4j]"
pip install "autoflow[postgres]"
pip install "autoflow[all]"  # installs all runtime extras
```

---

## Minimal Working Example (Shadow Evaluation)

Create a directory:

```
example_project/
├── config/
│   └── workflows.yaml
└── run_autoflow.py
```

**config/workflows.yaml**

```yaml
workflows:
  my_workflow:
    retry_policy:
      max_retries: 1
      backoff_ms: [100]
      jitter: false
```

**run_autoflow.py**

```python
from pathlib import Path

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event

store = SQLiteGraphStore(db_path="autoflow_graph.db")

engine = AutoImproveEngine(
    store=store,
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(
        rules=[
            HighErrorRateRetryRule(workflow_id="my_workflow", threshold=3),
        ]
    ),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)

events = [
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
    make_event(source="app", name="exception", attributes={"workflow_id": "my_workflow"}),
]

engine.ingest(events)

proposals = engine.propose()
results = engine.evaluate(proposals)
applied = engine.apply(proposals, results)

print("Proposals:")
for p in proposals:
    print("-", p.title)

print("Applied changes:")
for a in applied:
    print("-", a.reference)
```

---

## Real Replay Evaluation Example (AI workflows)

This example shows:
- loading a historical replay dataset (JSONL)
- running a deterministic replay evaluator that gates regressions

**1) Create a replay dataset: replay_runs.jsonl**

Each line is one run:

```json
{"run_id":"r1","workflow_id":"support_router","tool_calls":[{"tool":"search","latency_ms":120,"success":true}],"model_calls":[{"model":"gpt","latency_ms":300,"input_tokens":800,"output_tokens":200}],"outcome":{"success":true,"human_override":false,"cost_usd":0.01}}
{"run_id":"r2","workflow_id":"support_router","tool_calls":[{"tool":"search","latency_ms":450,"success":false,"error_type":"timeout"}],"model_calls":[{"model":"gpt","latency_ms":280,"input_tokens":700,"output_tokens":180}],"outcome":{"success":false,"human_override":true,"cost_usd":0.01}}
{"run_id":"r3","workflow_id":"support_router","tool_calls":[{"tool":"search","latency_ms":200,"success":true}],"model_calls":[{"model":"gpt","latency_ms":320,"input_tokens":900,"output_tokens":220}],"outcome":{"success":true,"human_override":false,"cost_usd":0.01}}
```

**2) Use the AI replay evaluator**

```python
from pathlib import Path

from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.evaluate.replay import ReplayGates
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore

from autoflow_ai.dataset import load_jsonl_dataset
from autoflow_ai.eval.replay_ai import AIReplayEvaluator
from autoflow_ai.rules.retry_tuning import RetryTuningRule

ai_dataset = load_jsonl_dataset("replay_runs.jsonl")

replay = AIReplayEvaluator(
    dataset=ai_dataset,
    workflow_id="support_router",
    gates=ReplayGates(
        max_regressions={
            # don't regress p95 tool latency by > 100ms
            "p95_tool_latency_ms": 100.0,
            # don't increase average cost by > 2 cents
            "avg_cost_usd": 0.02,
        },
        min_improvements={
            # must improve success rate by >= 1%
            "success_rate": 0.01,
        },
    ),
).as_core()

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path="autoflow_graph.db"),
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(
        rules=[RetryTuningRule(workflow_id="support_router", exception_threshold=2)]
    ),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator(), replay]),
    applier=ProposalApplier(
        policy=ApplyPolicy(allowed_paths_prefixes=("config/", "prompts/", "skills/")),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)

# Ingest events from your system (here you'd ingest real telemetry)
# engine.ingest(...)

proposals = engine.propose()
results = engine.evaluate(proposals)

for r in results:
    print(r.passed, r.notes)
```

### What replay gates do

Replay evaluation computes baseline metrics from historical runs, simulates the candidate proposal effect (deterministically), then enforces:

- **Max regressions:** candidate cannot regress certain metrics beyond allowed deltas
- **Min improvements:** candidate must improve target metrics beyond required deltas

This is what makes iterative improvement safe and CI-friendly.

---

## How to Test It

### Shadow-based example

Initialize git:

```bash
git init
git add .
git commit -m "Initial commit"
```

Run:

```bash
python run_autoflow.py
```

Inspect:
- Generated proposals
- Working tree changes (if applying patches)

### Replay-based example

Install AI extras:

```bash
pip install "autoflow[ai]"
```

Create `replay_runs.jsonl` and run your replay script and verify gates pass/fail as expected.

---

## How to Integrate Into an AI System

Instrument your AI system to emit events like:

```python
from autoflow.observe.events import make_event

make_event(
    source="agent",
    name="tool_call",
    attributes={
        "workflow_id": "support_router",
        "tool": "vector_search",
        "latency_ms": 312,
        "success": True,
    },
)
```

Or:

```python
make_event(
    source="agent",
    name="human_override",
    attributes={
        "workflow_id": "triage",
        "reason": "wrong routing",
    },
)
```

Feed them to:

```python
engine.ingest(events)
```

Then periodically:

```python
proposals = engine.propose()
results = engine.evaluate(proposals)
engine.apply(proposals, results)
```

---

## Production Usage Pattern

Recommended safe workflow:

**observe → propose → evaluate → open PR → CI → merge**

Instead of auto-applying directly to main.

You can:
- Replace GitApplyBackend with a PR backend
- Add replay evaluation as a hard gate
- Add golden tests
- Add cost regression gates
- Add canary rollout evaluators

---

## Safety Guarantees

- No arbitrary command execution by default
- No direct commits to main
- Policy-restricted path edits
- Risk levels enforced
- Evaluation gated before apply
- Auditable proposals and outcomes

---

## Extending the System

### Add a new Rule

Create a new rule in `decide/rules.py` or `autoflow_ai/rules/`:

```python
class HighLatencyRule:
    ...
```

### Add a new Evaluator

Combine it via `CompositeEvaluator`:

```python
class GoldenTestEvaluator:
    ...
```

### Add a new Backend

Example:

```python
class GitHubPRBackend:
    ...
```

---

## Future Extensions

Contributions welcome for:

- LLM-based improvement heuristics
- Embedding-powered pattern detection
- Model selection auto-tuning
- Prompt regression detection
- Canary rollout engine
- Distributed graph store
- PR-first application workflow

---

## License

MIT License — see [LICENSE](LICENSE) for details.