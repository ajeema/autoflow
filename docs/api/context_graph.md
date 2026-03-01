# Context Graph API

## Overview

The Context Graph is a graph-based representation of your system's events and their relationships. It stores:

- **Nodes** - Represent events, steps, metrics, or any entity
- **Edges** - Represent relationships between nodes (flow, causality, dependencies)

---

## Core Types

### GraphNode

```python
@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    properties: Mapping[str, Any]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | `str` | Unique identifier for the node |
| `node_type` | `str` | Type/category of the node (e.g., "workflow_step", "metric") |
| `properties` | `Mapping[str, Any]` | Arbitrary key-value pairs with node data |

### GraphEdge

```python
@dataclass(frozen=True)
class GraphEdge:
    edge_type: str
    from_node_id: str
    to_node_id: str
    properties: Mapping[str, Any]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `edge_type` | `str` | Type of relationship (e.g., "next_step", "depends_on", "caused_by") |
| `from_node_id` | `str` | Source node ID |
| `to_node_id` | `str` | Target node ID |
| `properties` | `Mapping[str, Any]` | Edge metadata |

### ContextGraphDelta

```python
@dataclass(frozen=True)
class ContextGraphDelta:
    nodes: Sequence[GraphNode]
    edges: Sequence[GraphEdge]
```

Represents a set of changes to apply to the graph.

---

## Building Context Graphs

### Basic ContextGraphBuilder

```python
from autoflow.graph.context_graph import ContextGraphBuilder

builder = ContextGraphBuilder()

# Build from events
delta = builder.build_delta(events)

print(f"Created {len(delta.nodes)} nodes")
print(f"Created {len(delta.edges)} edges")
```

The basic builder creates simple nodes from events, without edges.

### Workflow-Aware Graph Builder

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

See [Workflow Module](workflow.md) for details.

### Custom Graph Builder

```python
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge

class MyCustomBuilder(ContextGraphBuilder):
    """Custom builder that adds external data."""

    def __init__(self, external_api_client):
        self.external_api = external_api_client

    def build_delta(self, events):
        # Build base graph
        nodes = []
        edges = []

        for event in events:
            # Create node
            node = GraphNode(
                node_id=f"node:{event.event_id}",
                node_type="custom_event",
                properties={
                    "event_name": event.name,
                    "source": event.source,
                    **event.attributes,
                },
            )
            nodes.append(node)

            # ENHANCE: Add external data
            if "user_id" in event.attributes:
                user = self.external_api.get_user(event.attributes["user_id"])
                # Create enriched node
                enriched_node = GraphNode(
                    node_id=f"enriched:{event.event_id}",
                    node_type="enriched_event",
                    properties={
                        **event.attributes,
                        "user_tier": user.tier,
                        "user_region": user.region,
                    },
                )
                nodes.append(enriched_node)

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

---

## Storing Context Graphs

### ContextGraphStore Protocol

```python
from typing import Protocol, Sequence, Optional

class ContextGraphStore(Protocol):
    def upsert(self, delta: ContextGraphDelta) -> None: ...
    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]: ...
    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]: ...
```

### SQLite Graph Store

```python
from autoflow.graph.sqlite_store import SQLiteGraphStore

# Create store
store = SQLiteGraphStore(db_path="autoflow.db")

# Upsert (add/update) nodes and edges
store.upsert(delta)

# Query nodes
all_nodes = store.query_nodes(limit=1000)
workflow_nodes = store.query_nodes(node_type="workflow_step", limit=100)

# Query edges
all_edges = store.query_edges(limit=1000)
causality_edges = store.query_edges(edge_type="caused_by", limit=100)
```

---

## Querying the Graph

### Basic Queries

```python
# Get all nodes
nodes = store.query_nodes()

# Filter by type
workflow_steps = store.query_nodes(node_type="workflow_step")

# Limit results
recent_nodes = store.query_nodes(limit=10)

# Get edges
edges = store.query_edges()

# Filter by edge type
causality_edges = store.query_edges(edge_type="caused_by")
```

### Using Workflow Query Helpers

```python
from autoflow.workflow import WorkflowQueryHelpers

q = WorkflowQueryHelpers()

# Filter by workflow
pipeline_nodes = q.filter_by_workflow(all_nodes, "my_pipeline")

# Filter by step
extract_nodes = q.filter_by_step(all_nodes, "extract")

# Filter by status
failed_nodes = q.filter_by_status(all_nodes, "failure")

# Group by step name
steps = q.group_by_step(nodes)

# Group by workflow run
runs = q.group_by_workflow_run(nodes)

# Get status breakdown
status_counts = q.count_by_status(nodes)
```

---

## Custom Graph Stores

### PostgreSQL Graph Store

```python
import psycopg
from psycopg_pool import ConnectionPool
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge

class PostgresGraphStore:
    """PostgreSQL-backed graph store."""

    def __init__(self, connection_string: str):
        self.pool = ConnectionPool(connection_string)
        self._init_tables()

    def _init_tables(self):
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        node_id TEXT PRIMARY KEY,
                        node_type TEXT NOT NULL,
                        properties JSONB NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS edges (
                        edge_id TEXT PRIMARY KEY,
                        edge_type TEXT NOT NULL,
                        from_node_id TEXT NOT NULL,
                        to_node_id TEXT NOT NULL,
                        properties JSONB NOT NULL,
                        FOREIGN KEY (from_node_id) REFERENCES nodes(node_id),
                        FOREIGN KEY (to_node_id) REFERENCES nodes(node_id)
                    )
                """)
                conn.commit()

    def upsert(self, delta: ContextGraphDelta) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for node in delta.nodes:
                    cur.execute("""
                        INSERT INTO nodes (node_id, node_type, properties)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (node_id)
                        DO UPDATE SET
                            node_type = EXCLUDED.node_type,
                            properties = EXCLUDED.properties
                    """, (node.node_id, node.node_type, json.dumps(node.properties)))

                for edge in delta.edges:
                    edge_id = f"{edge.from_node_id}->{edge.to_node_id}"
                    cur.execute("""
                        INSERT INTO edges (edge_id, edge_type, from_node_id, to_node_id, properties)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (edge_id)
                        DO UPDATE SET
                            edge_type = EXCLUDED.edge_type,
                            properties = EXCLUDED.properties
                    """, (edge_id, edge.edge_type, edge.from_node_id, edge.to_node_id,
                          json.dumps(edge.properties)))

                conn.commit()

    def query_nodes(self, node_type=None, limit=100):
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                if node_type:
                    cur.execute("""
                        SELECT node_id, node_type, properties
                        FROM nodes
                        WHERE node_type = %s
                        LIMIT %s
                    """, (node_type, limit))
                else:
                    cur.execute("""
                        SELECT node_id, node_type, properties
                        FROM nodes
                        LIMIT %s
                    """, (limit,))

                rows = cur.fetchall()
                return [
                    GraphNode(node_id=r[0], node_type=r[1], properties=json.loads(r[2]))
                    for r in rows
                ]

    def query_edges(self, edge_type=None, limit=100):
        # Similar implementation
        ...
```

### Neo4j Graph Store

```python
from neo4j import GraphDatabase

class Neo4jGraphStore:
    """Neo4j-backed graph store for graph queries."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def upsert(self, delta: ContextGraphDelta) -> None:
        with self.driver.session() as session:
            for node in delta.nodes:
                session.run(
                    "MERGE (n:Node {id: $id, type: $type, props: $props})",
                    id=node.node_id,
                    type=node.node_type,
                    props=json.dumps(node.properties),
                )

            for edge in delta.edges:
                session.run("""
                    MATCH (from:Node {id: $from_id}),
                           (to:Node {id: $to_id})
                    MERGE (from)-[r:RELATIONSHIP {type: $type, props: $props}]->(to)
                """, from_id=edge.from_node_id, to_id=edge.to_node_id,
                    type=edge.edge_type, props=json.dumps(edge.properties))

    def query_nodes(self, node_type=None, limit=100):
        with self.driver.session() as session:
            if node_type:
                result = session.run(
                    "MATCH (n:Node {type: $type}) RETURN n LIMIT $limit",
                    type=node_type, limit=limit,
                )
            else:
                result = session.run("MATCH (n:Node) RETURN n LIMIT $limit", limit=limit)

            return [
                GraphNode(
                    node_id=record["n"]["id"],
                    node_type=record["n"]["type"],
                    properties=record["n"]["props"],
                )
                for record in result
            ]
```

---

## Graph Query Examples

### Find All Failed Steps

```python
from autoflow.workflow import WorkflowQueryHelpers

q = WorkflowQueryHelpers()
nodes = store.query_nodes("workflow_step", limit=1000)

failed_nodes = q.filter_by_status(nodes, "failure")

for node in failed_nodes:
    print(f"Step: {node.properties.get('step_name')}")
    print(f"Error: {node.properties.get('error_type')}")
```

### Find Error Propagation Chains

```python
edges = store.query_edges("caused_by", limit=100)
nodes = store.query_nodes("workflow_step", limit=1000)

propagations = q.find_error_propagation(nodes, edges)

for prop in propagations:
    print(f"{prop['from_step']} failed → caused {prop['to_step']} to {prop['to_status']}")
```

### Trace a Workflow Run

```python
run_id = "pipeline_run_123"

nodes = store.query_nodes("workflow_step", limit=1000)
path = q.trace_execution_path(nodes, run_id)

for step_info in path:
    print(f"{step_info['step_order']}. {step_info['step_name']}")
    print(f"   Status: {step_info['status']}")
    print(f"   Latency: {step_info['latency_ms']}ms")
```

### Graph Traversal

```python
# Build adjacency list for traversal
edges = store.query_edges(limit=1000)
nodes = store.query_nodes(limit=1000)

adjacency = {}
for edge in edges:
    if edge.from_node_id not in adjacency:
        adjacency[edge.from_node_id] = []
    adjacency[edge.from_node_id].append(edge.to_node_id)

# BFS traversal
def find_connected(start_node_id, max_depth=3):
    visited = set()
    queue = [(start_node_id, 0)]

    while queue:
        node_id, depth = queue.pop(0)

        if node_id in visited or depth >= max_depth:
            continue

        visited.add(node_id)

        # Get neighbors
        for neighbor_id in adjacency.get(node_id, []):
            queue.append((neighbor_id, depth + 1))

    return visited
```

---

## Extending the Context Graph

### Adding Custom Node Types

```python
class MetricsGraphBuilder:
    """Builder that adds metric nodes to the graph."""

    def build_delta(self, events):
        nodes = []
        edges = []

        # Create standard event nodes
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

        # ADD: Create metric summary nodes
        # Group by source and create summary nodes
        from collections import Counter
        source_counts = Counter(e.source for e in events)

        for source, count in source_counts.items():
            nodes.append(GraphNode(
                node_id=f"metric:{source}_count",
                node_type="metric_summary",
                properties={
                    "metric_name": f"{source}_event_count",
                    "value": count,
                },
            ))

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

### Adding Custom Edge Types

```python
class CausalityGraphBuilder:
    """Builder that adds custom causal relationships."""

    def build_delta(self, events):
        nodes = []
        edges = []

        # Create nodes from events
        for i, event in enumerate(events):
            node = GraphNode(
                node_id=f"event:{i}",
                node_type="event",
                properties=dict(event.attributes),
            )
            nodes.append(node)

        # ADD: Create temporal edges (events that happen close in time)
        for i in range(len(events) - 1):
            time_diff = (
                events[i + 1].timestamp - events[i].timestamp
            ).total_seconds()

            # If events happen within 1 second, link them
            if time_diff < 1.0:
                edges.append(GraphEdge(
                    edge_type="co_occurred",
                    from_node_id=f"event:{i}",
                    to_node_id=f"event:{i + 1}",
                    properties={
                        "time_diff_ms": time_diff * 1000,
                    },
                ))

        return ContextGraphDelta(nodes=nodes, edges=edges)
```

---

## API Reference

### ContextGraphBuilder

```python
class ContextGraphBuilder:
    def build_delta(self, events: Sequence[ObservationEvent]) -> ContextGraphDelta:
        """Build graph delta from events.

        Args:
            events: Sequence of observation events

        Returns:
            ContextGraphDelta with nodes (no edges)
        """
```

### ContextGraphStore Protocol

```python
class ContextGraphStore(Protocol):
    def upsert(self, delta: ContextGraphDelta) -> None:
        """Add/update nodes and edges in the graph."""

    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        """Query nodes from the graph."""

    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        """Query edges from the graph."""
```

### SQLiteGraphStore

```python
class SQLiteGraphStore:
    def __init__(self, db_path: str) -> None:
        """Initialize SQLite-based graph store.

        Args:
            db_path: Path to SQLite database file
        """

    def upsert(self, delta: ContextGraphDelta) -> None:
        """Store nodes and edges in SQLite."""

    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        """Query nodes from SQLite."""

    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        """Query edges from SQLite."""
```

---

## See Also

- [Observation Events API](observation_events.md) - Creating events that become nodes
- [Decision Graph API](decision_graph.md) - Analyzing the graph
- [Workflow Module](workflow.md) - Workflow-specific graph operations
- [Extension Guide](extension_guide.md) - Custom graph builders and stores
