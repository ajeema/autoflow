"""
Demonstration of different exporters for Context Graph Framework observability.

Shows how to configure and use:
1. Prometheus file exporter (for scraping)
2. Prometheus HTTP exporter (for web scraping)
3. OTLP exporter (for Alloy, Grafana Cloud, OTEL Collector)
4. Console exporter (for debugging)
5. Composite exporter (multiple backends simultaneously)
"""

from autoflow.context_graph.observability import MetricsRegistry
from autoflow.context_graph.observability_exporters import (
    PrometheusFileExporter,
    PrometheusHTTPExporter,
    OTLPExporter,
    OTLPHTTPExporter,
    ConsoleExporter,
    CompositeExporter,
)
from autoflow.context_graph.observability_config import (
    ObservabilityConfig,
    create_exporter_from_config,
)

print("=" * 70)
print("Context Graph Framework - Exporters Demo")
print("=" * 70)


# ============================================================================
# Example 1: Prometheus File Exporter
# ============================================================================
print("\n=== Example 1: Prometheus File Exporter ===\n")

# Create registry with file exporter
file_exporter = PrometheusFileExporter(filepath="/tmp/prometheus_metrics.prom")
registry1 = MetricsRegistry(exporter=file_exporter)

# Record some metrics
registry1.counter("api_requests_total", tags={"endpoint": "/entities", "method": "GET"})
registry1.gauge("active_connections", 42, tags={"server": "api-1"})
registry1.histogram("request_duration_ms", 45.2, tags={"endpoint": "/entities"})

# Export metrics
registry1.export_metrics()
print(f"✓ Exported metrics to /tmp/prometheus_metrics.prom")

# Show the file content
with open("/tmp/prometheus_metrics.prom", "r") as f:
    print("\nFile contents:")
    for line in f:
        print(f"  {line.rstrip()}")


# ============================================================================
# Example 2: Prometheus HTTP Exporter (for web scraping)
# ============================================================================
print("\n=== Example 2: Prometheus HTTP Exporter ===\n")

# Create registry with HTTP exporter
http_exporter = PrometheusHTTPExporter()
registry2 = MetricsRegistry(exporter=http_exporter)

# Record metrics
registry2.counter("entities_created", tags={"type": "brand"})
registry2.gauge("memory_usage_mb", 128.5)

# Export metrics
registry2.export_metrics()

# Get metrics text for serving via HTTP
metrics_text = http_exporter.get_metrics_text()
print("✓ Metrics ready for HTTP scraping:")
print()
print(metrics_text)


# ============================================================================
# Example 3: OTLP Exporter (for Alloy, Grafana Cloud, OTEL Collector)
# ============================================================================
print("\n=== Example 3: OTLP Exporter ===\n")

# Option A: Full OpenTelemetry SDK exporter
# Uncomment if you have opentelemetry-sdk installed:
# otlp_exporter = OTLPExporter(
#     endpoint="http://localhost:4318",  # Alloy default
#     headers={},  # Add auth headers for Grafana Cloud
#     insecure=True,
# )
# registry3 = MetricsRegistry(exporter=otlp_exporter)

# Option B: Simple HTTP-based OTLP exporter (no OTEL SDK required)
otlp_http_exporter = OTLPHTTPExporter(
    endpoint="http://localhost:4318/v1/metrics",
    headers={"Content-Type": "application/json"},
)
registry3 = MetricsRegistry(exporter=otlp_http_exporter)

# Record metrics
registry3.counter("operations_total", tags={"operation": "traverse", "success": "true"})
registry3.gauge("queue_size", 10)

# Note: This will fail if no OTLP collector is running
try:
    registry3.export_metrics()
    print("✓ Exported metrics via OTLP to http://localhost:4318")
except Exception as e:
    print(f"✗ OTLP export failed (expected if no collector running): {e}")


# ============================================================================
# Example 4: Console Exporter (for debugging)
# ============================================================================
print("\n=== Example 4: Console Exporter (Debugging) ===\n")

console_exporter = ConsoleExporter()
registry4 = MetricsRegistry(exporter=console_exporter)

# Record metrics
registry4.counter("debug_counter", tags={"source": "test"})
registry4.gauge("debug_gauge", 99.9)
registry4.histogram("debug_histogram", 12.3)

# Export metrics (will print to console)
print("Metrics printed to console:")
registry4.export_metrics()


# ============================================================================
# Example 5: Composite Exporter (multiple backends)
# ============================================================================
print("\n=== Example 5: Composite Exporter ===\n")

# Export to multiple backends simultaneously
composite_exporter = CompositeExporter([
    PrometheusFileExporter(filepath="/tmp/metrics_multi.prom"),
    ConsoleExporter(),  # Also print to console for debugging
    # Add OTLP exporter here if needed
])

registry5 = MetricsRegistry(exporter=composite_exporter)

# Record metrics
registry5.counter("multi_backend_counter", tags={"backend": "test"})
registry5.gauge("multi_backend_gauge", 42)

# Export to all backends
registry5.export_metrics()
print("\n✓ Exported to multiple backends:")
print("  - File: /tmp/metrics_multi.prom")
print("  - Console (printed above)")


# ============================================================================
# Example 6: Using Configuration Presets
# ============================================================================
print("\n=== Example 6: Configuration Presets ===\n")

# Development: Console + File
dev_config = ObservabilityConfig.development()
print("Development config:")
print(f"  - Prometheus file: {dev_config.prometheus_file_path}")
print(f"  - Console enabled: {dev_config.console_enabled}")

# Production: Alloy
alloy_config = ObservabilityConfig.production_alloy(
    alloy_endpoint="http://localhost:4318",
    metrics_file="/tmp/alloy_metrics.prom",
)
print("\nAlloy config:")
print(f"  - OTLP endpoint: {alloy_config.otlp_endpoint}")
print(f"  - Metrics file: {alloy_config.prometheus_file_path}")

# Production: Grafana Cloud
grafana_config = ObservabilityConfig.production_grafana_cloud(
    instance_url="https://your-instance.grafana.net",
    api_key="your-api-key",
)
print("\nGrafana Cloud config:")
print(f"  - OTLP endpoint: {grafana_config.otlp_endpoint}")
print(f"  - Headers: {list(grafana_config.otlp_headers.keys())}")

# Production: Prometheus scraping
# Note: In production, use node_exporter path. For demo, use /tmp
print("\nPrometheus config:")
print(f"  - Metrics file: /var/lib/node_exporter/textfile_collector/context_graph.prom")
print("  - (Demo would use: /tmp/prometheus_metrics.prom)")


# ============================================================================
# Example 7: Custom Exporter Setup
# ============================================================================
print("\n=== Example 7: Custom Exporter Setup ===\n")

# Create exporters
custom_exporters = [
    PrometheusFileExporter(filepath="/tmp/custom_metrics.prom"),
    ConsoleExporter(),
]

# Use custom configuration
custom_config = ObservabilityConfig.custom(
    exporters=custom_exporters,
    metrics_enabled=True,
    console_enabled=True,
)

# Create exporter from config
custom_exporter = create_exporter_from_config(custom_config)
registry6 = MetricsRegistry(exporter=custom_exporter)

# Record and export
registry6.counter("custom_counter", tags={"env": "custom"})
registry6.export_metrics()
print("✓ Custom configuration exported")


# ============================================================================
# Example 8: Complete Setup for Production
# ============================================================================
print("\n=== Example 8: Complete Production Setup ===\n")

# Typical production setup with Alloy
def setup_production_observability():
    """
    Setup observability for production with Alloy.

    This setup:
    1. Exports metrics to OTLP for Alloy
    2. Writes to file for Prometheus scraping (backup)
    3. Includes console logging in development
    """
    import os

    # Determine environment
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        # Production: Alloy + file backup
        config = ObservabilityConfig.production_alloy(
            alloy_endpoint="http://alloy:4318",
            metrics_file="/var/lib/node_exporter/textfile_collector/context_graph.prom",
        )
    else:
        # Development: Console + file
        config = ObservabilityConfig.development()

    # Create exporter and registry
    exporter = create_exporter_from_config(config)
    registry = MetricsRegistry(exporter=exporter)

    return registry

# Create production-ready registry
prod_registry = setup_production_observability()

# Use it
prod_registry.counter("app_requests_total", tags={"endpoint": "/api/health"})
prod_registry.gauge("app_uptime_seconds", 3600)
prod_registry.export_metrics()

print("✓ Production-ready observability setup")
print("\n" + "=" * 70)
print("Exporters demo complete!")
print("=" * 70)


# Cleanup
import os
try:
    os.remove("/tmp/prometheus_metrics.prom")
    os.remove("/tmp/metrics_multi.prom")
    os.remove("/tmp/custom_metrics.prom")
except:
    pass
