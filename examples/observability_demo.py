"""
Comprehensive observability demo for Context Graph Framework.

Demonstrates:
- Request context and correlation IDs
- Distributed tracing with spans
- Metrics collection and aggregation
- Health checks
- Alerting on thresholds
- Audit log querying and aggregation
- Prometheus export
"""

import time
from datetime import datetime, timedelta

from autoflow.context_graph.core import ContextGraph, Entity
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.security import SecurityConfig
from autoflow.context_graph.builders import brand

# Observability imports
from autoflow.context_graph.observability import (
    RequestContext,
    request_context,
    Span,
    MetricsRegistry,
    PerformanceTracker,
    HealthChecker,
    Alerter,
    format_prometheus_metrics,
    format_stats_dashboard,
    instrument,
    global_registry,
)

# Audit imports
from autoflow.context_graph.audit import (
    AuditEventType,
    Auditor,
    FileAuditBackend,
)

print("=" * 70)
print("Context Graph Framework - Observability Demo")
print("=" * 70)

# ============================================================================
# 1. Request Context and Correlation IDs
# ============================================================================
print("\n=== 1. Request Context and Correlation IDs ===\n")

with request_context(user_id="user123", metadata={"source": "api"}) as ctx:
    print(f"Request ID: {ctx.request_id}")
    print(f"Trace ID: {ctx.trace_id}")
    print(f"User ID: {ctx.user_id}")

    # Create nested spans
    span1 = ctx.create_span("entity_lookup", metadata={"entity_id": "brand:nike"})
    time.sleep(0.01)  # Simulate work
    span1.complete()

    span2 = ctx.create_span("traversal", metadata={"max_hops": 2})
    time.sleep(0.02)
    span2.complete()

    print(f"\nCreated {len(ctx._spans)} spans")
    print(f"Total duration: {ctx.get_duration_ms():.2f}ms")
    print(f"\nRequest context:")
    for key, value in ctx.to_dict().items():
        if key != "spans":
            print(f"  {key}: {value}")

# ============================================================================
# 2. Metrics Collection
# ============================================================================
print("\n=== 2. Metrics Collection ===\n")

registry = MetricsRegistry()

# Record some metrics
registry.counter("entities_created", tags={"type": "brand"})
registry.counter("entities_created", tags={"type": "campaign"})
registry.gauge("active_connections", 42, tags={"server": "api-1"})
registry.histogram("operation_duration_ms", 45.2, tags={"operation": "traverse"})
registry.histogram("operation_duration_ms", 78.5, tags={"operation": "traverse"})
registry.histogram("operation_duration_ms", 23.1, tags={"operation": "traverse"})

print("Counter:")
print(f"  entities_created: {registry.get_counter('entities_created')}")

print("\nGauge:")
print(f"  active_connections: {registry.get_gauge('active_connections')}")

print("\nHistogram stats:")
stats = registry.get_histogram_stats("operation_duration_ms")
print(f"  count: {stats['count']}")
print(f"  avg: {stats['avg']:.2f}ms")
print(f"  p50: {stats['p50']:.2f}ms")
print(f"  p95: {stats['p95']:.2f}ms")
print(f"  p99: {stats['p99']:.2f}ms")

# ============================================================================
# 3. Performance Tracking with Percentiles
# ============================================================================
print("\n=== 3. Performance Tracking ===\n")

tracker = PerformanceTracker(window_size_seconds=10)

# Record some operations
for i in range(10):
    duration = 50 + (i * 10) + (time.time() * 5 % 30)
    tracker.record("traversal", duration, success=(i % 4 != 0))

# Get stats
stats = tracker.get_stats("traversal")
print(f"Operation: traversal")
print(f"  count: {stats['count']}")
print(f"  ops/sec: {stats['operations_per_second']:.2f}")
print(f"  success_rate: {stats['success_rate']:.2%}")
print(f"\nDuration stats:")
d = stats["duration_ms"]
print(f"  avg: {d['avg']:.2f}ms")
print(f"  min: {d['min']:.2f}ms")
print(f"  max: {d['max']:.2f}ms")
print(f"  p50: {d['median']:.2f}ms")
print(f"  p95: {d['p95']:.2f}ms")
print(f"  p99: {d['p99']:.2f}ms")

# ============================================================================
# 4. Health Checks
# ============================================================================
print("\n=== 4. Health Checks ===\n")

health_checker = HealthChecker()

# Register some health checks
def check_graph():
    return {"healthy": True, "message": "Graph operational"}

def check_memory():
    return {"healthy": True, "message": "Memory OK", "metadata": {"usage_mb": 125}}

def check_slow_service():
    time.sleep(0.1)  # Simulate slowness
    return {"healthy": True, "message": "Slow but functional"}

health_checker.register("graph", check_graph)
health_checker.register("memory", check_memory)
health_checker.register("external_api", check_slow_service)

health = health_checker.check_health()
print(f"Overall status: {health.status}")
print(f"Duration: {health.duration_ms:.2f}ms")
for name, check in health.checks.items():
    print(f"  {name}: {check}")

# ============================================================================
# 5. Alerting on Thresholds
# ============================================================================
print("\n=== 5. Alerting ===\n")

alerter = Alerter()

# Add threshold rules
alerter.add_threshold_rule(
    metric_name="operation_duration_ms",
    threshold=100.0,
    comparison="gt",
    severity="warning",
    title_template="Slow operation detected",
    description_template="Operation took {value:.2f}ms (threshold: {threshold}ms)",
)

alerter.add_threshold_rule(
    metric_name="error_rate",
    threshold=0.1,  # 10%
    comparison="gt",
    severity="critical",
    title_template="High error rate",
    description_template="Error rate is {value:.1%} (threshold: {threshold:.1%})",
)

# Simulate metrics that trigger alerts
registry.histogram("operation_duration_ms", 150.0, tags={"operation": "traversal"})
registry.counter("error_rate", 0.15, tags={"operation": "query"})

alerts = alerter.check_rules(registry)
print(f"Generated {len(alerts)} alerts:")
for alert in alerts:
    print(f"  [{alert.severity.upper()}] {alert.title}")
    print(f"    {alert.description}")

# ============================================================================
# 6. Instrumentation Decorator
# ============================================================================
print("\n=== 6. Automatic Instrumentation ===\n")

# Create a tracker and registry for the decorator
instrument_tracker = PerformanceTracker()

# Create a class with instrumented methods
class InstrumentedGraph:
    def __init__(self):
        self.graph = ContextGraph(backend=InMemoryBackend())
        self.registry = MetricsRegistry()
        self.tracker = instrument_tracker

    @instrument(
        operation_name="get_entity",
        registry=global_registry,
        tracker=instrument_tracker,
    )
    def get_entity(self, entity_id: str):
        """Get an entity (auto-instrumented)."""
        entity = self.graph.get_entity(entity_id)
        return entity

    @instrument(operation_name="traverse")
    def traverse_slow(self, pattern):
        """Slow traversal (auto-instrumented)."""
        time.sleep(0.05)  # Simulate work
        return self.graph.traverse("entity:test", pattern)

# Use the instrumented class
igraph = InstrumentedGraph()

# These calls are automatically tracked
for i in range(3):
    if i == 1:
        try:
            igraph.get_entity("test")
        except:
            pass
    else:
        pass

print("Auto-instrumented operations tracked in metrics registry")

# ============================================================================
# 7. Audit Log Querying and Aggregation
# ============================================================================
print("\n=== 7. Audit Log Analysis ===\n")

# Create auditor with file backend
auditor = Auditor(
    backend=FileAuditBackend(filepath="/tmp/audit_observability.log"),
    enabled=True,
)

# Add some audit events
auditor.log(
    event_type=AuditEventType.ENTITY_READ,
    operation="read",
    user_id="user123",
    resource_id="brand:nike",
)

auditor.log(
    event_type=AuditEventType.GRAPH_TRAVERSE,
    operation="traverse",
    user_id="user123",
    resource_id="brand:nike",
    duration_ms=45.2,
)

auditor.log(
    event_type=AuditEventType.ENTITY_READ,
    operation="read",
    user_id="user456",
    resource_id="brand:adidas",
    success=False,
    error_message="Entity not found",
)

# Query by user
user_events = auditor.query_events(user_id="user123")
print(f"Events for user123: {len(user_events)}")

# Aggregate by user
user_stats = auditor.aggregate_by_user()
print(f"\nUser activity:")
for user_id, stats in list(user_stats.items())[:3]:
    print(f"  {user_id}:")
    print(f"    operations: {stats['total_operations']}")
    print(f"    success rate: {stats['successful_operations'] / stats['total_operations']:.2%}")

# Aggregate by operation
op_stats = auditor.aggregate_by_operation()
print(f"\nOperation stats:")
for op, stats in list(op_stats.items())[:3]:
    print(f"  {op}:")
    print(f"    count: {stats['total_count']}")
    print(f"    avg duration: {stats['avg_duration_ms']:.2f}ms")

# Export to Prometheus format
prometheus_file = "/tmp/audit_metrics.prom"
auditor.export_to_prometheus(prometheus_file)
print(f"\nExported metrics to {prometheus_file}")

# Show a few lines
with open(prometheus_file, "r") as f:
    lines = f.readlines()
    print("Prometheus metrics preview:")
    for line in lines[:5]:
        print(f"  {line.strip()}")

# ============================================================================
# 8. Dashboard Summary
# ============================================================================
print("\n=== 8. Dashboard Summary ===\n")

# Get dashboard-friendly stats
dashboard = format_stats_dashboard(tracker)
print("Performance dashboard data:")
for operation, stats in list(dashboard.items())[:3]:
    print(f"\n{operation}:")
    print(f"  requests: {stats['count']}")
    print(f"  success_rate: {stats['success_rate']:.2%}")
    d = stats["duration_ms"]
    print(f"  p95 latency: {d['p95']:.2f}ms")

# ============================================================================
# 9. Prometheus Export
# ============================================================================
print("\n=== 9. Prometheus Export ===\n")

# Add more metrics for export
registry.counter("api_requests_total", tags={"endpoint": "/entities"})
registry.counter("api_requests_total", tags={"endpoint": "/traverse"})
registry.gauge("concurrent_users", 7)

prometheus_file = "/tmp/metrics.prom"
with open(prometheus_file, "w") as f:
    f.write(format_prometheus_metrics(registry))

print(f"Exported metrics to {prometheus_file}")
with open(prometheus_file, "r") as f:
    lines = f.readlines()
    print("\nPrometheus metrics preview:")
    for line in lines[:8]:
        print(f"  {line.strip()}")

print("\n" + "=" * 70)
print("Observability demo complete!")
print("=" * 70)

# Cleanup
import os
try:
    os.remove("/tmp/audit_observability.log")
    os.remove("/tmp/audit_metrics.prom")
    os.remove("/tmp/metrics.prom")
except:
    pass
