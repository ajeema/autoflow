# Examples

## Overview

This page provides complete, end-to-end examples of using AutoFlow in real-world scenarios.

---

## Table of Contents

1. [Basic Setup](#example-1-basic-setup)
2. [API Optimization](#example-2-api-optimization)
3. [Workflow Optimization](#example-3-workflow-optimization)
4. [Prompt Engineering](#example-4-prompt-engineering)
5. [Database Performance](#example-5-database-performance)
6. [Custom Extension](#example-6-custom-extension)

---

## Example 1: Basic Setup

**Scenario:** Set up AutoFlow to observe a simple application and generate proposals.

### Step 1: Install AutoFlow

```bash
pip install autoflow
```

### Step 2: Create Basic Configuration

```python
# config.py
from pathlib import Path
from autoflow import AutoImproveEngine
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

# Create workspace
workspace = Path(".autoflow_workspace")
workspace.mkdir(exist_ok=True)

# Setup engine
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=workspace / "autoflow.db"),
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(rules=[
        HighErrorRateRetryRule(
            workflow_id="my_app",
            threshold=3,
        ),
    ]),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(
            allowed_paths_prefixes=("config/",),
            max_risk=RiskLevel.LOW,
        ),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)
```

### Step 3: Emit Events from Your Application

```python
# app.py
from autoflow.observe.events import make_event

def process_request(request):
    try:
        # Do work
        result = do_something(request)

        # Emit success event
        engine.ingest([make_event(
            source="my_app",
            name="request_processed",
            attributes={
                "success": True,
                "latency_ms": 150,
            },
        )])

        return result

    except Exception as e:
        # Emit error event
        engine.ingest([make_event(
            source="my_app",
            name="request_error",
            attributes={
                "success": False,
                "error_type": type(e).__name__,
            },
        )])
        raise
```

### Step 4: Generate and Apply Proposals

```python
# run_improvement.py

# Get all proposals
proposals = engine.propose()

print(f"Found {len(proposals)} proposals")

for proposal in proposals:
    print(f"\n{proposal.title}")
    print(f"  Description: {proposal.description}")
    print(f"  Risk: {proposal.risk}")

    # Evaluate
    result = engine.evaluator.evaluate(proposal)

    if result.passed:
        print(f"  ✓ Evaluation passed (score: {result.score:.2f})")

        # Apply
        try:
            engine.applier.apply(proposal)
            print(f"  ✓ Applied successfully")
        except Exception as e:
            print(f"  ✗ Apply failed: {e}")
    else:
        print(f"  ✗ Evaluation failed: {result.notes}")
```

---

## Example 2: API Optimization

**Scenario:** Optimize an external API call by adjusting timeout and retry policies based on observed performance.

### Step 1: Observe API Calls

```python
# api_client.py
import requests
import time
from autoflow.observe.events import make_event

class APIClient:
    def __init__(self, base_url: str, engine: AutoImproveEngine):
        self.base_url = base_url
        self.engine = engine

    def call(self, endpoint: str, method: str = "GET", **kwargs):
        url = f"{self.base_url}/{endpoint}"
        start = time.time()

        try:
            response = requests.request(method, url, timeout=5.0, **kwargs)
            latency_ms = (time.time() - start) * 1000

            # Emit success event
            self.engine.ingest([make_event(
                source="api_client",
                name="api_call",
                attributes={
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "success": response.status_code == 200,
                },
            )])

            return response

        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start) * 1000

            # Emit timeout event
            self.engine.ingest([make_event(
                source="api_client",
                name="api_call",
                attributes={
                    "endpoint": endpoint,
                    "method": method,
                    "latency_ms": latency_ms,
                    "success": False,
                    "error_type": "timeout",
                },
            )])

            raise

        except requests.exceptions.ConnectionError:
            latency_ms = (time.time() - start) * 1000

            # Emit connection error event
            self.engine.ingest([make_event(
                source="api_client",
                name="api_call",
                attributes={
                    "endpoint": endpoint,
                    "method": method,
                    "latency_ms": latency_ms,
                    "success": False,
                    "error_type": "connection_error",
                },
            )])

            raise
```

### Step 2: Create Custom Rule

```python
# rules.py
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from autoflow.decide.rules import HighErrorRateRetryRule
from uuid import uuid4

class APITimeoutRule:
    """Detects frequent timeouts and proposes timeout increase."""

    def __init__(self, endpoint: str, timeout_threshold: int = 5):
        self.endpoint = endpoint
        self.timeout_threshold = timeout_threshold

    def propose(self, nodes):
        proposals = []

        # Filter API call events for this endpoint
        api_calls = [
            n for n in nodes
            if n.properties.get("source") == "api_client"
            and n.properties.get("endpoint") == self.endpoint
        ]

        if len(api_calls) < 10:
            return proposals  # Not enough data

        # Count timeouts
        timeouts = [
            n for n in api_calls
            if n.properties.get("error_type") == "timeout"
        ]

        timeout_rate = len(timeouts) / len(api_calls)

        # If > 20% timeouts, propose increasing timeout
        if timeout_rate > 0.2:
            current_timeout = self.timeout_threshold * 1000  # ms
            new_timeout = current_timeout * 2

            proposals.append(ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.CONFIG_EDIT,
                title=f"Increase timeout for {self.endpoint}",
                description=f"{timeout_rate:.1%} of calls timeout (current: {current_timeout}ms)",
                risk=RiskLevel.LOW,
                target_paths=("config/api.yaml",),
                payload={
                    "endpoint": self.endpoint,
                    "setting": "timeout_ms",
                    "value": int(new_timeout),
                    "old_value": int(current_timeout),
                },
            ))

        return proposals
```

### Step 3: Setup Engine with API Rules

```python
# api_setup.py
from autoflow.workflow.rules import FailingStepRule

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=".autoflow_workspace/autoflow.db"),
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(rules=[
        APITimeoutRule(endpoint="/api/v1/process", timeout_threshold=5),
        APITimeoutRule(endpoint="/api/v1/analyze", timeout_threshold=5),
    ]),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(
            allowed_paths_prefixes=("config/",),
            max_risk=RiskLevel.LOW,
        ),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)
```

### Step 4: Run and Improve

```python
# main.py
from config import engine
from api_client import APIClient

# Create API client
api = APIClient(base_url="https://api.example.com", engine=engine)

# Make calls (over time)
for i in range(100):
    try:
        result = api.call("/api/v1/process", method="POST", json={"data": f"request_{i}"})
        print(f"Request {i}: Success")
    except:
        print(f"Request {i}: Failed")

# Periodically check for improvements
if i % 10 == 0:
    proposals = engine.propose()
    for proposal in proposals:
        result = engine.evaluator.evaluate(proposal)
        if result.passed:
            engine.applier.apply(proposal)
```

---

## Example 3: Workflow Optimization

**Scenario:** Optimize a multi-step ETL pipeline by identifying bottlenecks and failures.

### Step 1: Instrument Workflow

```python
# etl_pipeline.py
from autoflow.observe.events import make_event
from autoflow.types import StepStatus
import time

class ETLPipeline:
    def __init__(self, engine: AutoImproveEngine):
        self.engine = engine
        self.workflow_id = "etl_pipeline"

    def run(self, run_id: str):
        steps = ["extract", "transform", "validate", "load"]
        step_order = 1

        for step_name in steps:
            start = time.time()
            status = StepStatus.SUCCESS
            error_type = None
            error_message = None

            try:
                # Execute step
                if step_name == "extract":
                    self._extract(run_id)
                elif step_name == "transform":
                    self._transform(run_id)
                elif step_name == "validate":
                    self._validate(run_id)
                elif step_name == "load":
                    self._load(run_id)

                latency_ms = (time.time() - start) * 1000

            except TimeoutError:
                latency_ms = (time.time() - start) * 1000
                status = StepStatus.FAILURE
                error_type = "timeout"
                error_message = f"Step {step_name} timed out"

            except ValidationError as e:
                latency_ms = (time.time() - start) * 1000
                status = StepStatus.FAILURE
                error_type = "validation_error"
                error_message = str(e)

            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                status = StepStatus.FAILURE
                error_type = "unknown"
                error_message = str(e)

            # Emit step event
            self.engine.ingest([make_event(
                source="workflow_engine",
                name="step_execution",
                attributes={
                    "workflow_id": self.workflow_id,
                    "workflow_run_id": run_id,
                    "step_name": step_name,
                    "step_id": f"{run_id}_step_{step_order}",
                    "step_order": step_order,
                    "status": status.value,
                    "latency_ms": latency_ms,
                    "error_type": error_type,
                    "error_message": error_message,
                },
            )])

            step_order += 1

            # Stop on failure
            if status == StepStatus.FAILURE:
                break

    def _extract(self, run_id):
        time.sleep(0.5)  # Simulate work

    def _transform(self, run_id):
        time.sleep(2.0)  # Simulate work

    def _validate(self, run_id):
        time.sleep(0.3)  # Simulate work

    def _load(self, run_id):
        time.sleep(1.0)  # Simulate work
```

### Step 2: Setup Workflow-Aware Engine

```python
# workflow_setup.py
from autoflow.workflow import WorkflowAwareGraphBuilder
from autoflow.workflow.rules import FailingStepRule, SlowStepRule, ErrorPropagationRule

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=".autoflow_workspace/autoflow.db"),
    graph_builder=WorkflowAwareGraphBuilder(),  # Workflow-aware!
    decision_graph=DecisionGraph(rules=[
        FailingStepRule(
            workflow_id="etl_pipeline",
            failure_threshold=0.10,  # 10% failure rate
        ),
        SlowStepRule(
            workflow_id="etl_pipeline",
            slowness_threshold_ms=1500,  # P95 > 1.5s
        ),
        ErrorPropagationRule(
            workflow_id="etl_pipeline",
            cascade_threshold=2,  # 2+ downstream failures
        ),
    ]),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(
            allowed_paths_prefixes=("config/",),
            max_risk=RiskLevel.LOW,
        ),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)
```

### Step 3: Run Workflow and Analyze

```python
# main.py
from etl_pipeline import ETLPipeline
from workflow_setup import engine
from autoflow.workflow import WorkflowQueryHelpers
from autoflow.workflow import (
    step_success_rate,
    step_failure_rate,
    step_latency_stats,
    workflow_bottlenecks,
)

# Create pipeline
pipeline = ETLPipeline(engine)

# Run multiple times
for i in range(50):
    run_id = f"run_{i:03d}"
    pipeline.run(run_id)

# Analyze results
nodes = engine.store.query_nodes("workflow_step")
edges = engine.store.query_edges()

q = WorkflowQueryHelpers()

# Get metrics
print("=== Workflow Metrics ===")
print(f"Total runs: {len(q.group_by_workflow_run(nodes))}")

# Step success rates
for step_name in ["extract", "transform", "validate", "load"]:
    success_rate = step_success_rate(nodes, workflow_id="etl_pipeline", step_name=step_name)
    latency = step_latency_stats(nodes, workflow_id="etl_pipeline", step_name=step_name)
    print(f"{step_name}:")
    print(f"  Success rate: {success_rate:.1%}")
    print(f"  P95 latency: {latency['p95']:.0f}ms")

# Bottlenecks
bottlenecks = workflow_bottlenecks(nodes, workflow_id="etl_pipeline")
print(f"\nBottlenecks:")
for b in bottlenecks[:3]:
    print(f"  {b['step_name']}: {b['avg_latency_ms']:.0f}ms avg")

# Generate proposals
proposals = engine.propose_with_edges()  # Use edges for workflow rules

print(f"\n=== Proposals ===")
for proposal in proposals:
    print(f"\n{proposal.title}")
    print(f"  {proposal.description}")
    print(f"  Risk: {proposal.risk}")
```

---

## Example 4: Prompt Engineering

**Scenario:** Automatically improve LLM prompts based on quality metrics.

### Step 1: Track Prompt Performance

```python
# llm_wrapper.py
from autoflow.observe.events import make_event
import time

class LLMWrapper:
    def __init__(self, api_client, engine: AutoImproveEngine):
        self.client = api_client
        self.engine = engine

    def complete(self, prompt_name: str, prompt: str, **kwargs):
        start = time.time()

        try:
            # Call LLM
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            latency_ms = (time.time() - start) * 1000

            # Get metrics
            completion = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_usd = (tokens_used / 1000) * 0.03  # GPT-4 pricing

            # Emit event
            self.engine.ingest([make_event(
                source="llm_wrapper",
                name="prompt_execution",
                attributes={
                    "prompt_name": prompt_name,
                    "model": "gpt-4",
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd,
                    "success": True,
                },
            )])

            return completion

        except Exception as e:
            latency_ms = (time.time() - start) * 1000

            # Emit error event
            self.engine.ingest([make_event(
                source="llm_wrapper",
                name="prompt_execution",
                attributes={
                    "prompt_name": prompt_name,
                    "model": "gpt-4",
                    "latency_ms": latency_ms,
                    "success": False,
                    "error_type": type(e).__name__,
                },
            )])

            raise
```

### Step 2: Track Quality Scores

```python
# quality_tracker.py
from autoflow.observe.events import make_event

class QualityTracker:
    def __init__(self, engine: AutoImproveEngine):
        self.engine = engine

    def score_output(self, prompt_name: str, output: str, score: float, reason: str = ""):
        """Score LLM output (0.0 - 1.0)."""

        # Emit quality event
        self.engine.ingest([make_event(
            source="quality_tracker",
            name="quality_score",
            attributes={
                "prompt_name": prompt_name,
                "quality_score": score,
                "reason": reason,
            },
        )])
```

### Step 3: Create Prompt Optimization Rule

```python
# prompt_rules.py
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from uuid import uuid4

class LowQualityPromptRule:
    """Detects low-scoring prompts and proposes improvements."""

    def __init__(self, prompt_name: str, quality_threshold: float = 0.7):
        self.prompt_name = prompt_name
        self.quality_threshold = quality_threshold

    def propose(self, nodes):
        proposals = []

        # Filter quality scores for this prompt
        quality_events = [
            n for n in nodes
            if n.properties.get("source") == "quality_tracker"
            and n.properties.get("prompt_name") == self.prompt_name
        ]

        if not quality_events:
            return proposals

        # Calculate average quality
        scores = [n.properties.get("quality_score", 0) for n in quality_events]
        avg_quality = sum(scores) / len(scores)

        # If quality is below threshold, propose improvement
        if avg_quality < self.quality_threshold:
            proposals.append(ChangeProposal(
                proposal_id=str(uuid4()),
                kind=ProposalKind.TEXT_PATCH,
                title=f"Improve prompt '{self.prompt_name}'",
                description=f"Average quality is {avg_quality:.2%} (threshold: {self.quality_threshold:.2%})",
                risk=RiskLevel.LOW,
                target_paths=(f"prompts/{self.prompt_name}.txt",),
                payload={
                    "patch": f"""
--- a/prompts/{self.prompt_name}.txt
+++ b/prompts/{self.prompt_name}.txt
@@ -1,1 +1,2 @@
-Current prompt text
+Improved prompt text with clearer instructions
""",
                    "format": "unified",
                },
            ))

        return proposals
```

### Step 4: Run and Improve

```python
# main.py
from llm_wrapper import LLMWrapper
from quality_tracker import QualityTracker
from prompt_rules import LowQualityPromptRule

# Setup
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=".autoflow_workspace/autoflow.db"),
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(rules=[
        LowQualityPromptRule(prompt_name="summarization", quality_threshold=0.75),
        LowQualityPromptRule(prompt_name="qa", quality_threshold=0.80),
    ]),
    evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
    applier=ProposalApplier(
        policy=ApplyPolicy(
            allowed_paths_prefixes=("prompts/",),
            max_risk=RiskLevel.LOW,
        ),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)

llm = LLMWrapper(openai_client, engine)
quality = QualityTracker(engine)

# Run multiple iterations
for i in range(20):
    # Generate completion
    summary = llm.complete("summarization", "Summarize this text...")

    # Score quality
    quality.score_output("summarization", summary, score=0.6 + (i * 0.02))

    # Check for improvements every 5 iterations
    if i % 5 == 0:
        proposals = engine.propose()
        for proposal in proposals:
            result = engine.evaluator.evaluate(proposal)
            if result.passed:
                print(f"Applying: {proposal.title}")
                engine.applier.apply(proposal)
```

---

## Example 5: Database Performance

**Scenario:** Detect slow queries and propose optimizations.

### Step 1: Instrument Database Queries

```python
# db_wrapper.py
import time
from autoflow.observe.events import make_event

class DatabaseWrapper:
    def __init__(self, connection, engine: AutoImproveEngine):
        self.conn = connection
        self.engine = engine

    def execute(self, query: str, params=None):
        start = time.time()

        try:
            cursor = self.conn.execute(query, params or [])
            rows = cursor.fetchall()
            latency_ms = (time.time() - start) * 1000

            # Emit event
            self.engine.ingest([make_event(
                source="database",
                name="query_executed",
                attributes={
                    "query": query,
                    "latency_ms": latency_ms,
                    "rows_returned": len(rows),
                    "success": True,
                },
            )])

            return rows

        except Exception as e:
            latency_ms = (time.time() - start) * 1000

            # Emit error event
            self.engine.ingest([make_event(
                source="database",
                name="query_failed",
                attributes={
                    "query": query,
                    "latency_ms": latency_ms,
                    "error_type": type(e).__name__,
                    "success": False,
                },
            )])

            raise
```

### Step 2: Create Slow Query Rule

```python
# db_rules.py
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from uuid import uuid4

class SlowQueryRule:
    """Detects slow queries and proposes optimizations."""

    def __init__(self, latency_threshold_ms: float = 1000):
        self.latency_threshold = latency_threshold_ms

    def propose(self, nodes):
        proposals = []

        # Filter query events
        queries = [
            n for n in nodes
            if n.properties.get("source") == "database"
            and n.properties.get("success") == True
        ]

        if not queries:
            return proposals

        # Find slow queries
        slow_queries = [
            n for n in queries
            if n.properties.get("latency_ms", 0) > self.latency_threshold
        ]

        if slow_queries:
            # Group by query pattern
            from collections import defaultdict
            query_patterns = defaultdict(list)

            for q in slow_queries:
                # Extract table name (simple pattern)
                query = q.properties.get("query", "")
                if "FROM" in query:
                    table = query.split("FROM")[1].split()[0]
                    query_patterns[table].append(q)

            # Propose indexes for slow tables
            for table, table_queries in query_patterns.items():
                avg_latency = sum(
                    q.properties.get("latency_ms", 0)
                    for q in table_queries
                ) / len(table_queries)

                proposals.append(ChangeProposal(
                    proposal_id=str(uuid4()),
                    kind=ProposalKind.CONFIG_EDIT,
                    title=f"Add index for table '{table}'",
                    description=f"Queries on {table} average {avg_latency:.0f}ms (threshold: {self.latency_threshold}ms)",
                    risk=RiskLevel.LOW,
                    target_paths=("migrations/add_indexes.sql",),
                    payload={
                        "table": table,
                        "operation": "create_index",
                        "sql": f"CREATE INDEX idx_{table}_created_at ON {table}(created_at);",
                    },
                ))

        return proposals
```

---

## Example 6: Custom Extension

**Scenario:** Extend AutoFlow with a custom graph store and evaluator.

### Custom Graph Store: MongoDB

```python
# mongo_store.py
from pymongo import MongoClient
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge
import json

class MongoGraphStore:
    """MongoDB-backed graph store."""

    def __init__(self, connection_string: str, database: str = "autoflow"):
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.nodes = self.db.nodes
        self.edges = self.db.edges

    def upsert(self, delta: ContextGraphDelta) -> None:
        for node in delta.nodes:
            self.nodes.update_one(
                {"node_id": node.node_id},
                {
                    "$set": {
                        "node_type": node.node_type,
                        "properties": node.properties,
                    }
                },
                upsert=True,
            )

        for edge in delta.edges:
            self.edges.update_one(
                {
                    "from_node_id": edge.from_node_id,
                    "to_node_id": edge.to_node_id,
                    "edge_type": edge.edge_type,
                },
                {
                    "$set": {
                        "properties": edge.properties,
                    }
                },
                upsert=True,
            )

    def query_nodes(self, node_type=None, limit=100):
        query = {}
        if node_type:
            query["node_type"] = node_type

        cursor = self.nodes.find(query).limit(limit)
        return [
            GraphNode(
                node_id=doc["node_id"],
                node_type=doc["node_type"],
                properties=doc["properties"],
            )
            for doc in cursor
        ]

    def query_edges(self, edge_type=None, limit=100):
        query = {}
        if edge_type:
            query["edge_type"] = edge_type

        cursor = self.edges.find(query).limit(limit)
        return [
            GraphEdge(
                edge_type=doc["edge_type"],
                from_node_id=doc["from_node_id"],
                to_node_id=doc["to_node_id"],
                properties=doc["properties"],
            )
            for doc in cursor
        ]
```

### Custom Evaluator: External API

```python
# external_evaluator.py
import requests
from autoflow.types import ChangeProposal, EvaluationResult

class ExternalAPIEvaluator:
    """Delegate evaluation to external API service."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        response = requests.post(
            f"{self.api_url}/evaluate",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "proposal_id": proposal.proposal_id,
                "title": proposal.title,
                "description": proposal.description,
                "kind": proposal.kind,
                "risk": proposal.risk,
                "target_paths": list(proposal.target_paths),
                "payload": proposal.payload,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=data["passed"],
            score=data.get("score", 1.0),
            metrics=data.get("metrics", {}),
            notes=data.get("notes", ""),
        )
```

### Use Custom Extensions

```python
# custom_setup.py
from mongo_store import MongoGraphStore
from external_evaluator import ExternalAPIEvaluator

engine = AutoImproveEngine(
    store=MongoGraphStore(
        connection_string="mongodb://localhost:27017",
        database="autoflow",
    ),
    graph_builder=ContextGraphBuilder(),
    decision_graph=DecisionGraph(rules=[...]),
    evaluator=ExternalAPIEvaluator(
        api_url="https://evaluator.example.com",
        api_key="your-api-key",
    ),
    applier=ProposalApplier(
        policy=ApplyPolicy(
            allowed_paths_prefixes=("config/",),
            max_risk=RiskLevel.LOW,
        ),
        backend=GitApplyBackend(repo_path=Path(".")),
    ),
)
```

---

## See Also

- [Overview](overview.md) - Quick start guide
- [Observation Events](observation_events.md) - Creating events
- [Context Graph](context_graph.md) - Graph building
- [Decision Graph](decision_graph.md) - Creating rules
- [Workflow Module](workflow.md) - Workflow examples
- [Extension Guide](extension_guide.md) - Extending AutoFlow
