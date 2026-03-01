# Extension Guide

## Overview

AutoFlow is designed to be **extensible at every layer**. This guide shows you how to customize and extend AutoFlow for your specific needs.

---

## Extension Points

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                         │
│                  (emits ObservationEvent)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Custom Event Sources                       │
│  - Database collectors                                       │
│  - API monitors                                              │
│  - Message queue consumers                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Custom Graph Builders                          │
│  - Enrich events with external data                         │
│  - Create custom node types                                 │
│  - Create custom edge relationships                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Custom Graph Stores                            │
│  - PostgreSQL, Neo4j, Redis                                 │
│  - Custom query interfaces                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Custom Decision Rules                        │
│  - Domain-specific proposal logic                           │
│  - ML-powered detectors                                     │
│  - Time-series analysis                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Custom Evaluators                             │
│  - Domain-specific validation                               │
│  - External service integration                              │
│  - Semantic analysis                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Custom Apply Backends                        │
│  - Git, PR, filesystem, Kubernetes                          │
│  - Manual approval workflows                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Custom Event Sources

### Pattern 1: Database Poller

```python
class DatabaseEventCollector:
    """Collect events from database queries."""

    def __init__(self, db_connection, poll_interval_seconds=60):
        self.db = db_connection
        self.poll_interval = poll_interval_seconds
        self.last_check = datetime.now()

    def collect_events(self) -> list[ObservationEvent]:
        """Poll database for new records and create events."""

        rows = self.db.execute("""
            SELECT
                id,
                table_name,
                operation,
                timestamp,
                user_id
            FROM audit_log
            WHERE timestamp > ?
            ORDER BY timestamp
            LIMIT 1000
        """, (self.last_check,)).fetchall()

        events = []
        for row in rows:
            events.append(make_event(
                source="database",
                name="record_changed",
                attributes={
                    "table": row["table_name"],
                    "operation": row["operation"],
                    "user_id": row["user_id"],
                },
            ))

        # Update last check
        if rows:
            self.last_check = max(row["timestamp"] for row in rows)

        return events

# Usage
import time

collector = DatabaseEventCollector(db_conn)

while True:
    events = collector.collect_events()
    if events:
        engine.ingest(events)
    time.sleep(collector.poll_interval)
```

### Pattern 2: API Monitor

```python
import requests
from autoflow.observe.events import make_event

class APIHealthMonitor:
    """Monitor API health and create events."""

    def __init__(self, api_endpoints: list[str]):
        self.endpoints = api_endpoints

    def check_endpoints(self) -> list[ObservationEvent]:
        events = []

        for endpoint in self.endpoints:
            try:
                start = time.time()
                response = requests.get(endpoint, timeout=10)
                latency_ms = (time.time() - start) * 1000

                events.append(make_event(
                    source="api_monitor",
                    name="health_check",
                    attributes={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "healthy": response.status_code == 200,
                    },
                ))

            except Exception as e:
                events.append(make_event(
                    source="api_monitor",
                    name="health_check_failed",
                    attributes={
                        "endpoint": endpoint,
                        "error": str(e),
                        "healthy": False,
                    },
                ))

        return events
```

### Pattern 3: Kafka Consumer

```python
from kafka import KafkaConsumer
import json

class KafkaEventSource:
    """Consume events from Kafka and convert to AutoFlow events."""

    def __init__(self, bootstrap_servers: str, topic: str):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        )

    def consume_events(self, timeout_ms=1000) -> list[ObservationEvent]:
        events = []

        for message in self.consumer:
            data = message.value

            # Convert Kafka message to AutoFlow event
            events.append(make_event(
                source=data.get("source", "kafka"),
                name=data.get("event_type", "unknown"),
                attributes=data.get("attributes", {}),
            ))

            # Timeout after collecting some
            if len(events) >= 100:
                break

        return events
```

---

## 2. Custom Graph Builders

### Pattern 1: Enrichment Builder

```python
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge

class EnrichmentGraphBuilder(ContextGraphBuilder):
    """Builder that enriches events with external data."""

    def __init__(self, user_service_client, product_service_client):
        self.user_service = user_service_client
        self.product_service = product_service_client

    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        nodes = []
        edges = []

        for event in events:
            # Create standard node
            node = GraphNode(
                node_id=f"event:{event.event_id}",
                node_type="event",
                properties={
                    "name": event.name,
                    "source": event.source,
                    **event.attributes,
                },
            )
            nodes.append(node)

            # ENRICH: Add user data if user_id present
            if "user_id" in event.attributes:
                user = self.user_service.get_user(event.attributes["user_id"])

                enriched_node = GraphNode(
                    node_id=f"user:{event.attributes['user_id']}",
                    node_type="user_profile",
                    properties={
                        "user_id": user.id,
                        "tier": user.tier,
                        "region": user.region,
                        "signup_date": user.created_at.isoformat(),
                    },
                )
                nodes.append(enriched_node)

                # Create edge: event -> user
                edges.append(GraphEdge(
                    edge_type="attributed_to",
                    from_node_id=node.node_id,
                    to_node_id=enriched_node.node_id,
                    properties={},
                ))

            # ENRICH: Add product data if product_id present
            if "product_id" in event.attributes:
                product = self.product_service.get_product(event.attributes["product_id"])

                product_node = GraphNode(
                    node_id=f"product:{event.attributes['product_id']}",
                    node_type="product",
                    properties={
                        "product_id": product.id,
                        "category": product.category,
                        "price": product.price,
                    },
                )
                nodes.append(product_node)

                edges.append(GraphEdge(
                    edge_type="references",
                    from_node_id=node.node_id,
                    to_node_id=product_node.node_id,
                    properties={},
                ))

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

### Pattern 2: Aggregation Builder

```python
class AggregationGraphBuilder(ContextGraphBuilder):
    """Builder that creates summary/aggregated nodes."""

    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        nodes = []
        edges = []

        # Create individual event nodes
        for event in events:
            nodes.append(GraphNode(
                node_id=f"event:{event.event_id}",
                node_type="event",
                properties={
                    "name": event.name,
                    "source": event.source,
                    **event.attributes,
                },
            ))

        # CREATE: Aggregated metrics nodes
        from collections import Counter, defaultdict

        # Count by source
        source_counts = Counter(e.source for e in events)
        for source, count in source_counts.items():
            nodes.append(GraphNode(
                node_id=f"metric:source_count:{source}",
                node_type="metric",
                properties={
                    "metric_name": f"{source}_event_count",
                    "value": count,
                    "aggregation": "count",
                },
            ))

        # Average latency by source
        latencies = defaultdict(list)
        for event in events:
            if "latency_ms" in event.attributes:
                latencies[event.source].append(event.attributes["latency_ms"])

        for source, source_latencies in latencies.items():
            avg_latency = sum(source_latencies) / len(source_latencies)
            nodes.append(GraphNode(
                node_id=f"metric:avg_latency:{source}",
                node_type="metric",
                properties={
                    "metric_name": f"{source}_avg_latency_ms",
                    "value": avg_latency,
                    "aggregation": "average",
                },
            ))

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

### Pattern 3: Relationship Builder

```python
class RelationshipGraphBuilder(ContextGraphBuilder):
    """Builder that creates custom relationships between nodes."""

    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        nodes = []
        edges = []

        # Create nodes
        for i, event in enumerate(events):
            node = GraphNode(
                node_id=f"event:{i}",
                node_type="event",
                properties=dict(event.attributes),
            )
            nodes.append(node)

        # CREATE: Custom edges

        # 1. Temporal edges (events close in time)
        for i in range(len(events) - 1):
            time_diff = (events[i + 1].timestamp - events[i].timestamp).total_seconds()

            # If events happen within 5 seconds, link them
            if time_diff < 5.0:
                edges.append(GraphEdge(
                    edge_type="co_occurred",
                    from_node_id=f"event:{i}",
                    to_node_id=f"event:{i + 1}",
                    properties={"time_diff_seconds": time_diff},
                ))

        # 2. Same user edges
        user_events = {}
        for i, event in enumerate(events):
            user_id = event.attributes.get("user_id")
            if user_id:
                if user_id not in user_events:
                    user_events[user_id] = []
                user_events[user_id].append(i)

        for user_id, event_indices in user_events.items():
            for i in range(len(event_indices) - 1):
                edges.append(GraphEdge(
                    edge_type="same_user",
                    from_node_id=f"event:{event_indices[i]}",
                    to_node_id=f"event:{event_indices[i + 1]}",
                    properties={"user_id": user_id},
                ))

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

---

## 3. Custom Graph Stores

### Pattern 1: Redis Graph Store

```python
import redis
import json
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge

class RedisGraphStore:
    """Redis-backed graph store."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    def upsert(self, delta: ContextGraphDelta) -> None:
        pipe = self.redis.pipeline()

        # Store nodes
        for node in delta.nodes:
            key = f"node:{node.node_id}"
            pipe.hset(key, mapping={
                "node_type": node.node_type,
                "properties": json.dumps(node.properties),
            })

        # Store edges
        for edge in delta.edges:
            key = f"edge:{edge.from_node_id}:{edge.to_node_id}"
            pipe.hset(key, mapping={
                "edge_type": edge.edge_type,
                "properties": json.dumps(edge.properties),
            })

        pipe.execute()

    def query_nodes(self, node_type=None, limit=100):
        pattern = f"node:*" if node_type is None else f"node:*"

        keys = self.redis.scan_iter(match=pattern, count=limit)
        nodes = []

        for key in keys:
            data = self.redis.hgetall(key)

            # Filter by type if specified
            if node_type and data[b"node_type"].decode() != node_type:
                continue

            nodes.append(GraphNode(
                node_id=key.decode().split(":")[1],
                node_type=data[b"node_type"].decode(),
                properties=json.loads(data[b"properties"].decode()),
            ))

        return nodes

    def query_edges(self, edge_type=None, limit=100):
        pattern = f"edge:*"

        keys = self.redis.scan_iter(match=pattern, count=limit)
        edges = []

        for key in keys:
            data = self.redis.hgetall(key)

            # Filter by type if specified
            if edge_type and data[b"edge_type"].decode() != edge_type:
                continue

            # Parse key: from_node_id:to_node_id
            parts = key.decode().split(":")
            from_id, to_id = parts[1], parts[2]

            edges.append(GraphEdge(
                edge_type=data[b"edge_type"].decode(),
                from_node_id=from_id,
                to_node_id=to_id,
                properties=json.loads(data[b"properties"].decode()),
            ))

        return edges
```

### Pattern 2: Neo4j Graph Store

```python
from neo4j import GraphDatabase
import json

class Neo4jGraphStore:
    """Neo4j-backed graph store for complex queries."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def upsert(self, delta: ContextGraphDelta) -> None:
        with self.driver.session() as session:
            for node in delta.nodes:
                session.run(
                    "MERGE (n:Node {id: $id}) "
                    "SET n.type = $type, n.properties = $props",
                    id=node.node_id,
                    type=node.node_type,
                    props=json.dumps(node.properties),
                )

            for edge in delta.edges:
                session.run("""
                    MATCH (from:Node {id: $from_id})
                    MATCH (to:Node {id: $to_id})
                    MERGE (from)-[r:RELATIONSHIP]->(to)
                    SET r.type = $type, r.properties = $props
                """,
                    from_id=edge.from_node_id,
                    to_id=edge.to_node_id,
                    type=edge.edge_type,
                    props=json.dumps(edge.properties),
                )

    def query_nodes(self, node_type=None, limit=100):
        with self.driver.session() as session:
            if node_type:
                result = session.run(
                    "MATCH (n:Node {type: $type}) RETURN n LIMIT $limit",
                    type=node_type, limit=limit,
                )
            else:
                result = session.run("MATCH (n:Node) RETURN n LIMIT $limit", limit=limit)

            nodes = []
            for record in result:
                n = record["n"]
                nodes.append(GraphNode(
                    node_id=n["id"],
                    node_type=n["type"],
                    properties=json.loads(n["properties"]),
                ))

            return nodes

    def query_edges(self, edge_type=None, limit=100):
        with self.driver.session() as session:
            if edge_type:
                result = session.run("""
                    MATCH (from:Node)-[r:RELATIONSHIP {type: $type}]->(to:Node)
                    RETURN from.id as from_id, to.id as to_id, r
                    LIMIT $limit
                """, type=edge_type, limit=limit)
            else:
                result = session.run("""
                    MATCH (from:Node)-[r:RELATIONSHIP]->(to:Node)
                    RETURN from.id as from_id, to.id as to_id, r
                    LIMIT $limit
                """, limit=limit)

            edges = []
            for record in result:
                r = record["r"]
                edges.append(GraphEdge(
                    edge_type=r["type"],
                    from_node_id=record["from_id"],
                    to_node_id=record["to_id"],
                    properties=json.loads(r["properties"]),
                ))

            return edges
```

---

## 4. Custom Rules

### Pattern 1: ML-Powered Anomaly Detector

```python
import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetectionRule:
    """Rule that uses ML to detect anomalous patterns."""

    def __init__(self, model_path: str = None):
        if model_path:
            import joblib
            self.model = joblib.load(model_path)
        else:
            self.model = IsolationForest(contamination=0.1)

    def train(self, nodes: list[GraphNode]):
        """Train model on historical data."""
        features = self._extract_features(nodes)
        self.model.fit(features)

    def propose(self, nodes, edges=None):
        """Detect anomalies and propose investigations."""
        proposals = []

        # Extract features
        features = self._extract_features(nodes)

        # Predict anomalies
        predictions = self.model.predict(features)

        for i, (is_anomaly, feature) in enumerate(zip(predictions, features)):
            if is_anomaly == -1:  # Anomaly detected
                proposals.append(ChangeProposal(
                    proposal_id=str(uuid4()),
                    kind=ProposalKind.CONFIG_EDIT,
                    title="Investigate anomalous workflow run",
                    description=f"Anomalous pattern detected in run {feature.get('run_id')}",
                    risk=RiskLevel.LOW,
                    target_paths=("logs/anomalies.log",),
                    payload={
                        "run_id": feature.get("run_id"),
                        "investigation": "required",
                    },
                ))

        return proposals

    def _extract_features(self, nodes: list[GraphNode]) -> list[dict]:
        """Extract ML features from nodes."""
        # Group by run
        from collections import defaultdict

        runs = defaultdict(list)
        for node in nodes:
            run_id = node.properties.get("workflow_run_id")
            if run_id:
                runs[run_id].append(node)

        # Extract features per run
        features = []
        for run_id, run_nodes in runs.items():
            feature = {
                "run_id": run_id,
                "total_latency_ms": sum(
                    n.properties.get("latency_ms", 0)
                    for n in run_nodes
                ),
                "error_count": sum(
                    1 for n in run_nodes
                    if n.properties.get("status") == "failure"
                ),
                "step_count": len(run_nodes),
                "avg_step_latency": np.mean([
                    n.properties.get("latency_ms", 0)
                    for n in run_nodes
                ]),
            }
            features.append(feature)

        return features
```

### Pattern 2: Threshold-Based Rule

```python
class ThresholdRule:
    """Generic rule that triggers when metric exceeds threshold."""

    def __init__(
        self,
        metric_name: str,
        threshold: float,
        comparison: str = "greater_than",  # or "less_than"
        proposal_creator: callable = None,
    ):
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.proposal_creator = proposal_creator

    def propose(self, nodes, edges=None):
        proposals = []

        # Extract metric values
        values = [
            n.properties.get(self.metric_name, 0)
            for n in nodes
            if self.metric_name in n.properties
        ]

        if not values:
            return proposals

        # Check threshold
        if self.comparison == "greater_than":
            triggered = max(values) > self.threshold
            trigger_value = max(values)
        else:
            triggered = min(values) < self.threshold
            trigger_value = min(values)

        if triggered:
            if self.proposal_creator:
                proposals.append(self.proposal_creator(trigger_value))
            else:
                proposals.append(ChangeProposal(
                    proposal_id=str(uuid4()),
                    kind=ProposalKind.CONFIG_EDIT,
                    title=f"Threshold exceeded for {self.metric_name}",
                    description=f"{self.metric_name} is {trigger_value} (threshold: {self.threshold})",
                    risk=RiskLevel.LOW,
                    target_paths=("config/thresholds.yaml",),
                    payload={
                        "metric": self.metric_name,
                        "threshold": self.threshold,
                        "current_value": trigger_value,
                    },
                ))

        return proposals
```

---

## 5. Custom Evaluators

### Pattern 1: A/B Test Evaluator

```python
class ABTestEvaluator:
    """Evaluate proposals using A/B test methodology."""

    def __init__(self, min_sample_size=100):
        self.min_sample_size = min_sample_size

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        # Get baseline data (control group)
        control_metrics = self._get_control_metrics()

        # Simulate with proposal (treatment group)
        treatment_metrics = self._simulate_proposal(proposal)

        # Check sample size
        if len(control_metrics) < self.min_sample_size:
            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=False,
                score=0.0,
                notes=f"Insufficient sample size: {len(control_metrics)} < {self.min_sample_size}",
            )

        # Run statistical test
        from scipy import stats

        t_stat, p_value = stats.ttest_ind(control_metrics, treatment_metrics)

        # Pass if treatment is significantly better
        passed = p_value < 0.05 and np.mean(treatment_metrics) > np.mean(control_metrics)

        score = (np.mean(treatment_metrics) - np.mean(control_metrics)) / np.std(control_metrics)

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            score=score,
            metrics={
                "control_mean": np.mean(control_metrics),
                "treatment_mean": np.mean(treatment_metrics),
                "p_value": p_value,
            },
            notes=f"p-value: {p_value:.4f}, t-stat: {t_stat:.4f}",
        )
```

### Pattern 2: Cost-Benefit Evaluator

```python
class CostBenefitEvaluator:
    """Evaluate proposals based on cost-benefit analysis."""

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        # Estimate implementation cost
        impl_cost = self._estimate_implementation_cost(proposal)

        # Estimate benefit
        benefit = self._estimate_benefit(proposal)

        # Calculate ROI
        roi = (benefit - impl_cost) / impl_cost if impl_cost > 0 else 0

        # Pass if ROI > threshold
        passed = roi > 1.0  # Must break even or better
        score = min(roi / 5.0, 1.0)  # Normalize to 0-1 (5x ROI = 1.0)

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            score=score,
            metrics={
                "implementation_cost": impl_cost,
                "benefit": benefit,
                "roi": roi,
            },
            notes=f"ROI: {roi:.2f}x, Cost: ${impl_cost:.2f}, Benefit: ${benefit:.2f}",
        )
```

---

## 6. Custom Backends

### Pattern 1: Terraform Backend

```python
class TerraformBackend:
    """Apply proposals by updating Terraform configurations."""

    def __init__(self, tf_root: Path):
        self.tf_root = tf_root

    def apply(self, proposal: ChangeProposal) -> None:
        if proposal.kind == ProposalKind.CONFIG_EDIT:
            self._apply_terraform_change(proposal)
        else:
            raise ValueError(f"Unsupported kind: {proposal.kind}")

    def _apply_terraform_change(self, proposal: ChangeProposal) -> None:
        import hcl2

        for path in proposal.target_paths:
            tf_file = self.tf_root / path

            # Load Terraform file
            with open(tf_file) as f:
                tf_config = hcl2.load(f)

            # Apply change
            payload = proposal.payload
            if payload["op"] == "set":
                # Navigate to resource and set value
                resource_path = payload["path"].split(".")
                current = tf_config

                for key in resource_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                current[resource_path[-1]] = payload["value"]

            # Write back
            with open(tf_file, "w") as f:
                hcl2.dump(tf_config, f)

            # Run terraform apply
            import subprocess
            subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                cwd=self.tf_root,
                check=True,
            )

            print(f"[APPLY] Updated {path} via Terraform")
```

### Pattern 2: AWS SSM Backend

```python
import boto3

class AWSSSMBackend:
    """Apply proposals by updating AWS SSM Parameters."""

    def __init__(self, region: str = "us-east-1"):
        self.ssm = boto3.client("ssm", region_name=region)

    def apply(self, proposal: ChangeProposal) -> None:
        if proposal.kind != ProposalKind.CONFIG_EDIT:
            raise ValueError("Only CONFIG_EDIT supported")

        payload = proposal.payload

        if payload["op"] == "set":
            # Update SSM parameter
            self.ssm.put_parameter(
                Name=payload["path"],
                Value=str(payload["value"]),
                Type="String",
                Overwrite=True,
            )

            print(f"[APPLY] Updated SSM parameter {payload['path']}")
```

---

## Extension Best Practices

### DO ✅

**1. Use Protocols for Interfaces**

```python
from typing import Protocol

class CustomStore(Protocol):
    def upsert(self, delta: ContextGraphDelta) -> None: ...
    def query_nodes(self, node_type: Optional[str] = None) -> Sequence[GraphNode]: ...
```

**2. Add Logging**

```python
import logging

logger = logging.getLogger(__name__)

class CustomRule:
    def propose(self, nodes):
        logger.debug(f"Running rule on {len(nodes)} nodes")
        # ...
        logger.info(f"Generated {len(proposals)} proposals")
```

**3. Handle Errors Gracefully**

```python
class CustomBackend:
    def apply(self, proposal):
        try:
            self._apply_impl(proposal)
        except Exception as e:
            logger.error(f"Failed to apply {proposal.proposal_id}: {e}")
            raise ApplyError(f"Backend error: {e}")
```

**4. Write Tests**

```python
def test_custom_rule():
    rule = CustomRule()
    nodes = [GraphNode(...)]

    proposals = rule.propose(nodes)

    assert len(proposals) == 1
    assert proposals[0].risk == RiskLevel.LOW
```

### DON'T ❌

**1. Don't Break Existing APIs**

```python
# Avoid - changes signature
def propose(self, nodes: list, extra_param: str):  # ❌

# Good - maintains compatibility
def propose(self, nodes, edges=None):  # ✅
```

**2. Don't Hardcode Configuration**

```python
# Avoid
class CustomStore:
    def __init__(self):
        self.host = "localhost"  # ❌

# Good
class CustomStore:
    def __init__(self, host: str = "localhost"):  # ✅
        self.host = host
```

**3. Don't Ignore Performance**

```python
# Avoid - loads all data
def query_nodes(self):
    return self.load_all_nodes()  # ❌

# Good - paginates
def query_nodes(self, limit=100):  # ✅
    return self.load_nodes(limit)
```

---

## See Also

- [Context Graph API](context_graph.md) - Custom graph builders and stores
- [Decision Graph API](decision_graph.md) - Custom rules
- [Evaluation API](evaluation.md) - Custom evaluators
- [Apply API](apply.md) - Custom backends
- [Examples](examples.md) - Complete extension examples
