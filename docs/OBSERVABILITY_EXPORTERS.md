# Observability Exporters Guide

The Context Graph Framework supports flexible, pluggable exporters for metrics and traces. Send observability data to Prometheus, Alloy, Grafana Cloud, OpenTelemetry Collector, or custom backends.

## Quick Start

```python
from autoflow.context_graph.observability import MetricsRegistry
from autoflow.context_graph.observability_config import ObservabilityConfig

# Use a preset configuration
config = ObservabilityConfig.production_alloy()
registry = MetricsRegistry(exporter=create_exporter_from_config(config))

# Record metrics
registry.counter("api_requests_total", tags={"endpoint": "/api/health"})
registry.gauge("active_connections", 42)
registry.histogram("request_duration_ms", 45.2)

# Export to configured backends
registry.export_metrics()
```

## Available Exporters

### 1. Prometheus File Exporter

Write metrics to a file in Prometheus exposition format. Useful for node_exporter textfile collector or local development.

```python
from autoflow.context_graph.observability_exporters import PrometheusFileExporter

exporter = PrometheusFileExporter(filepath="/tmp/metrics.prom")
registry = MetricsRegistry(exporter=exporter)
registry.export_metrics()
```

**Use cases:**
- Local development and testing
- Integration with node_exporter textfile collector
- Debugging metrics format

### 2. Prometheus HTTP Exporter

Store metrics in memory for HTTP scraping. Use with aiohttp, FastAPI, Flask, etc.

```python
from autoflow.context_graph.observability_exporters import PrometheusHTTPExporter

exporter = PrometheusHTTPExporter()
registry = MetricsRegistry(exporter=exporter)

# In your HTTP handler:
async def metrics_handler(request):
    metrics_text = exporter.get_metrics_text()
    return web.Response(text=metrics_text, content_type="text/plain")
```

**Use cases:**
- Exposing /metrics endpoint for Prometheus scraping
- Alloy scraping
- Grafana Cloud on-prem scraping

**Example server:** See `examples/production_setup.py`

### 3. OTLP Exporter (OpenTelemetry)

Export metrics to OTLP-compatible collectors (Alloy, OpenTelemetry Collector, Grafana).

```python
from autoflow.context_graph.observability_exporters import OTLPExporter

exporter = OTLPExporter(
    endpoint="http://localhost:4318",  # Alloy default
    headers={},  # Add auth for Grafana Cloud
    insecure=True,
)
registry = MetricsRegistry(exporter=exporter)
registry.export_metrics()
```

**Requirements:**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

**Use cases:**
- Grafana Alloy (OTLP receiver)
- Grafana Cloud (OTLP endpoint)
- OpenTelemetry Collector
- Any OTLP-compatible backend

### 4. OTLP HTTP Exporter (Simpler)

HTTP-based OTLP export without full OpenTelemetry SDK.

```python
from autoflow.context_graph.observability_exporters import OTLPHTTPExporter

exporter = OTLPHTTPExporter(
    endpoint="http://localhost:4318/v1/metrics",
    headers={"Content-Type": "application/json"},
)
registry = MetricsRegistry(exporter=exporter)
```

**Use cases:**
- Simple OTLP export without OTEL dependencies
- Custom OTLP endpoints
- Testing and development

### 5. Console Exporter

Print metrics to console for debugging.

```python
from autoflow.context_graph.observability_exporters import ConsoleExporter

exporter = ConsoleExporter()
registry = MetricsRegistry(exporter=exporter)
registry.export_metrics()
# Prints:
# [METRIC] api_requests_total, endpoint=/api/health = 1.0 @ 2024-01-01 12:00:00
```

**Use cases:**
- Development and testing
- Debugging metric flow
- Quick verification

### 6. Composite Exporter

Export to multiple backends simultaneously.

```python
from autoflow.context_graph.observability_exporters import CompositeExporter

exporter = CompositeExporter([
    PrometheusHTTPExporter(),  # For scraping
    OTLPExporter(endpoint="http://alloy:4318"),  # For OTLP
    ConsoleExporter(),  # For debugging
])
registry = MetricsRegistry(exporter=exporter)
registry.export_metrics()  # Sends to all three
```

## Configuration Presets

### Development

```python
config = ObservabilityConfig.development()
# - Prometheus file: /tmp/metrics.prom
# - Console enabled: True
```

### Testing

```python
config = ObservabilityConfig.testing()
# - Prometheus file: /tmp/test_metrics.prom
# - Minimal overhead
```

### Production with Alloy

```python
config = ObservabilityConfig.production_alloy(
    alloy_endpoint="http://localhost:4318",
    metrics_file="/var/lib/node_exporter/textfile_collector/context_graph.prom",
)
# - OTLP endpoint: http://localhost:4318
# - File backup for scraping
```

### Production with Grafana Cloud

```python
config = ObservabilityConfig.production_grafana_cloud(
    instance_url="https://your-instance.grafana.net",
    api_key="your-api-key",
)
# - OTLP endpoint with auth
# - Optional local file backup
```

### Production with Prometheus

```python
config = ObservabilityConfig.production_prometheus(
    metrics_file="/var/lib/node_exporter/textfile_collector/context_graph.prom",
)
# - File for node_exporter scraping
```

## Custom Configuration

```python
from autoflow.context_graph.observability_exporters import (
    PrometheusFileExporter,
    OTLPExporter,
    ConsoleExporter,
)

# Create custom exporters
custom_exporters = [
    PrometheusFileExporter(filepath="/tmp/custom.prom"),
    OTLPExporter(endpoint="http://custom-collector:4318"),
    ConsoleExporter(),
]

# Use custom configuration
config = ObservabilityConfig.custom(
    exporters=custom_exporters,
    metrics_enabled=True,
    tracing_enabled=True,
)

# Create registry
registry = MetricsRegistry(exporter=create_exporter_from_config(config))
```

## Integration with Web Frameworks

### aiohttp

```python
from aiohttp import web
from autoflow.context_graph.observability_exporters import PrometheusHTTPExporter

exporter = PrometheusHTTPExporter()
registry = MetricsRegistry(exporter=exporter)

async def metrics_handler(request):
    metrics_text = exporter.get_metrics_text()
    return web.Response(text=metrics_text, content_type="text/plain")

app = web.Application()
app.router.add_get("/metrics", metrics_handler)
```

### FastAPI

```python
from fastapi import FastAPI
from autoflow.context_graph.observability_exporters import PrometheusHTTPExporter

exporter = PrometheusHTTPExporter()
registry = MetricsRegistry(exporter=exporter)

app = FastAPI()

@app.get("/metrics")
def metrics():
    from fastapi.responses import Response
    metrics_text = exporter.get_metrics_text()
    return Response(content=metrics_text, media_type="text/plain")
```

### Flask

```python
from flask import Flask, Response
from autoflow.context_graph.observability_exporters import PrometheusHTTPExporter

exporter = PrometheusHTTPExporter()
registry = MetricsRegistry(exporter=exporter)

app = Flask(__name__)

@app.route("/metrics")
def metrics():
    metrics_text = exporter.get_metrics_text()
    return Response(metrics_text, mimetype="text/plain")
```

## Alloy Configuration

Configure Alloy to scrape metrics or receive OTLP:

### Scraping Prometheus Endpoint

```alloy
prometheus.scrape "context_graph" {
  targets = [{
    __address__ = "localhost:9090",
  }]

  forward_to = [prometheus.remote_write.metrics_service]
}
```

### OTLP Receiver

```alloy
otelcol.receiver.otlp "default" {
  grpc {
    endpoint = "0.0.0.0:4318"
  }

  output {
    metrics = [otelcol.processor.batch.metrics.output]
    traces  = [otelcol.processor.batch.traces.output]
  }
}
```

## Grafana Cloud Setup

1. **Get your instance URL and API key** from Grafana Cloud portal

2. **Configure exporter:**
```python
config = ObservabilityConfig.production_grafana_cloud(
    instance_url="https://your-instance.grafana.net",
    api_key="your-api-key",
)
registry = MetricsRegistry(exporter=create_exporter_from_config(config))
```

3. **View metrics in Grafana:**
- Metrics appear in Grafana Cloud
- Use Explore to query
- Build dashboards with your metrics

## Creating Custom Exporters

Implement the `Exporter` protocol:

```python
from typing import Protocol
from autoflow.context_graph.observability_exporters import MetricPoint, Span

class MetricsExporter(Protocol):
    def export_metrics(self, metrics: list[MetricPoint]) -> None:
        """Export metrics to your backend."""
        ...

    def export_spans(self, spans: list[Span]) -> None:
        """Export spans to your backend."""
        ...

    def shutdown(self) -> None:
        """Cleanup."""
        ...
```

## Best Practices

1. **Use CompositeExporter in production** - Export to multiple backends for redundancy
2. **Set appropriate scrape intervals** - Match your exporter flush rate
3. **Monitor exporter health** - Check for connection failures
4. **Use tags consistently** - Helps with querying and aggregation
5. **Test exporters locally** - Use ConsoleExporter for debugging
6. **Graceful shutdown** - Call `registry.shutdown_exporter()` on exit

## Examples

- `examples/exporters_demo.py` - All exporters demonstrated
- `examples/production_setup.py` - Production HTTP server with metrics
- `examples/observability_demo.py` - Full observability features

## Troubleshooting

**Metrics not appearing:**
- Check exporter is enabled: `exporter.enabled`
- Verify endpoint is reachable
- Check logs for errors
- Use ConsoleExporter to verify metrics are being created

**OTLP connection refused:**
- Ensure collector is running: `docker run -p 4318:4318 grafana/alloy`
- Check endpoint URL
- Verify firewall rules

**Prometheus not scraping:**
- Check /metrics endpoint is accessible
- Verify content-type is `text/plain`
- Check Prometheus scrape config
