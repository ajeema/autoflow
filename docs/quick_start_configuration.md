# AutoFlow Configuration - Quick Start Guide

## Super Simple (5 seconds)

```python
from autoflow.config import get_config

# Load all settings from environment
config = get_config()

# Use config
print(f"Database: {config.database.url}")
print(f"Tracing: {config.observability.otel_enabled}")
```

That's it! All `AUTOFLOW_*` environment variables are automatically loaded.

---

## Environment-Based Quick Start

### Development (Local)

```bash
# .env file
AUTOFLOW_ENVIRONMENT=development
AUTOFLOW_DB_PATH=:memory:
AUTOFLOW_LOG_LEVEL=DEBUG
AUTOFLOW_POLICY_MAX_RISK=HIGH
AUTOFLOW_POLICY_DRY_RUN=true
```

```python
from autoflow.config import get_config, ConfigProfiles

# Option 1: Load from environment
config = get_config()

# Option 2: Use preset
config = ConfigProfiles.development()
```

### Production (PostgreSQL + Grafana Cloud)

```bash
# Environment variables
export AUTOFLOW_ENVIRONMENT=production
export AUTOFLOW_DB_TYPE=postgresql
export AUTOFLOW_POSTGRES_HOST=db.prod.example.com
export AUTOFLOW_POSTGRES_DATABASE=autoflow_prod
export AUTOFLOW_POSTGRES_USER=autoflow_user
export AUTOFLOW_POSTGRES_PASSWORD=${AUTOFLOW_DB_PASSWORD}
export AUTOFLOW_POSTGRES_POOL_SIZE=20

# Observability
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=autoflow-engine
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic ${GRAFANA_CLOUD_CREDS}"

# Policy
export AUTOFLOW_POLICY_ALLOWED_PATHS=config/,prompts/
export AUTOFLOW_POLICY_MAX_RISK=LOW
export AUTOFLOW_POLICY_REQUIRE_APPROVAL=true

# Vector DB
export AUTOFLOW_PINECONE_ENABLED=true
export AUTOFLOW_PINECONE_API_KEY=${PINECONE_API_KEY}
```

```python
from autoflow.config import get_config

config = get_config()
setup = config.setup_observability()
```

### Testing

```bash
export AUTOFLOW_ENVIRONMENT=test
export AUTOFLOW_DB_PATH=:memory:
AUTOFLOW_LOG_LEVEL=WARNING
```

---

## Configuration by Feature

### Vector Database Integration

#### Pinecone (Cloud)

```bash
export AUTOFLOW_PINECONE_ENABLED=true
export AUTOFLOW_PINECONE_API_KEY=your-api-key
export AUTOFLOW_PINECONE_ENVIRONMENT=us-west1-gcp
export AUTOFLOW_PINECONE_INDEX_PREFIX=autoflow-prod
```

#### ChromaDB (Local, Free)

```bash
export AUTOFLOW_CHROMADB_ENABLED=true
export AUTOFLOW_CHROMADB_PATH=./chroma_db
```

#### Weaviate (Self-hosted)

```bash
export AUTOFLOW_WEAVIATE_ENABLED=true
export AUTOFLOW_WEAVIATE_URL=http://localhost:8080
```

```python
from autoflow.config import get_config

config = get_config()

# Access vector DB config
if config.vector_db.pinecone_enabled:
    print("Using Pinecone")
    print(f"Environment: {config.vector_db.pinecone_environment}")
```

---

### Message Queue Integration

#### Kafka

```bash
export AUTOFLOW_KAFKA_ENABLED=true
export AUTOFLOW_KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092
export AUTOFLOW_KAFKA_TOPIC_PREFIX=autoflow-prod
```

#### RabbitMQ

```bash
export AUTOFLOW_RABBITMQ_ENABLED=true
export AUTOFLOW_RABBITMQ_URL=amqp://guest:guest@localhost:5672
```

#### AWS SQS

```bash
export AUTOFLOW_SQS_ENABLED=true
export AUTOFLOW_SQS_REGION=us-east-1
export AUTOFLOW_SQS_QUEUE_PREFIX=autoflow
```

---

### Cloud Storage Integration

#### AWS S3

```bash
export AUTOFLOW_S3_ENABLED=true
export AUTOFLOW_S3_BUCKET=autoflow-prod-context
export AUTOFLOW_S3_REGION=us-east-1
export AUTOFLOW_S3_PREFIX=autoflow/prod/
```

#### Google Cloud Storage

```bash
export AUTOFLOW_GCS_ENABLED=true
export AUTOFLOW_GCS_BUCKET=autoflow-context
export AUTOFLOW_GCS_CREDENTIALS_PATH=/path/to/service-account.json
```

#### MinIO (Local S3-compatible)

```bash
export AUTOFLOW_MINIO_ENABLED=true
export AUTOFLOW_MINIO_ENDPOINT=http://localhost:9000
export AUTOFLOW_MINIO_ACCESS_KEY=minioadmin
export AUTOFLOW_MINIO_SECRET_KEY=minioadmin
```

```python
from autoflow.config import get_config

config = get_config()

# Access S3 config
if config.s3.enabled:
    print(f"Using S3 bucket: {config.s3.bucket}")
```

---

### Communication Integration

#### Slack

```bash
export AUTOFLOW_SLACK_ENABLED=true
export AUTOFLOW_SLACK_BOT_TOKEN=xoxb-your-token
export AUTOFLOW_SLACK_CHANNEL=#autoflow-alerts
```

#### Discord

```bash
export AUTOFLOW_DISCORD_ENABLED=true
export AUTOFLOW_DISCORD_BOT_TOKEN=your-bot-token
export AUTOFLOW_DISCORD_CHANNEL_ID=your-channel-id
```

#### Email

```bash
export AUTOFLOW_EMAIL_ENABLED=true
export AUTOFLOW_EMAIL_SMTP_HOST=smtp.example.com
export AUTOFLOW_EMAIL_USERNAME=alerts@example.com
export AUTOFLOW_EMAIL_PASSWORD=your-password
export AUTOFLOW_EMAIL_FROM=autoflow@example.com
```

```python
from autoflow.config import get_config

config = get_config()

# Access Slack config
if config.slack.enabled:
    print(f"Posting to Slack: {config.slack.channel}")
```

---

### Observability Options

#### Local Grafana (Docker Compose)

```bash
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=autoflow-engine
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

#### Grafana Cloud

```bash
export OTEL_ENABLED=true
export GRAFANA_CLOUD_INSTANCE_ID=your-instance
export GRAFANA_CLOUD_API_KEY=your-api-key
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
```

#### Or use OTEL standard variables

```bash
export OTEL_SERVICE_NAME=autoflow-engine
export OTEL_SERVICE_VERSION=1.0.0
export OTEL_EXPORTER_OTLP_ENDPOINT=https://tempo.example.com:4317
export OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic creds
export OTEL_TRACES_SAMPLER=always_on
export OTEL_BSP_SCHEDULE_DELAY_MILLIS=5000
```

```python
from autoflow.config import get_config, setup_autoflow

config = get_config()
setup_autoflow(config)  # Sets up logging, tracing, metrics
```

---

## Database Options

### SQLite (Default)

```bash
export AUTOFLOW_DB_TYPE=sqlite
export AUTOFLOW_DB_PATH=/data/autoflow.db
```

### PostgreSQL

```bash
export AUTOFLOW_DB_TYPE=postgresql
export AUTOFLOW_POSTGRES_HOST=db.example.com
export AUTOFLOW_POSTGRES_PORT=5432
export AUTOFLOW_POSTGRES_DATABASE=autoflow
export AUTOFLOW_POSTGRES_USER=autoflow
export AUTOFLOW_POSTGRES_PASSWORD=secret
export AUTOFLOW_POSTGRES_POOL_SIZE=20
```

### MySQL

```bash
export AUTOFLOW_DB_TYPE=mysql
export AUTOFLOW_MYSQL_HOST=mysql.example.com
export AUTOFLOW_MYSQL_PORT=3306
export AUTOFLOW_MYSQL_DATABASE=autoflow
export AUTOFLOW_MYSQL_USER=autoflow
export AUTOFLOW_MYSQL_PASSWORD=secret
```

### Redis

```bash
export AUTOFLOW_REDIS_HOST=localhost
export AUTOFLOW_REDIS_PORT=6379
export AUTOFLOW_REDIS_DB=0
export AUTOFLOW_REDIS_PASSWORD=secret
```

### MongoDB

```bash
export AUTOFLOW_MONGODB_HOST=mongodb.example.com
export AUTOFLOW_MONGODB_PORT=27017
export AUTOFLOW_MONGODB_DATABASE=autoflow
export AUTOFLOW_MONGODB_USER=user
export AUTOFLOW_MONGODB_PASSWORD=secret
```

```python
from autoflow.config import get_config

config = get_config()

# Database connection URL
print(f"Database URL: {config.database.url}")

# Check SSL
if config.database.is_ssl_enabled():
    print("SSL is enabled")
```

---

## Using Configuration in Code

### Basic Usage

```python
from autoflow.config import get_config
from autoflow import AutoImproveEngine
from autoflow.graph.sqlite_store import SQLiteGraphStore

# Load configuration
config = get_config()

# Setup observability (logging, tracing, metrics)
config.setup_observability()

# Create engine with config
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=config.database.path),
    # ... other components
)

# Use other config values
print(f"Workflow: {config.workflow_id}")
print(f"Max risk: {config.policy.max_risk}")
print(f"Batch size: {config.performance.batch_size}")
```

### Using Specific Section

```python
from autoflow.config import (
    DatabaseConfig,
    ObservabilityConfig,
    PolicyConfig,
)

# Load just what you need
db_config = DatabaseConfig.from_env()
otel_config = ObservabilityConfig.from_env()
policy_config = PolicyConfig.from_env()

print(f"Database: {db_config.url}")
print(f"Tracing: {otel_config.otel_enabled}")
print(f"Max risk: {policy_config.max_risk}")
```

### Using Presets

```python
from autoflow.config import ConfigProfiles

# Development preset
config = ConfigProfiles.development()

# Testing preset
config = ConfigProfiles.testing()

# Production preset
config = ConfigProfiles.production()

# Serverless preset (AWS Lambda)
config = ConfigProfiles.serverless()
```

---

## Advanced: Multiple Environments

### Directory Structure

```
project/
├── config/
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
└── .env.development
```

### Development Configuration

```yaml
# config/development.yaml
database:
  type: sqlite
  path: ":memory:"

policy:
  max_risk: "HIGH"
  dry_run: true

observability:
  enabled: false

logging:
  level: "DEBUG"
```

```bash
# .env.development
export AUTOFLOW_CONFIG_FILE=config/development.yaml
```

### Production Configuration

```yaml
# config/production.yaml
database:
  type: postgresql
  postgres_host: ${POSTGRES_HOST}
  postgres_database: ${POSTGRES_DATABASE}
  pool_size: 20

observability:
  enabled: true
  otel_enabled: true

policy:
  max_risk: "LOW"
  require_approval: true
```

```bash
# .env.production
export AUTOFLOW_CONFIG_FILE=config/production.yaml
export POSTGRES_HOST=db.prod.example.com
export POSTGRES_DATABASE=autoflow_prod
export GRAFANA_CLOUD_API_KEY=${GRAFANA_API_KEY}
```

### Load in Code

```python
import os
from autoflow.config import AutoFlowConfig

# Load from config file if specified
config_file = os.getenv("AUTOFLOW_CONFIG_FILE")
if config_file:
    config = AutoFlowConfig.from_yaml(config_file)
else:
    # Fall back to environment variables
    config = AutoFlowConfig.from_env()

# Override with environment if needed
if os.getenv("OVERRIDE_OTEL_ENDPOINT"):
    config.observability.otel_exporter_otlp_endpoint = os.getenv("OVERRIDE_OTEL_ENDPOINT")

# Setup
config.setup_observability()
```

---

## Docker/Kubernetes Usage

### Dockerfile

```dockerfile
# Set environment at build time
ENV AUTOFLOW_ENVIRONMENT=production
ENV AUTOFLOW_LOG_LEVEL=INFO

# Override at runtime
ENV AUTOFLOW_POSTGRES_HOST=${POSTGRES_HOST}
ENV AUTOFLOW_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

### docker-compose.yml

```yaml
services:
  autoflow:
    image: autoflow:latest
    environment:
      - AUTOFLOW_ENVIRONMENT=production
      - AUTOFLOW_POSTGRES_HOST=db
      - AUTOFLOW_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
      - AUTOFLOW_S3_BUCKET=autoflow-context
    env_file:
      - .env.production
```

### Kubernetes ConfigMap + Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoflow-config
data:
  AUTOFLOW_ENVIRONMENT: "production"
  AUTOFLOW_LOG_LEVEL: "INFO"
  AUTOFLOW_POLICY_ALLOWED_PATHS: "config/,prompts/"
---
apiVersion: v1
kind: Secret
metadata:
  name: autoflow-secrets
type: Opaque
stringData:
  AUTOFLOW_POSTGRES_PASSWORD: "prod-password"
  AUTOFLOW_PINECONE_API_KEY: "pinecone-key"
  SLACK_BOT_TOKEN: "xoxb-token"
```

```yaml
apiVersion: v1
kind: Deployment
metadata:
  name: autoflow
spec:
  template:
    spec:
      containers:
      - name: autoflow
        env:
        - name: AUTOFLOW_ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: autoflow-config
              key: AUTOFLOW_ENVIRONMENT
        - name: AUTOFLOW_POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: autoflow-secrets
              key: AUTOFLOW_POSTGRES_PASSWORD
```

---

## Complete Examples

### Example 1: Local Development with ChromaDB

```bash
# .env
AUTOFLOW_ENVIRONMENT=development
AUTOFLOW_DB_PATH=:memory:
AUTOFLOW_LOG_LEVEL=DEBUG
AUTOFLOW_CHROMADB_ENABLED=true
AUTOFLOW_CHROMADB_PATH=./chroma_db
```

```python
from autoflow.config import get_config
from autoflow import AutoImproveEngine

config = get_config()
print(f"Using ChromaDB: {config.vector_db.chromadb_enabled}")

# ChromaDB is now configured
# Use it in your vector context source
```

### Example 2: Production with Full Stack

```bash
#!/bin/bash
# setup_prod.sh

# Core
export AUTOFLOW_ENVIRONMENT=production
export AUTOFLOW_WORKFLOW_ID=ml-pipeline

# Database
export AUTOFLOW_DB_TYPE=postgresql
export AUTOFLOW_POSTGRES_HOST=db.prod.svc.cluster.local
export AUTOFLOW_POSTGRES_PORT=5432
export AUTOFLOW_POSTGRES_DATABASE=autoflow_prod
export AUTOFLOW_POSTGRES_USER=autoflow_user
export AUTOFLOW_POSTGRES_PASSWORD=${AUTOFLOW_DB_PASSWORD}
export AUTOFLOW_POSTGRES_POOL_SIZE=20

# Vector DB (Pinecone)
export AUTOFLOW_PINECONE_ENABLED=true
export AUTOFLOW_PINECONE_API_KEY=${PINECONE_API_KEY}
export AUTOFLOW_PINECONE_ENVIRONMENT=us-west1-gcp

# S3
export AUTOFLOW_S3_ENABLED=true
export AUTOFLOW_S3_BUCKET=autoflow-prod-context

# Kafka
export AUTOFLOW_KAFKA_ENABLED=true
export AUTOFLOW_KAFKA_BOOTSTRAP_SERVERS=kafka-0.kafka.svc.cluster.local:9092

# Slack
export AUTOFLOW_SLACK_ENABLED=true
export AUTOFLOW_SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
export AUTOFLOW_SLACK_CHANNEL=#autoflow-alerts

# Observability (Grafana Cloud)
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=autoflow-engine
export OTEL_SERVICE_VERSION=1.0.0
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
export GRAFANA_CLOUD_INSTANCE_ID=${GRAFANA_INSTANCE}
export GRAFANA_CLOUD_API_KEY=${GRAFANA_API_KEY}

# Policy
export AUTOFLOW_POLICY_ALLOWED_PATHS=config/,prompts/,skills/
export AUTOFLOW_POLICY_MAX_RISK=LOW
export AUTOFLOW_POLICY_REQUIRE_APPROVAL=true

# Performance
export AUTOFLOW_BATCH_SIZE=500
export AUTOFLOW_WORKER_THREADS=16
```

```python
# prod_app.py
from autoflow.config import get_config, setup_autoflow
from autoflow import AutoImproveEngine

# Load production config
config = get_config()
setup_autoflow(config)

# Create engine
engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=config.database.path),
    # ... other components
)

# Everything is configured!
# - PostgreSQL connection pooling
# - Pinecone vector search
# - S3 archival
# - Kafka event streaming
# - Slack notifications
# - Grafana Cloud tracing
```

---

## Secret Management

### Using dotenv (Local Development)

```bash
# .env (never commit)
AUTOFLOW_POSTGRES_PASSWORD=secret
AUTOFLOW_PINECONE_API_KEY=your-key
SLACK_BOT_TOKEN=xoxb-token
```

```python
from dotenv import load_dotenv
from autoflow.config import get_config

# Load .env file
load_dotenv()

# Load config (will pick up .env values)
config = get_config()
```

### Using AWS Secrets Manager (Production)

```bash
export AUTOFLOW_POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value --secret-id autoflow/db-password --query SecretString --output text)
export AUTOFLOW_PINECONE_API_KEY=$(aws secretsmanager get-secret-value --secret-id autoflow/pinecone --query SecretString --output text)
```

### Using Kubernetes Secrets

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: autoflow-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
  target:
    name: autoflow-secrets
    creationPolicy: Owner
  data:
  - secretKey: AUTOFLOW_POSTGRES_PASSWORD
    remoteRef:
      key: autoflow/db-password
  - secretKey: AUTOFLOW_PINECONE_API_KEY
    remoteRef:
      key: autoflow/pinecone
```

---

## Validation

Configuration is automatically validated:

```python
from autoflow.config import get_config

config = get_config()

# Validate configuration
errors = config.validate()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  ✗ {error}")
    sys.exit(1)

print("✓ Configuration is valid!")
```

---

## Quick Reference Cards

### Card 1: Basic Setup

```python
from autoflow.config import get_config, setup_autoflow

config = get_config()
setup_autoflow(config)
```

### Card 2: Production

```bash
# Environment
export AUTOFLOW_ENVIRONMENT=production
export AUTOFLOW_POSTGRES_HOST=db.prod.com
export AUTOFLOW_POSTGRES_PASSWORD=${DB_PASSWORD}
export OTEL_EXPORTER_OTLP_ENDPOINT=https://grafana.com:4317
```

### Card 3: Vector DB

```bash
# Pinecone
export AUTOFLOW_PINECONE_ENABLED=true
export AUTOFLOW_PINECONE_API_KEY=${KEY}

# ChromaDB
export AUTOFLOW_CHROMADB_ENABLED=true
export AUTOFLOW_CHROMADB_PATH=./chroma_db
```

### Card 4: Observability

```bash
# Local
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Cloud
export OTEL_ENABLED=true
export GRAFANA_CLOUD_INSTANCE_ID=${INSTANCE}
export GRAFANA_CLOUD_API_KEY=${KEY}
```

---

## Checklist for New Setup

- [ ] Set `AUTOFLOW_ENVIRONMENT` (development/staging/production)
- [ ] Configure database (type, host, credentials)
- [ ] Set log level (`AUTOFLOW_LOG_LEVEL`)
- [ ] Configure policy (`AUTOFLOW_POLICY_MAX_RISK`)
- [ ] Enable integrations (S3, Slack, vector DB, etc.)
- [ ] Configure observability (OTEL endpoint, Grafana)
- [ ] Validate configuration with `config.validate()`
- [ ] Test with dry-run mode first

---

## Troubleshooting

### Problem: Configuration not loading

```python
import os
from autoflow.config import get_config

# Check environment variables are set
print("AUTOFLOW_ENVIRONMENT:", os.getenv("AUTOFLOW_ENVIRONMENT"))
print("AUTOFLOW_DB_TYPE:", os.getenv("AUTOFLOW_DB_TYPE"))

# Load config
config = get_config()
print("Loaded:", config.environment)
```

### Problem: Database connection failing

```python
from autoflow.config import get_config

config = get_config()

# Check URL
print("Database URL:", config.database.url)

# Check SSL
print("SSL enabled:", config.database.is_ssl_enabled())

# Test connection
try:
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    store = SQLiteGraphStore(db_path=config.database.path)
    print("✓ Database connection works")
except Exception as e:
    print(f"✗ Database error: {e}")
```

### Problem: Traces not appearing in Grafana

```bash
# Check endpoint
echo "OTEL endpoint: $OTEL_EXPORTER_OTLP_ENDPOINT"

# Check service name
echo "Service name: $OTEL_SERVICE_NAME"

# Test connectivity
curl -v $OTEL_EXPORTER_OTLP_ENDPOINT
```

---

## Full Variable List

See `docs/environment_variables_reference.md` for complete list of 200+ environment variables organized by category:

- Core settings
- Database (8 types)
- Vector databases (6 backends)
- Message queues (4 systems)
- Cloud storage (4 providers)
- Communication (4 platforms)
- Observability (30+ options)
- Policy & safety
- Performance & scaling
- Security
- Logging
- AI/ML models

---

## Need Help?

- **Full Reference**: `docs/environment_variables_reference.md`
- **Grafana Setup**: `docs/grafana_setup_guide.md`
- **Configuration Guide**: `docs/configuration_guide.md`
- **Examples**: `examples/` directory
