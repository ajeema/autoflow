#!/usr/bin/env python3
"""
AutoFlow + OpenTelemetry + Grafana Integration Example

This example demonstrates how to integrate AutoFlow with OpenTelemetry
for distributed tracing, metrics, and logs that can be visualized in Grafana.

It shows:
1. Setting up OpenTelemetry with proper resource attributes
2. Correlating AutoFlow operations with spans/traces
3. Exporting traces to OTLP (Grafana Tempo, Jaeger, etc.)
4. Structured logging with trace correlation
5. Metrics collection with Prometheus/Grafana Cloud

Setup:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-auto-instrumentation
    pip install opentelemetry-exporter-otlp opentelemetry-exporter-prometheus

For Grafana Cloud:
    export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
    export OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <your-base64-encoded-creds>

For Local Grafana/Tempo:
    docker run -d -p 4317:4317 -p 4318:4318 \\
        -v $(pwd)/tempo.yaml:/etc/tempo.yaml \\
        grafana/tempo:latest \\
        -config.file=/etc/tempo.yaml
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# =============================================================================
# Option 1: Auto-initialization (Recommended for production)
# =============================================================================
def setup_autoflow_with_otel_auto():
    """
    Automatically initialize OpenTelemetry with sensible defaults.
    This uses opentelemetry-auto-instrumentation for automatic span creation.
    """

    # Set environment variables before any imports
    # These configure the auto-instrumentation
    os.environ.setdefault("OTEL_SERVICE_NAME", "autoflow-engine")
    os.environ.setdefault("OTEL_RESOURCE_ATTRIBUTES",
        "service.name=autoflow-engine,"
        "service.version=1.0.0,"
        "deployment.environment=production,"
        "service.namespace=ai-automation"
    )
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    os.environ.setdefault("OTEL_TRACES_EXPORTER", "otlp")
    os.environ.setdefault("OTEL_METRICS_EXPORTER", "otlp")
    os.environ.setdefault("OTEL_LOGS_EXPORTER", "otlp")

    # Optional: Set batch span processor settings for production
    os.environ.setdefault("OTEL_BSP_SCHEDULE_DELAY_MILLIS", "5000")
    os.environ.setdefault("OTEL_BSP_MAX_QUEUE_SIZE", "2048")
    os.environ.setdefault("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")

    # Import after env vars are set
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource

    # Create resource with service information
    resource = Resource.create({
        "service.name": "autoflow-engine",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENV", "development"),
    })

    # Set up trace provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    # Configure OTLP exporter (works with Grafana Tempo, Jaeger, etc.)
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://localhost:4317"  # Default for local Tempo/Jaeger
    )
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

    exporter_kwargs = {}
    if otlp_headers:
        # Parse headers (e.g., "Authorization=Basic abc123")
        headers = {}
        for h in otlp_headers.split(","):
            if "=" in h:
                key, value = h.split("=", 1)
                headers[key.strip()] = value.strip()
        exporter_kwargs["headers"] = headers

    span_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        **exporter_kwargs
    )

    # Add batch span processor for better performance
    tracer_provider.add_span_processor(
        BatchSpanProcessor(span_exporter)
    )

    print(f"✓ OpenTelemetry initialized")
    print(f"  Endpoint: {otlp_endpoint}")
    print(f"  Service: autoflow-engine")
    print(f"  Environment: {os.getenv('ENV', 'development')}")


# =============================================================================
# Option 2: Manual Configuration (More control)
# =============================================================================
def setup_autoflow_with_otel_manual():
    """
    Manually configure OpenTelemetry with custom exporters and processors.
    Use this for fine-grained control over tracing behavior.
    """

    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_RESOURCE
    from opentelemetry.semantic_conventions import ResourceAttributes

    # Create comprehensive resource attributes
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: "autoflow-engine",
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENV", "development"),
        ResourceAttributes.PROCESS_PID: os.getpid(),
        "service.namespace": "ai-automation",
        "autoflow.workflow.id": "example-workflow",
    })

    # Configure tracing
    tracer_provider = TracerProvider(resource=resource)

    # Add multiple exporters
    # 1. Console exporter for debugging
    tracer_provider.add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )

    # 2. OTLP exporter for Grafana Tempo/Jaeger
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            headers=_parse_otlp_headers()
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )

    trace.set_tracer_provider(tracer_provider)

    # Configure metrics
    # Option A: Prometheus scrape endpoint (for local dev)
    prometheus_reader = PrometheusMetricReader(
        endpoint="localhost:9464",  # Default: http://localhost:9464/metrics
    )

    # Option B: OTLP metrics (for Grafana Cloud)
    # Uncomment to use OTLP for metrics
    # if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    #     otlp_metric_exporter = OTLPMetricExporter(
    #         endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
    #         headers=_parse_otlp_headers()
    #     )
    #     prometheus_reader = PeriodicExportingMetricReader(
    #         otlp_metric_exporter,
    #         export_interval_millis=15000,  # Export every 15 seconds
    #     )

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader]
    )
    metrics.set_meter_provider(meter_provider)

    print("✓ OpenTelemetry manually configured")
    print("  Tracing: Console + OTLP" if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") else "  Tracing: Console only")
    print("  Metrics: Prometheus (http://localhost:9464/metrics)")


def _parse_otlp_headers() -> dict[str, str]:
    """Parse OTLP headers from environment variable."""
    headers_str = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers = {}
    if headers_str:
        for h in headers_str.split(","):
            if "=" in h:
                key, value = h.split("=", 1)
                headers[key.strip()] = value.strip()
    return headers


# =============================================================================
# Option 3: Alloy/OTel Collector Configuration
# =============================================================================

def generate_alloy_config():
    """
    Generate an Alloy configuration file for collecting AutoFlow telemetry.

    Alloy is Grafana's new OpenTelemetry collector that replaces
    Promtail, the Prometheus scrape config, and the OTel collector.

    To use this config:
    1. Save it to config.alloy
    2. Run: alloy run config.alloy
    3. Configure AutoFlow to export to localhost:4317
    """

    config = """
// AutoFlow + Grafana Alloy Configuration
// This config receives traces/metrics/logs from AutoFlow
// and forwards them to Grafana Cloud or local backends

// Receivers: Accept telemetry from AutoFlow
otelcol.receiver.otlp "default" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }

  http {
    endpoint = "0.0.0.0:4318"
  }

  output -> otelcol.processor.batch.default.input
}

// Processors: Batch and enrich telemetry
otelcol.processor.batch "default" {
  timeout = 5s
  output -> otelcol.exporter.otlp.default.input
}

// Exporters: Send to Grafana Cloud (or local backends)
// Uncomment the appropriate section:

// Option A: Grafana Cloud
otelcol.exporter.otlp "default" {
  client {
    endpoint = "otlp-gateway-prod-us-central-0.grafana.net:4317"
    auth = otelcol.auth.basic "grafana_cloud" {
      username = "YOUR_GRAFANA_CLOUD_INSTANCE_ID"
      password = "YOUR_GRAFANA_API_KEY"
    }
  }

  output -> lok.write "autoflow_logs"
                -> prometheus.remote_write.metrics_service
                -> tempo.write "autoflow_traces"
}

// Option B: Local backends (for development)
// Uncomment these instead of the above:

// Local Tempo (traces)
// tempo.write "autoflow_traces" {
//   endpoint = "localhost:4317"
//   output -> <discard>
// }

// Local Prometheus (metrics)
// prometheus.remote_write "metrics_service" {
//   endpoint {
//     url = "http://localhost:9090/api/v1/write"
//   }
//   output -> <discard>
// }

// Local Loki (logs)
// lok.write "autoflow_logs" {
//   endpoint {
//     url = "http://localhost:3100/loki/api/v1/push"
//   }
//   output -> <discard>
// }

// Local Grafana dashboard
// grafana.dashboard "autoflow_overview" {
//   title = "AutoFlow Overview"
//   tags = ["autoflow", "ai-workflows"]
// }
"""

    print("=== Alloy Configuration (config.alloy) ===")
    print(config)
    print("\nTo use this config:")
    print("  1. Save to config.alloy")
    print("  2. alloy run config.alloy")
    print("  3. Set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317")


# =============================================================================
# Using AutoFlow with OpenTelemetry
# =============================================================================

def create_autoflow_engine_with_tracing():
    """Create AutoFlow engine with OpenTelemetry tracing enabled."""

    from autoflow import AutoImproveEngine
    from autoflow.apply.applier import ProposalApplier
    from autoflow.apply.git_backend import GitApplyBackend
    from autoflow.apply.policy import ApplyPolicy
    from autoflow.decide.decision_graph import DecisionGraph
    from autoflow.decide.rules import HighErrorRateRetryRule
    from autoflow.evaluate.shadow import ShadowEvaluator
    from autoflow.graph.context_graph import ContextGraphBuilder
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.otel import span  # AutoFlow's built-in OTEL wrapper
    from autoflow.types import RiskLevel

    # Import OpenTelemetry
    from opentelemetry import trace

    # Get tracer
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("autoflow.engine.init"):
        with span("graph_builder.init"):
            graph_builder = ContextGraphBuilder()

        with span("store.init"):
            store = SQLiteGraphStore(db_path=":memory:")

        with span("decision_graph.init"):
            decision_graph = DecisionGraph(
                rules=[
                    HighErrorRateRetryRule(
                        workflow_id="example_workflow",
                        threshold=3
                    )
                ]
            )

        with span("evaluator.init"):
            evaluator = ShadowEvaluator()

        with span("applier.init"):
            applier = ProposalApplier(
                policy=ApplyPolicy(
                    allowed_paths_prefixes=("config/",),
                    max_risk=RiskLevel.LOW
                ),
                backend=GitApplyBackend(repo_path=Path(".")),
            )

        with span("engine.init"):
            engine = AutoImproveEngine(
                store=store,
                graph_builder=graph_builder,
                decision_graph=decision_graph,
                evaluator=evaluator,
                applier=applier,
            )

    return engine


def example_autoflow_with_traced_workflow():
    """Example workflow with comprehensive tracing."""

    from autoflow.observe.events import make_event
    from opentelemetry import trace
    from opentelemetry import metrics

    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Create custom metrics
    workflow_counter = meter.create_counter(
        "autoflow.workflow.runs",
        description="Number of workflow runs"
    )

    workflow_duration = meter.create_histogram(
        "autoflow.workflow.duration_ms",
        description="Workflow execution duration"
    )

    with tracer.start_as_current_span("workflow.execution") as span:
        # Add attributes to the span
        span.set_attribute("workflow.name", "example_workflow")
        span.set_attribute("workflow.version", "1.0.0")
        span.set_attribute("workflow.environment", os.getenv("ENV", "development"))

        import time
        start_time = time.time()

        try:
            # Create engine (will create child spans)
            engine = create_autoflow_engine_with_tracing()

            # Ingest events (with span correlation)
            with span("workflow.ingest"):
                events = [
                    make_event(
                        source="example_workflow",
                        name="step_completed",
                        attributes={
                            "step_name": "data_processing",
                            "trace_id": hex(span.context.trace_id)[2:],
                            "span_id": hex(span.context.span_id)[2:],
                        }
                    ),
                    make_event(
                        source="example_workflow",
                        name="step_failed",
                        attributes={
                            "step_name": "model_inference",
                            "error": "timeout",
                            "trace_id": hex(span.context.trace_id)[2:],
                            "span_id": hex(span.context.span_id)[2:],
                        }
                    ),
                ]
                engine.ingest(events)

            # Propose improvements
            with span("workflow.propose"):
                proposals = engine.propose()
                span.set_attribute("workflow.proposals.count", len(proposals))

            # Evaluate
            with span("workflow.evaluate"):
                if proposals:
                    results = engine.evaluate(proposals)
                    span.set_attribute(
                        "workflow.evaluation.passed",
                        sum(1 for r in results if r.passed)
                    )

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            workflow_counter.add(1, {"workflow.name": "example_workflow"})
            workflow_duration.record(duration_ms, {"workflow.name": "example_workflow"})

            span.set_status("OK")
            span.set_attribute("workflow.success", True)

        except Exception as e:
            span.record_exception(e)
            span.set_status("ERROR", str(e))
            raise


# =============================================================================
# Structured Logging with Trace Correlation
# =============================================================================

def setup_logging_with_trace_correlation():
    """
    Configure structured logging that includes trace IDs for correlation.
    This allows you to find all logs related to a specific trace in Grafana/Loki.
    """

    import logging
    import json
    from opentelemetry import trace

    class TraceCorrelationFormatter(logging.Formatter):
        """Custom formatter that adds OpenTelemetry trace context to logs."""

        def format(self, record):
            # Get current span context
            current_span = trace.get_current_span()
            context = current_span.get_span_context()

            # Create structured log entry
            log_entry = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "trace_id": hex(context.trace_id)[2:] if context.is_valid else "",
                "span_id": hex(context.span_id)[2:] if context.is_valid else "",
                "workflow": getattr(record, "workflow", ""),
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_entry)

    # Configure root logger
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(TraceCorrelationFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


def example_traced_logging():
    """Example of logging with trace correlation."""

    from opentelemetry import trace
    from autoflow.otel import span

    logger = setup_logging_with_trace_correlation()
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("workflow.process"):
        logger.info("Starting workflow processing")

        with span("workflow.step1"):
            logger.info("Processing step 1")
            # This log will have trace_id and span_id automatically added

        with span("workflow.step2"):
            logger.info("Processing step 2")
            # Different span_id, same trace_id

    # In Grafana/Loki, you can query:
    # {trace_id="1234..."} to find all logs from this trace
    # Or use the trace ID in Tempo to find the trace, then switch to Logs


# =============================================================================
# Grafana Dashboard Configuration
# =============================================================================

def generate_grafana_dashboard():
    """
    Generate a Grafana dashboard JSON for visualizing AutoFlow metrics.

    To import this dashboard:
    1. Copy the JSON output
    2. Go to Grafana -> Dashboards -> Import
    3. Paste the JSON
    """

    import json

    dashboard = {
        "dashboard": {
            "title": "AutoFlow Performance Dashboard",
            "description": "Monitor AutoFlow workflow performance, improvements, and metrics",
            "tags": ["autoflow", "ai-workflows", "autoimprovement"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "10s",
            "panels": [
                {
                    "id": 1,
                    "title": "Workflow Runs",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(autoflow_workflow_runs_total[5m])",
                            "legendFormat": "{{workflow_name}}",
                            "refId": "A"
                        }
                    ]
                },
                {
                    "id": 2,
                    "title": "Workflow Duration",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, autoflow_workflow_duration_ms_bucket)",
                            "legendFormat": "P95 Latency",
                            "refId": "A"
                        },
                        {
                            "expr": "histogram_quantile(0.50, autoflow_workflow_duration_ms_bucket)",
                            "legendFormat": "P50 Latency",
                            "refId": "B"
                        }
                    ]
                },
                {
                    "id": 3,
                    "title": "Recent Traces",
                    "type": "table",
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "{from=\"TraceID\", source=\"autoflow-engine\"}",
                            "refId": "A"
                        }
                    ]
                }
            ]
        }
    }

    print(json.dumps(dashboard, indent=2))
    print("\nImport this JSON into Grafana to visualize AutoFlow metrics")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the OpenTelemetry integration example."""

    print("=" * 70)
    print("AutoFlow + OpenTelemetry + Grafana Integration Example")
    print("=" * 70)
    print()

    # Choose setup method
    setup_method = os.getenv("OTEL_SETUP_METHOD", "auto")

    if setup_method == "manual":
        print("Setting up OpenTelemetry with manual configuration...")
        setup_autoflow_with_otel_manual()
    else:
        print("Setting up OpenTelemetry with auto-configuration...")
        setup_autoflow_with_otel_auto()

    print()

    # Show Alloy configuration
    print("\n" + "=" * 70)
    print("Alloy Configuration (for collecting and routing telemetry)")
    print("=" * 70)
    generate_alloy_config()

    print("\n" + "=" * 70)
    print("Running example workflow with tracing...")
    print("=" * 70)
    example_autoflow_with_traced_workflow()

    print("\n" + "=" * 70)
    print("Example completed!")
    print("=" * 70)
    print("\nTo view traces in Grafana Tempo:")
    print("  1. Open Grafana")
    print("  2. Navigate to Explore -> Tempo")
    print("  3. Search by service.name=autoflow-engine")
    print("\nTo view metrics:")
    print("  1. Navigate to Explore -> Prometheus")
    print("  2. Query: rate(autoflow_workflow_runs_total[5m])")
    print("\nTo view logs with trace correlation:")
    print("  1. Navigate to Explore -> Loki")
    print("  2. Query: {source=\"autoflow-engine\"} | line format `{{.trace_id}}`")


if __name__ == "__main__":
    main()
