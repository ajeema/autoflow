# Grafana Setup Guide: Cloud vs Local

This guide shows how to configure AutoFlow with both Grafana Cloud and local Grafana instances.

## Option 1: Local Grafana Stack (Free, Self-Hosted)

### Quick Start with Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  # Grafana - Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - tempo
      - loki
      - prometheus

  # Tempo - Distributed Tracing
  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "4317:4317"  # OTLP gRPC receiver
      - "4318:4318"  # OTLP HTTP receiver
      - "3200:3200"  # Tempo query API

  # Loki - Log Aggregation
  loki:
    image: grafana/loki:latest
    command: ["-config.file=/etc/loki/local-config.yaml"]
    ports:
      - "3100:3100"  # Loki API
    volumes:
      - loki-data:/loki

  # Prometheus - Metrics
  prometheus:
    image: prom/prometheus:latest
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  # Grafana Agent/Alloy - Collects and ships telemetry
  alloy:
    image: grafana/alloy:latest
    command: ["run", "/etc/alloy/config.alloy"]
    volumes:
      - ./alloy-config.alloy:/etc/alloy/config.alloy
    ports:
      - "12345:12345"  # Alloy HTTP server
    depends_on:
      - tempo
      - loki
      - prometheus

volumes:
  grafana-data:
  tempo-data:
  loki-data:
  prometheus-data:
```

### Tempo Configuration (`tempo.yaml`):

```yaml
server:
  http_listen_port: 3200

distributions:
  service_name_mappings:
    service_name: autoflow-engine

compactor:
  compaction:
    block_retention: 24h

overrides:
  defaults:
    global:
      metrics_active:
        reporting_interval: 10s

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:

exporters:
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
```

### Alloy Configuration (`alloy-config.alloy`):

```alloy
// AutoFlow Telemetry Collection with Alloy

// Receive OTLP from AutoFlow
otelcol.receiver.otlp "default" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }

  output -> otelcol.processor.batch.default.input
}

// Batch processing
otelcol.processor.batch "default" {
  timeout = 5s

  output -> otelcol.exporter.otlp "tempo".input
             -> otelcol.exporter.otlp "prometheus".input
             -> otelcol.exporter.loki "default".input
}

// Export traces to Tempo
otelcol.exporter.otlp "tempo" {
  endpoint = "tempo:4317"
  insecure = true

  output -> <discard>
}

// Export metrics to Prometheus
otelcol.exporter.otlp "prometheus" {
  endpoint = "prometheus:9090/api/v1/otlp"
  insecure = true

  output -> <discard>
}

// Export logs to Loki
otelcol.exporter.loki "default" {
  endpoint = "http://loki:3100/loki/api/v1/push"

  output -> <discard>
}
```

### Start the Stack:

```bash
# Start all services
docker-compose up -d

# Check they're running
docker-compose ps

# View logs
docker-compose logs -f grafana
```

### Access Local Grafana:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200
- **Loki**: http://localhost:3100

### Configure AutoFlow for Local Grafana:

```python
import os

# For local Grafana with Tempo
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
os.environ["OTEL_SERVICE_NAME"] = "autoflow-engine"

# Run AutoFlow - traces will go to local Tempo
from autoflow import AutoImproveEngine

# ... your AutoFlow code
```

### Add Tempo as Data Source in Grafana:

1. Go to http://localhost:3000
2. Configuration → Data Sources → Add data source
3. Select "Tempo"
4. URL: `http://tempo:3200`
5. Click "Save & Test"

### View Traces in Local Grafana:

1. Go to Explore → Select Tempo
2. Search by: `service.name = "autoflow-engine"`
3. Click on traces to see detailed spans

---

## Option 2: Grafana Cloud (Managed Service)

### Get Grafana Cloud Credentials:

1. Sign up at https://grafana.com/products/cloud/
2. Create a new stack
3. Go to your stack → Portal → API Keys
4. Create a new API key with appropriate permissions

### Configure for Grafana Cloud:

```python
import os

# Grafana Cloud OTLP endpoint
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://otlp-gateway-prod-us-central-0.grafana.net:4317"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = "Authorization=Basic <your-base64-encoded-credentials>"

# Or more explicitly:
import base64
instance_id = "your-instance-id"
api_key = "your-api-key"
credentials = base64.b64encode(f"{instance_id}:{api_key}".encode()).decode()

os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {credentials}"
os.environ["OTEL_SERVICE_NAME"] = "autoflow-engine"
os.environ["OTEL_SERVICE_VERSION"] = "1.0.0"
os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "deployment.environment=production"

# Run AutoFlow - traces will go to Grafana Cloud
from autoflow import AutoImproveEngine

# ... your AutoFlow code
```

### Base64 Encode Credentials:

```bash
# In terminal
echo -n "your-instance-id:your-api-key" | base64
```

---

## Configuration Comparison

| Feature | Local Grafana | Grafana Cloud |
|---------|--------------|---------------|
| **Cost** | Free | Paid (with free tier) |
| **Setup** | Docker compose | Just set endpoint |
| **Maintenance** | Self-managed | Managed by Grafana |
| **Scalability** | Limited by hardware | Unlimited |
| **Data Retention** | Configurable | Up to plan limits |
| **OTLP Endpoint** | `http://localhost:4317` | `https://otlp-gateway-...grafana.net:4317` |
| **Authentication** | None (or basic) | API key in headers |

---

## Switching Between Local and Cloud

### Environment-Based Configuration:

```python
import os

def configure_otel():
    """Configure OpenTelemetry based on environment."""

    env = os.getenv("ENV", "development")

    if env == "production":
        # Grafana Cloud
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.getenv(
            "GRAFANA_CLOUD_OTLP_ENDPOINT",
            "https://otlp-gateway-prod-us-central-0.grafana.net:4317"
        )
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = os.getenv("GRAFANA_CLOUD_HEADERS")
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "deployment.environment=production"

    elif env == "staging":
        # Grafana Cloud staging
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.getenv("GRAFANA_STAGING_ENDPOINT")

    else:
        # Local development
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "deployment.environment=development"

    print(f"OpenTelemetry configured for {env}")
    print(f"  Endpoint: {os.environ['OTEL_EXPORTER_OTLP_ENDPOINT']}")

# Use it
configure_otel()

from autoflow import AutoImproveEngine

# ... rest of code
```

### Using a Configuration File:

Create `config/observability.yaml`:

```yaml
development:
  otlp_endpoint: "http://localhost:4317"
  resource_attributes:
    deployment.environment: "development"

staging:
  otlp_endpoint: "https://otlp-gateway-staging.grafana.net:4317"
  otlp_headers: "${GRAFANA_STAGING_HEADERS}"
  resource_attributes:
    deployment.environment: "staging"

production:
  otlp_endpoint: "https://otlp-gateway-prod-us-central-0.grafana.net:4317"
  otlp_headers: "${GRAFANA_CLOUD_HEADERS}"
  resource_attributes:
    deployment.environment: "production"
    service.namespace: "production"
```

Load and apply:

```python
import yaml
import os

def load_config(env="development"):
    with open(f"config/observability.yaml") as f:
        config = yaml.safe_load(f)

    env_config = config[env]

    # Apply configuration
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = env_config["otlp_endpoint"]

    if "otlp_headers" in env_config:
        headers = env_config["otlp_headers"]
        # Expand environment variables
        if headers.startswith("${"):
            var_name = headers[2:-1]
            headers = os.getenv(var_name, "")
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = headers

    for attr, value in env_config.get("resource_attributes", {}).items():
        os.environ[f"OTEL_RESOURCE_{attr.upper().replace('.', '_')}"] = str(value)

# Use
load_config(env=os.getenv("ENV", "development"))
```

---

## Quick Testing

### Test Local Setup:

```bash
# 1. Start Grafana stack
docker-compose up -d

# 2. Wait for services to be ready
sleep 10

# 3. Run AutoFlow with local endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python your_autoflow_script.py

# 4. View traces in Grafana
# Open http://localhost:3000
# Go to Explore → Tempo
# Search: service.name = "autoflow-engine"
```

### Test Grafana Cloud Setup:

```bash
# 1. Set credentials
export GRAFANA_CLOUD_INSTANCE_ID="your-instance-id"
export GRAFANA_CLOUD_API_KEY="your-api-key"

# 2. Encode credentials
CREDENTIALS=$(echo -n "${GRAFANA_CLOUD_INSTANCE_ID}:${GRAFANA_CLOUD_API_KEY}" | base64)
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net:4317"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic ${CREDENTIALS}"

# 3. Run AutoFlow
python your_autoflow_script.py

# 4. View traces in your Grafana Cloud stack
```

---

## Troubleshooting

### Local Grafana:

**Problem**: No traces appearing
```bash
# Check if Tempo is receiving traces
docker-compose logs tempo | grep "Received batch"

# Check OTLP endpoint
curl http://localhost:4317

# Verify AutoFlow is sending
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python -c "from opentelemetry import trace; print(trace.get_tracer())"
```

### Grafana Cloud:

**Problem**: Authentication errors
```bash
# Test credentials
# Decode your base64 to verify
echo "your-base64-credentials" | base64 -d

# Should show: instance-id:api-key
```

**Problem**: No traces in cloud
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Verify endpoint and headers are set
import os
print(f"Endpoint: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')}")
print(f"Headers: {os.getenv('OTEL_EXPORTER_OTLP_HEADERS')}")
```

---

## Dashboard Import

### Import AutoFlow Dashboard in Grafana:

1. Go to Dashboards → Import
2. Select "Import via panel json"
3. Paste this dashboard JSON:

```json
{
  "dashboard": {
    "title": "AutoFlow Performance",
    "description": "AutoFlow engine performance and proposals",
    "tags": ["autoflow", "ai", "workflows"],
    "timezone": "browser",
    "schemaVersion": 38,
    "version": 1,
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "title": "Workflow Executions",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "rate(autoflow_workflow_runs_total[5m])",
            "legendFormat": "{{workflow_id}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Proposal Success Rate",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "autoflow_proposals_applied_total / autoflow_proposals_total"
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
            "expr": "{source=\"autoflow-engine\"}",
            "refId": "A"
          }
        ]
      }
    ]
  }
}
```

This will work identically in both local and cloud Grafana!
