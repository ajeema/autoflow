#!/usr/bin/env python3
"""
AutoFlow Production Deployment Example

This example demonstrates a production-ready AutoFlow deployment with:
- Docker containerization
- Kubernetes deployment manifests
- Health checks and readiness probes
- Graceful shutdown
- Configuration management
- Secret management
- Monitoring and alerting
- Log aggregation
- Trace correlation

Architecture:
    AutoFlow Engine runs as a service that:
    1. Receives events via API or message queue
    2. Processes events and builds context graph
    3. Generates and evaluates proposals
    4. Applies improvements (with approval if needed)
    5. Exports metrics, traces, and logs

Infrastructure:
    - Kubernetes: Orchestration
    - Prometheus: Metrics collection
    - Grafana: Visualization
    - Tempo: Distributed tracing
    - Loki: Log aggregation
    - AlertManager: Alerting
"""

import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# =============================================================================
# Configuration Management
# =============================================================================

class ProductionConfig:
    """
    Production configuration with environment variable overrides.

    Environment Variables:
        AUTOFLOW_DB_PATH: Path to graph database
        AUTOFLOW_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
        AUTOFLOW_WORKER_THREADS: Number of worker threads
        AUTOFLOW_BATCH_SIZE: Event batch processing size
        AUTOFLOW_EVALUATION_INTERVAL: Seconds between proposal evaluations

        # Optional integrations
        OTEL_EXPORTER_OTLP_ENDPOINT: OpenTelemetry collector endpoint
        S3_BUCKET: S3 bucket for archival
        SLACK_BOT_TOKEN: Slack bot token for notifications
    """

    def __init__(self):
        # Core settings
        self.db_path = os.getenv("AUTOFLOW_DB_PATH", "/data/autoflow.db")
        self.log_level = os.getenv("AUTOFLOW_LOG_LEVEL", "INFO")
        self.worker_threads = int(os.getenv("AUTOFLOW_WORKER_THREADS", "4"))
        self.batch_size = int(os.getenv("AUTOFLOW_BATCH_SIZE", "100"))
        self.evaluation_interval = int(os.getenv("AUTOFLOW_EVALUATION_INTERVAL", "300"))

        # OpenTelemetry
        self.otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "autoflow-engine")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        self.deployment_environment = os.getenv("ENV", "production")

        # AWS S3
        self.s3_bucket = os.getenv("S3_BUCKET")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")

        # Slack
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_channel = os.getenv("SLACK_CHANNEL", "#autoflow")

        # Policy
        self.allowed_paths = os.getenv(
            "AUTOFLOW_ALLOWED_PATHS",
            "config/,prompts/,skills/"
        ).split(",")
        self.max_risk = os.getenv("AUTOFLOW_MAX_RISK", "MEDIUM")

    @classmethod
    def from_env(cls) -> "ProductionConfig":
        """Load configuration from environment."""
        return cls()


# =============================================================================
# Health Checks
# =============================================================================

class HealthChecker:
    """
    Health check endpoints for Kubernetes probes.

    Provides:
    - Liveness: Is the service running?
    - Readiness: Can the service handle requests?
    - Startup: Has the service finished initialization?
    """

    def __init__(self):
        self.ready = False
        self.live = True
        self.started = False

    def is_live(self) -> bool:
        """Liveness probe - service is running."""
        return self.live

    def is_ready(self) -> bool:
        """Readiness probe - service can handle requests."""
        return self.ready and self.live

    def is_started(self) -> bool:
        """Startup probe - service has finished initialization."""
        return self.started

    def set_ready(self, ready: bool):
        """Set readiness state."""
        self.ready = ready

    def set_started(self, started: bool):
        """Set startup state."""
        self.started = started


# =============================================================================
# Production AutoFlow Engine
# =============================================================================

class ProductionAutoFlowEngine:
    """
    Production-ready AutoFlow engine with observability and reliability features.

    Features:
    - Graceful shutdown
    - Health check endpoints
    - OpenTelemetry tracing
    - Prometheus metrics
    - Structured logging
    - Event batching
    - Async processing
    """

    def __init__(
        self,
        config: ProductionConfig,
        health_checker: HealthChecker,
    ):
        self.config = config
        self.health_checker = health_checker
        self._shutdown = False

        # Setup logging
        self._setup_logging()

        # Setup OpenTelemetry if configured
        self._setup_telemetry()

        # Initialize engine components
        self._initialize_engine()

    def _setup_logging(self):
        """Configure structured logging."""

        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

        self.logger = logging.getLogger("autoflow.production")
        self.logger.info("Logging initialized")

    def _setup_telemetry(self):
        """Setup OpenTelemetry if endpoint is configured."""

        if not self.config.otel_endpoint:
            self.logger.info("OpenTelemetry not configured")
            return

        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.resources import Resource, SERVICE_RESOURCE

            # Create resource
            resource = Resource.create({
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                "deployment.environment": self.config.deployment_environment,
            })

            # Setup tracing
            trace_provider = TracerProvider(resource=resource)
            trace_exporter = OTLPSpanExporter(
                endpoint=self.config.otel_endpoint,
            )
            trace_provider.add_span_processor(
                BatchSpanProcessor(trace_exporter)
            )
            trace.set_tracer_provider(trace_provider)

            # Setup metrics
            metric_exporter = OTLPMetricExporter(
                endpoint=self.config.otel_endpoint,
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=15000,
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            metrics.set_meter_provider(meter_provider)

            self.logger.info(f"OpenTelemetry configured: {self.config.otel_endpoint}")

        except ImportError:
            self.logger.warning("OpenTelemetry packages not installed")

    def _initialize_engine(self):
        """Initialize AutoFlow engine components."""

        from autoflow import AutoImproveEngine
        from autoflow.apply.applier import ProposalApplier
        from autoflow.apply.git_backend import GitApplyBackend
        from autoflow.apply.policy import ApplyPolicy
        from autoflow.decide.decision_graph import DecisionGraph
        from autoflow.decide.rules import HighErrorRateRetryRule
        from autoflow.evaluate.shadow import ShadowEvaluator
        from autoflow.graph.context_graph import ContextGraphBuilder
        from autoflow.graph.sqlite_store import SQLiteGraphStore
        from autoflow.types import RiskLevel

        self.logger.info("Initializing AutoFlow engine...")

        # Initialize components with tracing
        from autoflow.otel import span

        with span("store.init"):
            self.store = SQLiteGraphStore(db_path=self.config.db_path)

        with span("graph_builder.init"):
            self.graph_builder = ContextGraphBuilder()

        with span("decision_graph.init"):
            self.decision_graph = DecisionGraph(
                rules=[
                    HighErrorRateRetryRule(
                        workflow_id="production_workflow",
                        threshold=5,
                    )
                ]
            )

        with span("evaluator.init"):
            self.evaluator = ShadowEvaluator()

        with span("applier.init"):
            self.applier = ProposalApplier(
                policy=ApplyPolicy(
                    allowed_paths_prefixes=tuple(self.config.allowed_paths),
                    max_risk=RiskLevel[self.config.max_risk],
                ),
                backend=GitApplyBackend(repo_path=Path("/config")),
            )

        with span("engine.init"):
            self.engine = AutoImproveEngine(
                store=self.store,
                graph_builder=self.graph_builder,
                decision_graph=self.decision_graph,
                evaluator=self.evaluator,
                applier=self.applier,
            )

        self.logger.info("AutoFlow engine initialized")

    def start(self):
        """Start the engine."""

        self.logger.info("Starting AutoFlow engine...")

        # Mark as started (startup probe)
        self.health_checker.set_started(True)

        # Mark as ready (readiness probe)
        self.health_checker.set_ready(True)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.logger.info("AutoFlow engine started")

    def stop(self):
        """Stop the engine gracefully."""

        self.logger.info("Stopping AutoFlow engine...")

        # Mark as not ready (stop sending traffic)
        self.health_checker.set_ready(False)

        # Graceful shutdown
        self._shutdown = True

        self.logger.info("AutoFlow engine stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""

        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def ingest_events(self, events: list):
        """Ingest events with batching."""

        if self._shutdown:
            return

        from autoflow.otel import span
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("ingest_events") as span:
            span.set_attribute("event_count", len(events))

            try:
                self.engine.ingest(events)
                self.logger.debug(f"Ingested {len(events)} events")

            except Exception as e:
                self.logger.error(f"Error ingesting events: {e}")
                span.record_exception(e)

    def evaluate_and_propose(self):
        """Generate and evaluate proposals."""

        if self._shutdown:
            return

        from autoflow.otel import span
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("evaluate_and_propose"):
            try:
                # Propose improvements
                proposals = self.engine.propose()

                if not proposals:
                    self.logger.debug("No proposals generated")
                    return

                self.logger.info(f"Generated {len(proposals)} proposal(s)")

                # Evaluate
                results = self.engine.evaluate(proposals)

                passed = sum(1 for r in results if r.passed)
                self.logger.info(f"Evaluation: {passed}/{len(results)} passed")

                # Apply passed proposals
                applied = self.engine.apply(proposals, results)
                self.logger.info(f"Applied {len(applied)} proposal(s)")

                # Export metrics
                self._export_proposal_metrics(proposals, results, applied)

            except Exception as e:
                self.logger.error(f"Error in evaluate_and_propose: {e}")

    def _export_proposal_metrics(self, proposals, results, applied):
        """Export Prometheus metrics for proposals."""

        try:
            from opentelemetry import metrics

            meter = metrics.get_meter(__name__)

            # Create counters
            proposal_counter = meter.create_counter(
                "autoflow.proposals.total",
                description="Total number of proposals"
            )

            applied_counter = meter.create_counter(
                "autoflow.proposals.applied",
                description="Number of proposals applied"
            )

            # Record metrics
            proposal_counter.add(len(proposals))
            applied_counter.add(len(applied))

        except Exception as e:
            self.logger.warning(f"Error exporting metrics: {e}")


# =============================================================================
# HTTP API for Event Ingestion
# =============================================================================

class AutoFlowAPI:
    """
    Simple HTTP API for ingesting events.

    In production, you might use:
    - FastAPI for async performance
    - gRPC for high-throughput
    - Message queue (Kafka, RabbitMQ) for async processing
    """

    def __init__(
        self,
        engine: ProductionAutoFlowEngine,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        self.engine = engine
        self.host = host
        self.port = port

    def start(self):
        """Start HTTP server."""

        try:
            from flask import Flask, request, jsonify
            from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

            app = Flask(__name__)

            # Metrics
            request_counter = Counter(
                'autoflow_api_requests_total',
                'Total API requests',
                ['method', 'endpoint']
            )

            # Health endpoints
            @app.route("/health/live")
            def liveness():
                return {"status": "alive"}, 200

            @app.route("/health/ready")
            def readiness():
                if self.engine.health_checker.is_ready():
                    return {"status": "ready"}, 200
                return {"status": "not_ready"}, 503

            @app.route("/health/startup")
            def startup():
                if self.engine.health_checker.is_started():
                    return {"status": "started"}, 200
                return {"status": "starting"}, 503

            # Metrics endpoint for Prometheus scraping
            @app.route("/metrics")
            def metrics():
                return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

            # Event ingestion endpoint
            @app.route("/api/v1/events", methods=["POST"])
            def ingest_events():
                request_counter.labels(method='POST', endpoint='/events').inc()

                try:
                    events = request.json
                    if not isinstance(events, list):
                        events = [events]

                    self.engine.ingest_events(events)

                    return {"status": "accepted", "count": len(events)}, 202

                except Exception as e:
                    return {"status": "error", "message": str(e)}, 400

            # Run app
            app.run(host=self.host, port=self.port)

        except ImportError:
            print("Flask required for API: pip install flask")


# =============================================================================
# Kubernetes Deployment Manifests
# =============================================================================

def generate_kubernetes_manifests():
    """Generate Kubernetes deployment manifests."""

    manifests = """
# AutoFlow Kubernetes Deployment

---
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: autoflow

---
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoflow-config
  namespace: autoflow
data:
  AUTOFLOW_LOG_LEVEL: "INFO"
  AUTOFLOW_WORKER_THREADS: "4"
  AUTOFLOW_BATCH_SIZE: "100"
  AUTOFLOW_EVALUATION_INTERVAL: "300"
  AUTOFLOW_ALLOWED_PATHS: "config/,prompts/,skills/"
  AUTOFLOW_MAX_RISK: "MEDIUM"
  ENV: "production"
  OTEL_SERVICE_NAME: "autoflow-engine"
  OTEL_SERVICE_VERSION: "1.0.0"

---
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: autoflow-secrets
  namespace: autoflow
type: Opaque
stringData:
  # AWS credentials (if using S3)
  AWS_ACCESS_KEY_ID: "your-access-key"
  AWS_SECRET_ACCESS_KEY: "your-secret-key"
  AWS_REGION: "us-east-1"
  S3_BUCKET: "autoflow-context-prod"

  # Slack (if using Slack integration)
  SLACK_BOT_TOKEN: "xoxb-your-token"

  # OpenTelemetry (if using OTLP)
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://tempo:4317"

---
# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: autoflow-data
  namespace: autoflow
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autoflow-engine
  namespace: autoflow
  labels:
    app: autoflow-engine
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: autoflow-engine
  template:
    metadata:
      labels:
        app: autoflow-engine
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: autoflow
        image: autoflow:latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        env:
        - name: AUTOFLOW_DB_PATH
          value: "/data/autoflow.db"
        envFrom:
        - configMapRef:
            name: autoflow-config
        - secretRef:
            name: autoflow-secrets
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /config
        livenessProbe:
          httpGet:
            path: /health/live
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        startupProbe:
          httpGet:
            path: /health/startup
            port: http
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: autoflow-data
      - name: config
        configMap:
          name: autoflow-config

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: autoflow-engine
  namespace: autoflow
  labels:
    app: autoflow-engine
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: http
    protocol: TCP
    name: http
  selector:
    app: autoflow-engine

---
# ServiceMonitor (for Prometheus Operator)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: autoflow-engine
  namespace: autoflow
spec:
  selector:
    matchLabels:
      app: autoflow-engine
  endpoints:
  - port: http
    path: /metrics
    interval: 30s

---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: autoflow-engine
  namespace: autoflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: autoflow-engine
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30

---
# PodDisruptionBudget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: autoflow-engine
  namespace: autoflow
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: autoflow-engine
"""

    print(manifests)


# =============================================================================
# Dockerfile
# =============================================================================

def generate_dockerfile():
    """Generate Dockerfile for AutoFlow."""

    dockerfile = """
# AutoFlow Production Dockerfile

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 autoflow

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[all]"

# Copy application
COPY src/ ./src/
COPY examples/production/production_deployment.py ./

# Create directories
RUN mkdir -p /data /config \\
    && chown -R autoflow:autoflow /app /data /config

# Switch to app user
USER autoflow

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD curl -f http://localhost:8080/health/live || exit 1

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "production_deployment.py"]
"""

    print(dockerfile)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the production AutoFlow engine."""

    print("=" * 70)
    print("AutoFlow Production Deployment")
    print("=" * 70)
    print()

    # Load configuration
    config = ProductionConfig.from_env()

    # Create health checker
    health_checker = HealthChecker()

    # Create engine
    engine = ProductionAutoFlowEngine(
        config=config,
        health_checker=health_checker,
    )

    # Start engine
    engine.start()

    # Start API (optional)
    if os.getenv("ENABLE_API", "true").lower() == "true":
        api = AutoFlowAPI(engine)
        api.start()

    # Keep running until shutdown
    import time
    while not engine._shutdown:
        time.sleep(1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate-manifests":
        print("=" * 70)
        print("Kubernetes Deployment Manifests")
        print("=" * 70)
        print()
        generate_kubernetes_manifests()

    elif len(sys.argv) > 1 and sys.argv[1] == "generate-dockerfile":
        print("=" * 70)
        print("Dockerfile")
        print("=" * 70)
        print()
        generate_dockerfile()

    else:
        print("=" * 70)
        print("AutoFlow Production Deployment")
        print("=" * 70)
        print()
        print("Usage:")
        print("  python production_deployment.py                # Run engine")
        print("  python production_deployment.py generate-manifests  # Generate K8s manifests")
        print("  python production_deployment.py generate-dockerfile   # Generate Dockerfile")
        print()
        print("Environment Variables:")
        print("  AUTOFLOW_DB_PATH=/data/autoflow.db")
        print("  AUTOFLOW_LOG_LEVEL=INFO")
        print("  AUTOFLOW_WORKER_THREADS=4")
        print("  OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317")
        print("  S3_BUCKET=autoflow-context-prod")
        print("  SLACK_BOT_TOKEN=xoxb-...")
        print()
        print("Quick start:")
        print("  1. Generate manifests: python production_deployment.py generate-manifests > k8s.yaml")
        print("  2. Apply to Kubernetes: kubectl apply -f k8s.yaml")
        print("  3. Check status: kubectl get pods -n autoflow")
