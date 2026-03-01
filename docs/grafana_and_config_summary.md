# Grafana & Configuration Quick Summary

## Quick Answers

### Q1: Can it be used with Grafana Cloud OR locally hosted?

**YES!** AutoFlow works with both:
- ✅ **Local Grafana** (free, self-hosted)
- ✅ **Grafana Cloud** (managed service)

The only difference is one environment variable:

```bash
# Local Grafana
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

# Grafana Cloud
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net:4317"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-creds>"
```

That's it! Everything else works identically.

---

### Q2: How are settings/configurations set when importing the library?

**Multiple ways**, from simple to advanced:

## 1. **Environment Variables** (Simplest)
```bash
export AUTOFLOW_DB_PATH=/data/autoflow.db
export AUTOFLOW_MAX_RISK=MEDIUM
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Then in Python
from autoflow import AutoImproveEngine
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=os.getenv("AUTOFLOW_DB_PATH")),
)
```

## 2. **Configuration File** (Recommended for production)
```yaml
# config/autoflow.yaml
database:
  path: "/data/autoflow.db"

observability:
  enabled: true
  traces:
    endpoint: "http://localhost:4317"
```

```python
import yaml

with open("config/autoflow.yaml") as f:
    config = yaml.safe_load(f)

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=config["database"]["path"]),
)
```

## 3. **Pydantic Settings** (Type-safe, recommended)
```python
from pydantic import BaseModel

class AutoFlowConfig(BaseModel):
    db_path: str = ":memory:"
    otel_endpoint: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AutoFlowConfig":
        return cls(
            db_path=os.getenv("AUTOFLOW_DB_PATH", ":memory:"),
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        )

config = AutoFlowConfig.from_env()
engine = AutoImproveEngine(store=SQLiteGraphStore(db_path=config.db_path))
```

## 4. **Direct Configuration** (Simplest for small apps)
```python
from autoflow import AutoImproveEngine
from autoflow.graph.sqlite_store import SQLiteGraphStore

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path="/data/autoflow.db"),
    graph_builder=ContextGraphBuilder(),
    decision_graph=None,
    evaluator=ShadowEvaluator(),
    applier=None,
)
```

---

## Local Grafana Setup (5 minutes)

### Step 1: Create `docker-compose.yml`

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin

  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
    ports: ["4317:4317", "3200:3200"]
```

### Step 2: Create `tempo.yaml`

```yaml
server:
  http_listen_port: 3200

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
```

### Step 3: Start it

```bash
docker-compose up -d
```

### Step 4: Configure AutoFlow

```python
import os
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

from autoflow import AutoImproveEngine
# ... your code
```

### Step 5: View Traces

1. Open http://localhost:3000 (admin/admin)
2. Add Tempo data source: http://tempo:3200
3. Explore → Tempo → Search traces

---

## Grafana Cloud Setup (2 minutes)

### Step 1: Get Cloud Credentials

1. Go to https://grafana.com/products/cloud/
2. Create stack → Portal → API Keys
3. Copy Instance ID and API Key

### Step 2: Configure AutoFlow

```python
import os
import base64

# Encode credentials
instance_id = "your-instance-id"
api_key = "your-api-key"
credentials = base64.b64encode(f"{instance_id}:{api_key}".encode()).decode()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://otlp-gateway-prod-us-central-0.grafana.net:4317"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {credentials}"

from autoflow import AutoImproveEngine
# ... your code
```

### Step 3: View Traces

1. Log into your Grafana Cloud stack
2. Explore → Tempo
3. Search by `service.name = "autoflow-engine"`

---

## Switching Between Local and Cloud

### Use Environment Variable

```bash
# Development (local)
export ENV=dev
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Production (cloud)
export ENV=prod
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod...grafana.net:4317
export OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic ...
```

### In Python Code

```python
import os

ENV = os.getenv("ENV", "development")

if ENV == "production":
    otel_endpoint = os.getenv("GRAFANA_CLOUD_ENDPOINT")
    otel_headers = os.getenv("GRAFANA_CLOUD_HEADERS")
else:
    otel_endpoint = "http://localhost:4317"
    otel_headers = None

# Use in AutoFlow configuration
```

---

## Minimal Working Example

### For Local Grafana:

```python
# Step 1: Start Grafana + Tempo (see docker-compose above)

# Step 2: Run AutoFlow
import os
from autoflow import AutoImproveEngine
from autoflow.observe.events import make_event

# Point to local Tempo
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

# Create and use engine
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=":memory:"),  # In-memory for testing
)

# Track some events
engine.ingest([
    make_event(source="my_app", name="test_event", attributes={}),
])

# View traces at http://localhost:3000
```

### For Grafana Cloud:

```python
# Step 1: Get credentials from Grafana Cloud

# Step 2: Run AutoFlow
import os
import base64
from autoflow import AutoImproveEngine
from autoflow.observe.events import make_event

# Configure for Grafana Cloud
instance_id = "your-instance-id"
api_key = "your-api-key"
creds = base64.b64encode(f"{instance_id}:{api_key}".encode()).decode()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://otlp-gateway-prod-us-central-0.grafana.net:4317"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {creds}"

# Create and use engine
engine = AutoImproveEngine(store=SQLiteGraphStore(db_path=":memory:"))
engine.ingest([make_event(source="my_app", name="test", attributes={})])

# View traces in your Grafana Cloud stack
```

---

## Summary

✅ **Works with both local and cloud Grafana**
- Just change one endpoint variable
- All features identical

✅ **Flexible configuration**
- Environment variables (simple)
- YAML files (production)
- Pydantic (type-safe)
- Direct Python (for small apps)

✅ **Easy to switch environments**
- Use `ENV` variable
- Load different config files
- Same code, different settings

✅ **Production ready**
- Docker/Kubernetes configs provided
- Health checks included
- Graceful shutdown
- Full observability

---

## Documentation

Full details in:
- `docs/grafana_setup_guide.md` - Complete Grafana setup
- `docs/configuration_guide.md` - All configuration methods
- `examples/README.md` - Example descriptions
- `examples/integrations/observability/otel_grafana_integration.py` - Working code
