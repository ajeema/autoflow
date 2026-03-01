"""
Enhanced observability for Context Graph Framework.

Provides comprehensive monitoring, metrics, tracing, and alerting capabilities
for production deployments.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Generator, Protocol, TYPE_CHECKING
from collections import defaultdict
import threading
import time
import uuid
import logging
from functools import wraps
import statistics

# Pydantic for validation
from pydantic import BaseModel, Field, ConfigDict

# Type checking imports (avoid circular dependency)
if TYPE_CHECKING:
    from autoflow.context_graph.observability_exporters import Exporter, MetricPoint


# ============================================================================
# Correlation and Request Tracking
# ============================================================================


class RequestContext:
    """
    Context for tracking a request across multiple operations.

    Provides correlation IDs, request tracking, and distributed tracing support.
    """

    _context = threading.local()

    def __init__(
        self,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize request context.

        Args:
            request_id: Unique request identifier (auto-generated if None)
            trace_id: Distributed trace ID
            user_id: User making the request
            parent_span_id: Parent span for distributed tracing
            metadata: Additional context metadata
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.trace_id = trace_id or self.request_id
        self.user_id = user_id
        self.parent_span_id = parent_span_id
        self.metadata = metadata or {}
        self._spans: list[dict] = []
        self._start_time = time.perf_counter()

    @classmethod
    def current(cls) -> Optional["RequestContext"]:
        """Get the current request context."""
        return getattr(cls._context, "value", None)

    @classmethod
    def set(cls, context: "RequestContext") -> None:
        """Set the current request context."""
        cls._context.value = context

    def create_span(
        self,
        operation_name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "Span":
        """
        Create a child span for tracking sub-operations.

        Args:
            operation_name: Name of the operation
            metadata: Additional span metadata

        Returns:
            Span object
        """
        span = Span(
            span_id=str(uuid.uuid4()),
            parent_span_id=self.parent_span_id,
            operation_name=operation_name,
            metadata=metadata,
        )
        self._spans.append(span.to_dict())
        return span

    def get_duration_ms(self) -> float:
        """Get total request duration in milliseconds."""
        return (time.perf_counter() - self._start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": self.get_duration_ms(),
            "span_count": len(self._spans),
            "metadata": self.metadata,
            "spans": self._spans,
        }


@contextmanager
def request_context(
    user_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[RequestContext, None, None]:
    """
    Context manager for request-scoped tracking.

    Args:
        user_id: Optional user ID
        metadata: Optional request metadata

    Example:
        ```python
        with request_context(user_id="user123", metadata={"source": "api"}) as ctx:
            # All operations here share the same request_id and trace_id
            entity = graph.get_entity("brand:nike")
            result = graph.traverse("brand:nike", pattern)
        # Duration automatically tracked
        ```
    """
    context = RequestContext(user_id=user_id, metadata=metadata)
    RequestContext.set(context)
    try:
        yield context
    finally:
        RequestContext.set(None)


class Span:
    """
    A span represents a single operation within a trace.

    Used for distributed tracing and performance profiling.
    """

    def __init__(
        self,
        span_id: str,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize a span.

        Args:
            span_id: Unique span identifier
            operation_name: Name of the operation
            parent_span_id: Parent span ID if nested
            metadata: Additional metadata
        """
        self.span_id = span_id
        self.operation_name = operation_name
        self.parent_span_id = parent_span_id
        self.metadata = metadata or {}
        self._start_time = time.perf_counter()
        self._end_time: Optional[float] = None
        self._status = "started"

    def complete(
        self,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        """
        Mark the span as complete.

        Args:
            status: Status (completed, failed, cancelled)
            error: Error message if failed
        """
        self._end_time = time.perf_counter()
        self._status = status
        self.error = error

    def get_duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self._end_time or time.perf_counter()
        return (end - self._start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "operation_name": self.operation_name,
            "parent_span_id": self.parent_span_id,
            "status": self._status,
            "duration_ms": self.get_duration_ms(),
            "error": getattr(self, "error", None),
            "metadata": self.metadata,
        }


# ============================================================================
# Enhanced Metrics
# ============================================================================


class MetricsRegistry:
    """
    Registry for collecting and aggregating metrics.

    Thread-safe and supports multiple output formats and exporters.
    """

    def __init__(self, exporter: Optional["Exporter"] = None) -> None:
        """
        Initialize metrics registry.

        Args:
            exporter: Optional exporter for sending metrics to backends
        """
        self._metrics: list[MetricPoint] = []
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._exporter = exporter

    def counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Value to add (default: 1.0)
            tags: Optional tags
        """
        with self._lock:
            self._counters[name] += value
            self._metrics.append(
                MetricPoint(
                    name=name,
                    value=self._counters[name],
                    timestamp=time.time(),
                    tags=tags or {},
                    metric_type="counter",
                )
            )

    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Set a gauge metric.

        Args:
            name: Metric name
            value: Current value
            tags: Optional tags
        """
        with self._lock:
            self._gauges[name] = value
            self._metrics.append(
                MetricPoint(
                    name=name,
                    value=value,
                    timestamp=time.time(),
                    tags=tags or {},
                    metric_type="gauge",
                )
            )

    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Record a value in a histogram.

        Args:
            name: Metric name
            value: Value to record
            tags: Optional tags
        """
        with self._lock:
            self._histograms[name].append(value)
            self._metrics.append(
                MetricPoint(
                    name=name,
                    value=value,
                    timestamp=time.time(),
                    tags=tags or {},
                    metric_type="histogram",
                )
            )

    def get_counter(self, name: str) -> float:
        """Get current counter value."""
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value."""
        return self._gauges.get(name)

    def get_histogram_stats(
        self, name: str
    ) -> dict[str, float]:
        """
        Get histogram statistics.

        Args:
            name: Histogram name

        Returns:
            Dict with count, min, max, avg, p50, p95, p99, etc.
        """
        with self._lock:
            values = self._histograms.get(name, [])
            if not values:
                return {}

            sorted_values = sorted(values)
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": statistics.mean(values),
                "p50": sorted_values[len(sorted_values) // 2],
                "p75": sorted_values[int(len(sorted_values) * 0.75)],
                "p95": sorted_values[int(len(sorted_values) * 0.95)],
                "p99": sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) >= 100 else max(values),
                "sum": sum(values),
            }

    def get_metrics_since(
        self, timestamp: float
    ) -> list[MetricPoint]:
        """
        Get all metrics since a timestamp.

        Args:
            timestamp: Unix timestamp

        Returns:
            List of metric points
        """
        with self._lock:
            return [m for m in self._metrics if m.timestamp >= timestamp]

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def set_exporter(self, exporter: "Exporter") -> None:
        """
        Set or change the exporter.

        Args:
            exporter: Exporter instance to use
        """
        with self._lock:
            self._exporter = exporter

    def export_metrics(self, since_timestamp: Optional[float] = None) -> None:
        """
        Export metrics using the configured exporter.

        Args:
            since_timestamp: Only export metrics since this timestamp (if set)
        """
        if self._exporter is None:
            return

        with self._lock:
            if since_timestamp:
                metrics_to_export = [m for m in self._metrics if m.timestamp >= since_timestamp]
            else:
                metrics_to_export = list(self._metrics)

        # Export outside the lock to avoid holding it during I/O
        if metrics_to_export:
            self._exporter.export_metrics(metrics_to_export)

    def shutdown_exporter(self) -> None:
        """Shutdown the exporter, flushing any buffered metrics."""
        if self._exporter is not None:
            self._exporter.shutdown()


# Global metrics registry
global_registry = MetricsRegistry()


# ============================================================================
# Enhanced Performance Tracking
# ============================================================================


class PerformanceTracker:
    """
    Comprehensive performance tracking with percentiles and aggregation.

    Tracks operations over time windows and provides detailed statistics.
    """

    def __init__(
        self,
        window_size_seconds: int = 60,
        max_windows: int = 1440,  # 24 hours at 60s intervals
    ):
        """
        Initialize performance tracker.

        Args:
            window_size_seconds: Size of each time window in seconds
            max_windows: Maximum number of windows to keep
        """
        self.window_size = window_size_seconds
        self.max_windows = max_windows
        self._windows: dict[str, list[dict]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Record an operation performance data point.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            tags: Optional tags for grouping
        """
        window = int(time.time() // self.window_size)

        record = {
            "timestamp": time.time(),
            "duration_ms": duration_ms,
            "success": success,
            "tags": tags or {},
        }

        with self._lock:
            windows = self._windows[operation]
            windows.append(record)

            # Prune old windows
            while len(windows) > self.max_windows:
                windows.pop(0)

    def get_stats(
        self,
        operation: str,
        window_seconds: Optional[int] = None,
        tags: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Get performance statistics for an operation.

        Args:
            operation: Operation name
            window_seconds: Time window to analyze (default: all)
            tags: Filter by tags

        Returns:
            Detailed statistics dictionary
        """
        cutoff_time = None
        if window_seconds:
            cutoff_time = time.time() - window_seconds

        with self._lock:
            records = self._windows.get(operation, [])

        # Filter by time and tags
        filtered = []
        for record in records:
            if cutoff_time and record["timestamp"] < cutoff_time:
                continue
            if tags:
                if not all(
                    record.get("tags", {}).get(k) == v
                    for k, v in tags.items()
                ):
                    continue
            filtered.append(record)

        if not filtered:
            return {
                "count": 0,
                "operations_per_second": 0.0,
            }

        durations = [r["duration_ms"] for r in filtered]
        successes = [r for r in filtered if r["success"]]
        errors = [r for r in filtered if not r["success"]]

        sorted_durations = sorted(durations)
        n = len(durations)

        time_span = max(
            filtered[-1]["timestamp"] - filtered[0]["timestamp"],
            1,
        )

        return {
            "count": n,
            "operations_per_second": n / time_span,
            "success_rate": len(successes) / n if n > 0 else 0,
            "error_rate": len(errors) / n if n > 0 else 0,
            "duration_ms": {
                "min": min(durations),
                "max": max(durations),
                "avg": statistics.mean(durations),
                "median": sorted_durations[n // 2],
                "p90": sorted_durations[int(n * 0.9)] if n >= 10 else max(durations),
                "p95": sorted_durations[int(n * 0.95)] if n >= 20 else max(durations),
                "p99": sorted_durations[int(n * 0.99)] if n >= 100 else max(durations),
            },
        }


# ============================================================================
# Decorators for Automatic Instrumentation
# ============================================================================


def instrument(
    operation_name: Optional[str] = None,
    registry: Optional[MetricsRegistry] = None,
    tracker: Optional[PerformanceTracker] = None,
    include_args: bool = False,
):
    """
    Decorator to automatically instrument functions.

    Args:
        operation_name: Name for the operation (default: function name)
        registry: MetricsRegistry to record to
        tracker: PerformanceTracker to record to
        include_args: Include function arguments in metadata

    Example:
        ```python
        @instrument(operation_name="entity_lookup")
        def get_entity(self, entity_id: str) -> Optional[Entity]:
            return self._backend.get_entity(entity_id)
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start = time.perf_counter()
            metadata = {}
            error = None

            if include_args:
                # Include non-sensitive args
                safe_args = {
                    k: str(v)[:100]  # Truncate long values
                    for k, v in kwargs.items()
                    if not any(sensitive in str(v).lower() for sensitive in
                          ['password', 'token', 'secret', 'key'])
                }
                metadata.update(safe_args)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000

                # Record to registry
                if registry:
                    registry.histogram(
                        f"{name}.duration_ms",
                        duration_ms,
                        tags={"operation": name},
                    )
                    if error is None:
                        registry.counter(f"{name}.success", tags=metadata)
                    else:
                        registry.counter(f"{name}.error", tags=metadata)

                # Record to performance tracker
                if tracker:
                    tracker.record(
                        name,
                        duration_ms,
                        success=(error is None),
                        tags=metadata,
                    )

        return wrapper

    return decorator


# ============================================================================
# Health Checks
# ============================================================================


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck(BaseModel):
    """
    Health check result.

    Provides system health status for monitoring.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    status: HealthStatus
    checks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthChecker:
    """
    Health check registry and executor.

    Allows registering health checks and executing them.
    """

    def __init__(self) -> None:
        """Initialize health checker."""
        self._checks: dict[str, Callable[[], dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        check: Callable[[], dict[str, Any]],
    ) -> None:
        """
        Register a health check.

        Args:
            name: Check name
            check: Function that returns {"healthy": bool, "message": str, "metadata": dict}

        Example:
            ```python
            def check_db():
                try:
                    db.ping()
                    return {"healthy": True, "message": "Database OK"}
                except Exception as e:
                    return {"healthy": False, "message": str(e)}

            health_checker.register("database", check_db)
            ```
        """
        with self._lock:
            self._checks[name] = check

    def check_health(
        self,
        timeout_seconds: float = 5.0,
    ) -> HealthCheck:
        """
        Execute all health checks.

        Args:
            timeout_seconds: Maximum time to wait for all checks

        Returns:
            HealthCheck result with overall status
        """
        start = time.perf_counter()
        checks = {}

        # Run checks with timeout
        for name, check_fn in self._checks.items():
            try:
                # Run with timeout
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Health check '{name}' timed out")

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))

                try:
                    result = check_fn()
                    checks[name] = result
                finally:
                    signal.alarm(0)
                    old_handler = signal.signal(signal.SIGALRM, old_handler)

            except Exception as e:
                checks[name] = {
                    "healthy": False,
                    "message": str(e),
                    "error_type": type(e).__name__,
                }

        # Determine overall status
        if all(c.get("healthy", False) for c in checks.values()):
            status = HealthStatus.HEALTHY
        elif any(c.get("healthy", False) for c in checks.values()):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        duration_ms = (time.perf_counter() - start) * 1000

        return HealthCheck(
            status=status,
            checks=checks,
            duration_ms=duration_ms,
        )


# ============================================================================
# Alerting
# ============================================================================


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """
    Alert for notifying about important events.

    Generated from metrics and health checks.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity
    title: str
    description: str
    source: str  # Component that generated the alert
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Metric threshold info
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None


class Alerter:
    """
    Alert manager for generating alerts from metrics.

    Supports threshold-based alerting on metrics.
    """

    def __init__(self) -> None:
        """Initialize alerter."""
        self._rules: list[dict] = []
        self._alerts: list[Alert] = []
        self._lock = threading.Lock()

    def add_threshold_rule(
        self,
        metric_name: str,
        threshold: float,
        comparison: str,  # "gt", "lt", "gte", "lte", "eq"
        severity: AlertSeverity,
        title_template: str,
        description_template: str,
    ) -> None:
        """
        Add a threshold-based alerting rule.

        Args:
            metric_name: Name of metric to monitor
            threshold: Threshold value
            comparison: Comparison operator ("gt", "lt", "gte", "lte", "eq")
            severity: Alert severity
            title_template: Title template with {metric} and {value} placeholders
            description_template: Description template with {metric} and {value} placeholders

        Example:
            ```python
            alerter.add_threshold_rule(
                metric_name="traversal.duration_ms",
                threshold=1000,
                comparison="gt",
                severity=AlertSeverity.WARNING,
                title_template="Slow traversal detected",
                description_template="Traversal took {value:.2f}ms (threshold: {threshold}ms)"
            )
            ```
        """
        self._rules.append({
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "title_template": title_template,
            "description_template": description_template,
        })

    def check_rules(
        self,
        registry: MetricsRegistry,
    ) -> list[Alert]:
        """
        Check all alerting rules against current metrics.

        Args:
            registry: MetricsRegistry to check

        Returns:
            List of generated alerts
        """
        new_alerts = []

        with self._lock:
            # Get recent metrics (last minute)
            cutoff = time.time() - 60
            recent_metrics = registry.get_metrics_since(cutoff)

            for rule in self._rules:
                # Find matching metrics
                matching = [
                    m for m in recent_metrics
                    if m.name == rule["metric_name"]
                ]

                for metric in matching:
                    triggered = False
                    if rule["comparison"] == "gt" and metric.value > rule["threshold"]:
                        triggered = True
                    elif rule["comparison"] == "lt" and metric.value < rule["threshold"]:
                        triggered = True
                    elif rule["comparison"] == "gte" and metric.value >= rule["threshold"]:
                        triggered = True
                    elif rule["comparison"] == "lte" and metric.value <= rule["threshold"]:
                        triggered = True
                    elif rule["comparison"] == "eq" and metric.value == rule["threshold"]:
                        triggered = True

                    if triggered:
                        alert = Alert(
                            severity=rule["severity"],
                            title=rule["title_template"].format(
                                metric=rule["metric_name"],
                                value=metric.value,
                            ),
                            description=rule["description_template"].format(
                                metric=rule["metric_name"],
                                value=metric.value,
                                threshold=rule["threshold"],
                            ),
                            source="metrics_registry",
                            metric_name=rule["metric_name"],
                            metric_value=metric.value,
                            threshold=rule["threshold"],
                            current_value=metric.value,
                        )
                        new_alerts.append(alert)
                        self._alerts.append(alert)

        return new_alerts

    def get_active_alerts(self) -> list[Alert]:
        """Get all unresolved alerts."""
        with self._lock:
            return [a for a in self._alerts if not a.resolved]

    def resolve_alert(self, alert_id: str) -> None:
        """Mark an alert as resolved."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow()
                    break


# ============================================================================
# Export and Formatting
# ============================================================================


def format_prometheus_metrics(registry: MetricsRegistry) -> str:
    """
    Format metrics in Prometheus exposition format.

    Args:
        registry: MetricsRegistry with metrics

    Returns:
        Prometheus formatted metrics string
    """
    lines = []

    # Group metrics by name
    metrics_by_name: dict[str, list[MetricPoint]] = defaultdict(list)
    for metric in registry.get_metrics_since(0):
        metrics_by_name[metric.name].append(metric)

    for name, points in metrics_by_name.items():
        # Get latest values for each tag combination
        latest_by_tags: dict[tuple, MetricPoint] = {}
        for point in points:
            tag_key = tuple(sorted(point.tags.items()))
            if tag_key not in latest_by_tags or point.timestamp > latest_by_tags[tag_key].timestamp:
                latest_by_tags[tag_key] = point

        for point in latest_by_tags.values():
            # Format tags
            tags_str = ",".join(f'{k}="{v}"' for k, v in point.tags.items())
            lines.append(f"{name}{{{tags_str}}} {point.value} {int(point.timestamp)}")

    return "\n".join(lines)


def format_stats_dashboard(tracker: PerformanceTracker) -> dict[str, Any]:
    """
    Create dashboard-friendly statistics summary.

    Args:
        tracker: PerformanceTracker with data

    Returns:
        Dictionary suitable for dashboard display
    """
    summary = {}

    # Get the list of operations under lock to avoid concurrent modification
    with tracker._lock:
        operation_names = list(tracker._windows.keys())

    # Call get_stats for each operation (it handles its own locking)
    for operation_name in operation_names:
        stats = tracker.get_stats(operation_name)
        summary[operation_name] = stats

    return summary
