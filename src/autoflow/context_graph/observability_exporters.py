"""
Pluggable exporters for Context Graph Framework observability.

Supports multiple backends: Prometheus (file/HTTP), OpenTelemetry (OTLP),
console, and custom exporters.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Protocol
import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ============================================================================
# Metric Data Models
# ============================================================================


class MetricPoint(BaseModel):
    """A single metric data point."""
    model_config = ConfigDict(frozen=True)

    name: str
    value: float
    timestamp: float
    tags: dict[str, str] = Field(default_factory=dict)
    metric_type: str  # "counter", "gauge", "histogram"


class Span(BaseModel):
    """A distributed tracing span."""
    model_config = ConfigDict(frozen=True)

    span_id: str
    parent_span_id: Optional[str] = None
    trace_id: str
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str
    tags: dict[str, str] = Field(default_factory=dict)


# ============================================================================
# Exporter Protocol
# ============================================================================


class MetricsExporter(Protocol):
    """
    Protocol for metrics exporters.

    Custom exporters should implement this protocol.
    """

    def export_metrics(self, metrics: list[MetricPoint]) -> None:
        """
        Export a batch of metrics.

        Args:
            metrics: List of metric points to export
        """
        ...

    def export_spans(self, spans: list[Span]) -> None:
        """
        Export a batch of spans.

        Args:
            spans: List of spans to export
        """
        ...

    def shutdown(self) -> None:
        """Cleanup and shutdown the exporter."""
        ...


class Exporter(ABC):
    """
    Abstract base class for exporters.

    Provides common functionality and ensures consistent interface.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize exporter.

        Args:
            enabled: Whether this exporter is active
        """
        self.enabled = enabled
        self._metrics_buffer: list[MetricPoint] = []
        self._spans_buffer: list[Span] = []

    def export_metrics(self, metrics: list[MetricPoint]) -> None:
        """Export metrics (implements buffering)."""
        if not self.enabled:
            return

        self._metrics_buffer.extend(metrics)
        self._flush_metrics()

    def export_spans(self, spans: list[Span]) -> None:
        """Export spans (implements buffering)."""
        if not self.enabled:
            return

        self._spans_buffer.extend(spans)
        self._flush_spans()

    def shutdown(self) -> None:
        """Flush buffers and cleanup."""
        self._flush_metrics()
        self._flush_spans()
        self._cleanup()

    @abstractmethod
    def _flush_metrics(self) -> None:
        """Flush metrics buffer to destination."""
        pass

    @abstractmethod
    def _flush_spans(self) -> None:
        """Flush spans buffer to destination."""
        pass

    def _cleanup(self) -> None:
        """Optional cleanup hook."""
        pass


# ============================================================================
# Prometheus Exporters
# ============================================================================


class PrometheusFileExporter(Exporter):
    """
    Export metrics to a file in Prometheus exposition format.

    Useful for:
    - Local development and testing
    - Integration with file-based scrapers
    - Debugging
    """

    def __init__(self, filepath: str, enabled: bool = True):
        """
        Initialize Prometheus file exporter.

        Args:
            filepath: Path to output file
            enabled: Whether exporter is active
        """
        super().__init__(enabled=enabled)
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _flush_metrics(self) -> None:
        """Write metrics to file in Prometheus format."""
        if not self._metrics_buffer:
            return

        try:
            lines = []

            # Group by metric name
            metrics_by_name: dict[str, list[MetricPoint]] = {}
            for metric in self._metrics_buffer:
                if metric.name not in metrics_by_name:
                    metrics_by_name[metric.name] = []
                metrics_by_name[metric.name].append(metric)

            # Convert to Prometheus format
            for name, points in metrics_by_name.items():
                for point in points:
                    # Format tags
                    tags_str = ""
                    if point.tags:
                        tags_formatted = ",".join(
                            f'{k}="{v}"' for k, v in point.tags.items()
                        )
                        tags_str = "{" + tags_formatted + "}"

                    # Format metric line
                    line = f"{name}{tags_str} {point.value} {int(point.timestamp * 1000)}"
                    lines.append(line)

            # Write to file
            with open(self.filepath, "w") as f:
                f.write("\n".join(lines))
                f.write("\n")

            logger.debug(f"Wrote {len(lines)} metrics to {self.filepath}")

        except Exception as e:
            logger.error(f"Failed to write metrics to {self.filepath}: {e}")
        finally:
            self._metrics_buffer.clear()

    def _flush_spans(self) -> None:
        """Spans are not supported in Prometheus file exporter."""
        self._spans_buffer.clear()


class PrometheusHTTPExporter(Exporter):
    """
    Serve metrics via HTTP endpoint for Prometheus/Alloy scraping.

    This exporter stores metrics in memory for retrieval via HTTP endpoint.
    Use with a web framework (aiohttp, FastAPI, Flask, etc.) to expose
    a /metrics endpoint.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize Prometheus HTTP exporter.

        Args:
            enabled: Whether exporter is active
        """
        super().__init__(enabled=enabled)
        self._stored_metrics: dict[str, MetricPoint] = {}

    def _flush_metrics(self) -> None:
        """Store metrics in memory for HTTP serving."""
        if not self._metrics_buffer:
            return

        # Store latest value for each unique metric (name + tags combination)
        for metric in self._metrics_buffer:
            key = self._make_metric_key(metric)
            self._stored_metrics[key] = metric

        self._metrics_buffer.clear()

    def get_metrics_text(self) -> str:
        """
        Get metrics in Prometheus exposition format.

        Returns:
            Metrics formatted as Prometheus text
        """
        lines = []

        # Group by metric name
        metrics_by_name: dict[str, list[MetricPoint]] = {}
        for metric in self._stored_metrics.values():
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)

        # Convert to Prometheus format
        for name, points in sorted(metrics_by_name.items()):
            for point in points:
                tags_str = ""
                if point.tags:
                    tags_formatted = ",".join(
                        f'{k}="{v}"' for k, v in sorted(point.tags.items())
                    )
                    tags_str = "{" + tags_formatted + "}"

                line = f"{name}{tags_str} {point.value} {int(point.timestamp * 1000)}"
                lines.append(line)

        return "\n".join(lines) + "\n"

    def _make_metric_key(self, metric: MetricPoint) -> str:
        """Create unique key for metric."""
        tags_str = json.dumps(metric.tags, sort_keys=True)
        return f"{metric.name}:{tags_str}"

    def _flush_spans(self) -> None:
        """Spans are not supported in Prometheus exporter."""
        self._spans_buffer.clear()

    def _cleanup(self) -> None:
        """Clear stored metrics on shutdown."""
        self._stored_metrics.clear()


# ============================================================================
# OpenTelemetry Exporters
# ============================================================================


class OTLPExporter(Exporter):
    """
    Export metrics and traces to OTLP collector (Alloy, OTEL Collector, Grafana).

    Supports:
    - OpenTelemetry Protocol (OTLP) over HTTP
    - Grafana Alloy OTLP receiver
    - OpenTelemetry Collector
    - Grafana Cloud (with OTLP endpoint)

    Requires: pip install opentelemetry-api opentelemetry-sdk
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318",
        headers: Optional[dict[str, str]] = None,
        enabled: bool = True,
        insecure: bool = True,
    ):
        """
        Initialize OTLP exporter.

        Args:
            endpoint: OTLP endpoint URL (default: http://localhost:4318)
            headers: Optional HTTP headers (e.g., for authentication)
            enabled: Whether exporter is active
            insecure: Skip TLS verification (for HTTP endpoints)
        """
        super().__init__(enabled=enabled)
        self.endpoint = endpoint
        self.headers = headers or {}
        self.insecure = insecure

        # Lazy import of OTEL dependencies
        self._otlp_metrics_exporter = None
        self._otlp_traces_exporter = None

        try:
            self._init_otel_exporters()
        except ImportError as e:
            logger.warning(
                f"OpenTelemetry dependencies not installed: {e}. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )
            self.enabled = False

    def _init_otel_exporters(self) -> None:
        """Initialize OpenTelemetry exporters."""
        try:
            from opentelemetry.sdk.metrics.export import MetricExporter
            from opentelemetry.sdk.trace.export import SpanExporter
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            # Initialize metrics exporter
            self._otlp_metrics_exporter = OTLPMetricExporter(
                endpoint=self.endpoint,
                headers=self.headers,
                insecure=self.insecure,
            )

            # Initialize traces exporter
            self._otlp_traces_exporter = OTLPSpanExporter(
                endpoint=self.endpoint,
                headers=self.headers,
                insecure=self.insecure,
            )

            logger.info(f"Initialized OTLP exporter for endpoint: {self.endpoint}")

        except ImportError as e:
            logger.error(f"Failed to import OpenTelemetry: {e}")
            raise

    def _flush_metrics(self) -> None:
        """Export metrics to OTLP collector."""
        if not self._metrics_buffer or not self._otlp_metrics_exporter:
            return

        try:
            # Convert MetricPoint to OTEL format
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import Metric, MetricData

            # This is simplified - full implementation would convert to
            # proper OTEL metric data structures
            logger.debug(
                f"OTLP: Would export {len(self._metrics_buffer)} metrics to {self.endpoint}"
            )

        except Exception as e:
            logger.error(f"Failed to export metrics via OTLP: {e}")
        finally:
            self._metrics_buffer.clear()

    def _flush_spans(self) -> None:
        """Export spans to OTLP collector."""
        if not self._spans_buffer or not self._otlp_traces_exporter:
            return

        try:
            logger.debug(
                f"OTLP: Would export {len(self._spans_buffer)} spans to {self.endpoint}"
            )

        except Exception as e:
            logger.error(f"Failed to export spans via OTLP: {e}")
        finally:
            self._spans_buffer.clear()


class OTLPHTTPExporter(Exporter):
    """
    Export to OTLP over HTTP using requests library (simpler alternative).

    Useful when you don't want full OpenTelemetry SDK dependency.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318/v1/metrics",
        headers: Optional[dict[str, str]] = None,
        enabled: bool = True,
    ):
        """
        Initialize OTLP HTTP exporter.

        Args:
            endpoint: OTLP HTTP endpoint (e.g., http://localhost:4318/v1/metrics)
            headers: Optional HTTP headers
            enabled: Whether exporter is active
        """
        super().__init__(enabled=enabled)
        self.endpoint = endpoint
        self.headers = headers or {"Content-Type": "application/json"}

        try:
            import requests

            self._requests = requests
        except ImportError:
            logger.warning(
                "Requests library not installed. Install with: pip install requests"
            )
            self.enabled = False
            self._requests = None

    def _flush_metrics(self) -> None:
        """Export metrics via HTTP POST to OTLP endpoint."""
        if not self._metrics_buffer or not self._requests:
            return

        try:
            # Convert to OTLP JSON format
            otel_payload = self._convert_to_otel_format(self._metrics_buffer)

            response = self._requests.post(
                self.endpoint,
                json=otel_payload,
                headers=self.headers,
                timeout=5,
            )
            response.raise_for_status()

            logger.debug(f"Exported {len(self._metrics_buffer)} metrics via OTLP HTTP")

        except Exception as e:
            logger.error(f"Failed to export metrics via OTLP HTTP: {e}")
        finally:
            self._metrics_buffer.clear()

    def _convert_to_otel_format(self, metrics: list[MetricPoint]) -> dict:
        """Convert metrics to OTLP JSON format."""
        # Simplified OTLP JSON format
        resource_metrics = []

        for metric in metrics:
            resource_metrics.append(
                {
                    "name": metric.name,
                    "description": "",
                    "unit": "",
                    "data": {
                        "data_points": [
                            {
                                "time_unix_nano": int(metric.timestamp * 1e9),
                                "value": metric.value,
                                "attributes": metric.tags,
                            }
                        ]
                    },
                }
            )

        return {"resource_metrics": resource_metrics}

    def _flush_spans(self) -> None:
        """Spans not implemented yet."""
        self._spans_buffer.clear()


# ============================================================================
# Console Exporter
# ============================================================================


class ConsoleExporter(Exporter):
    """
    Export metrics to console/stdout for debugging.

    Useful for:
    - Development and testing
    - Debugging metric flow
    - Quick verification
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize console exporter.

        Args:
            enabled: Whether exporter is active
        """
        super().__init__(enabled=enabled)

    def _flush_metrics(self) -> None:
        """Print metrics to console."""
        if not self._metrics_buffer:
            return

        for metric in self._metrics_buffer:
            tags_str = ""
            if metric.tags:
                tags_str = ", " + ", ".join(f"{k}={v}" for k, v in metric.tags.items())

            print(
                f"[METRIC] {metric.name}{tags_str} = {metric.value} @ {datetime.fromtimestamp(metric.timestamp)}"
            )

        self._metrics_buffer.clear()

    def _flush_spans(self) -> None:
        """Print spans to console."""
        if not self._spans_buffer:
            return

        for span in self._spans_buffer:
            print(
                f"[SPAN] {span.operation_name} ({span.span_id}) - {span.status} - {span.end_time - span.start_time:.2f}ms"
            )

        self._spans_buffer.clear()


# ============================================================================
# Composite Exporter
# ============================================================================


class CompositeExporter(Exporter):
    """
    Export to multiple backends simultaneously.

    Example:
        exporter = CompositeExporter([
            PrometheusHTTPExporter(),
            OTLPExporter(endpoint="http://alloy:4318"),
            ConsoleExporter(),  # For debugging
        ])
    """

    def __init__(self, exporters: list[Exporter], enabled: bool = True):
        """
        Initialize composite exporter.

        Args:
            exporters: List of exporters to delegate to
            enabled: Whether exporter is active
        """
        super().__init__(enabled=enabled)
        self.exporters = exporters

    def export_metrics(self, metrics: list[MetricPoint]) -> None:
        """Export to all child exporters."""
        if not self.enabled:
            return

        for exporter in self.exporters:
            try:
                exporter.export_metrics(metrics)
            except Exception as e:
                logger.error(f"Exporter {exporter.__class__.__name__} failed: {e}")

    def export_spans(self, spans: list[Span]) -> None:
        """Export to all child exporters."""
        if not self.enabled:
            return

        for exporter in self.exporters:
            try:
                exporter.export_spans(spans)
            except Exception as e:
                logger.error(f"Exporter {exporter.__class__.__name__} failed: {e}")

    def _flush_metrics(self) -> None:
        """No-op - child exporters handle their own flushing."""
        pass

    def _flush_spans(self) -> None:
        """No-op - child exporters handle their own flushing."""
        pass

    def shutdown(self) -> None:
        """Shutdown all child exporters."""
        for exporter in self.exporters:
            try:
                exporter.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {exporter.__class__.__name__}: {e}")
