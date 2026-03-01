"""
Metrics and performance tracking for the Context Graph Framework.

Provides context managers and utilities for tracking operation performance
and integrating with audit logging.

Integrates with the enhanced observability module for production-grade monitoring.
"""

from contextlib import contextmanager
from time import perf_counter
from typing import Any, Generator, Optional

# Import enhanced observability when available
try:
    from autoflow.context_graph.observability import (
        RequestContext,
        request_context,
        global_registry,
        MetricsRegistry,
        PerformanceTracker,
        instrument,
        HealthChecker,
        Alerter,
        format_prometheus_metrics,
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    global_registry = None
    MetricsRegistry = None
    PerformanceTracker = None
    instrument = None
    HealthChecker = None
    Alerter = None


@contextmanager
def track_operation(
    operation_name: str,
    auditor: Optional[Any] = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager for tracking operation performance.

    Automatically measures execution time and logs to the auditor if provided.

    Args:
        operation_name: Name of the operation being tracked (e.g., "traversal", "query")
        auditor: Optional auditor to log metrics to

    Yields:
        dict with keys:
        - success: bool (set to False if exception raised)
        - error: Optional[str] (set if exception raised)
        - duration_ms: Optional[float] (set on exit)

    Example:
        ```python
        with track_operation("traversal", auditor) as metrics:
            result = graph.traverse("brand:nike", pattern)
            # metrics['success'] will be True if no exception
            # metrics['duration_ms'] will contain execution time
        ```
    """
    start = perf_counter()
    result: dict[str, Any] = {"success": False, "error": None, "duration_ms": None}

    try:
        yield result
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        raise
    finally:
        result["duration_ms"] = (perf_counter() - start) * 1000

        # Log to auditor if provided
        if auditor is not None:
            from autoflow.context_graph.audit import AuditEventType

            # Map operation names to event types
            event_type_map = {
                "traversal": AuditEventType.GRAPH_TRAVERSE,
                "query": AuditEventType.GRAPH_QUERY,
                "search": AuditEventType.GRAPH_SEARCH,
                "create_entity": AuditEventType.ENTITY_CREATED,
                "create_relationship": AuditEventType.RELATIONSHIP_CREATED,
                "read_entity": AuditEventType.ENTITY_READ,
                "read_relationship": AuditEventType.RELATIONSHIP_READ,
            }

            event_type = event_type_map.get(
                operation_name,
                AuditEventType.GRAPH_TRAVERSE,
            )

            auditor.log(
                event_type=event_type,
                operation=operation_name,
                success=result["success"],
                duration_ms=result["duration_ms"],
                error_message=result.get("error"),
            )


class Timer:
    """
    Simple timer for measuring execution time.

    Example:
        ```python
        timer = Timer()
        timer.start()
        # ... do work ...
        timer.stop()
        print(f" Took {timer.elapsed_ms}ms")
        ```
    """

    def __init__(self) -> None:
        """Initialize timer."""
        self._start: Optional[float] = None
        self._end: Optional[float] = None
        self.elapsed_ms: float = 0.0

    def start(self) -> None:
        """Start the timer."""
        self._start = perf_counter()

    def stop(self) -> float:
        """
        Stop the timer and return elapsed time in milliseconds.

        Returns:
            Elapsed time in milliseconds
        """
        if self._start is None:
            return 0.0

        self._end = perf_counter()
        self.elapsed_ms = (self._end - self._start) * 1000
        return self.elapsed_ms

    def __enter__(self) -> "Timer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()


class OperationMetrics:
    """
    Collect and aggregate metrics for operations.

    Useful for tracking performance over time.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._counts: dict[str, int] = {}
        self._times: dict[str, list[float]] = {}
        self._errors: dict[str, int] = {}

    def record(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """
        Record an operation metric.

        Args:
            operation: Operation name
            duration_ms: Execution time in milliseconds
            success: Whether operation succeeded
        """
        # Count
        self._counts[operation] = self._counts.get(operation, 0) + 1

        # Time
        if operation not in self._times:
            self._times[operation] = []
        self._times[operation].append(duration_ms)

        # Errors
        if not success:
            self._errors[operation] = self._errors.get(operation, 0) + 1

    def get_stats(self, operation: str) -> dict[str, Any]:
        """
        Get statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Dictionary with count, avg_time_ms, min_time_ms, max_time_ms, error_count
        """
        times = self._times.get(operation, [])

        if not times:
            return {
                "count": 0,
                "avg_time_ms": 0.0,
                "min_time_ms": 0.0,
                "max_time_ms": 0.0,
                "error_count": self._errors.get(operation, 0),
            }

        return {
            "count": len(times),
            "avg_time_ms": sum(times) / len(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "error_count": self._errors.get(operation, 0),
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all operations.

        Returns:
            Dictionary mapping operation names to their stats
        """
        return {
            operation: self.get_stats(operation)
            for operation in set(list(self._counts.keys()) + list(self._times.keys()))
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counts.clear()
        self._times.clear()
        self._errors.clear()
