# AutoFlow Environment Variables - Complete Reference

Complete list of all environment variables for configuring AutoFlow.

## Table of Contents

- [Core AutoFlow Settings](#core-autoflow-settings)
- [Database Configuration](#database-configuration)
- [Vector Database Configuration](#vector-database-configuration)
- [Message Queue Configuration](#message-queue-configuration)
- [Cloud Storage Configuration](#cloud-storage-configuration)
- [Communication Configuration](#communication-configuration)
- [Observability & Telemetry](#observability--telemetry)
- [OpenTelemetry Configuration](#opentelemetry-configuration)
- [Policy & Safety Configuration](#policy--safety-configuration)
- [Performance & Scaling](#performance--scaling)
- [Security & Authentication](#security--authentication)
- [Logging Configuration](#logging-configuration)
- [Advanced Configuration](#advanced-configuration)
- [AI/ML Model Configuration](#aiml-model-configuration)
- [Feature Flags](#feature-flags)

---

## Core AutoFlow Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_ENABLED` | bool | `true` | Enable/disable AutoFlow entirely |
| `AUTOFLOW_WORKSPACE` | string | `.autoflow_workspace` | Workspace directory for local files |
| `AUTOFLOW_WORKFLOW_ID` | string | `default` | Default workflow identifier |
| `AUTOFLOW_ENVIRONMENT` | string | `development` | Environment name (dev/staging/prod) |
| `AUTOFLOW_DEBUG` | bool | `false` | Enable debug mode |
| `AUTOFLOW_CONFIG_FILE` | string | `null` | Path to configuration file (YAML/JSON) |
| `AUTOFLOW_PROFILE` | string | `default` | Configuration profile name |

---

## Database Configuration

### SQLite (Default)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_DB_TYPE` | string | `sqlite` | Database backend type |
| `AUTOFLOW_DB_PATH` | string | `:memory:` | SQLite database file path |
| `AUTOFLOW_DB_TIMEOUT` | int | `30` | Query timeout in seconds |
| `AUTOFLOW_DB_CHECKPOINT_INTERVAL` | int | `1000` | WAL checkpoint interval |

### PostgreSQL

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_POSTGRES_HOST` | string | `localhost` | PostgreSQL host |
| `AUTOFLOW_POSTGRES_PORT` | int | `5432` | PostgreSQL port |
| `AUTOFLOW_POSTGRES_DATABASE` | string | `autoflow` | Database name |
| `AUTOFLOW_POSTGRES_USER` | string | `autoflow` | Database user |
| `AUTOFLOW_POSTGRES_PASSWORD` | string | `null` | Database password |
| `AUTOFLOW_POSTGRES_SSL_MODE` | string | `prefer` | SSL mode (disable/allow/prefer/require/verify-ca/verify-full) |
| `AUTOFLOW_POSTGRES_POOL_SIZE` | int | `10` | Connection pool size |
| `AUTOFLOW_POSTGRES_MAX_OVERFLOW` | int | `20` | Max overflow connections |
| `AUTOFLOW_POSTGRES_POOL_TIMEOUT` | int | `30` | Connection pool timeout |
| `AUTOFLOW_POSTGRES_POOL_RECYCLE` | int | `3600` | Connection recycle time |
| `AUTOFLOW_POSTGRES_SCHEMA` | string | `public` | Database schema |

### MySQL/MariaDB

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_MYSQL_HOST` | string | `localhost` | MySQL host |
| `AUTOFLOW_MYSQL_PORT` | int | `3306` | MySQL port |
| `AUTOFLOW_MYSQL_DATABASE` | string | `autoflow` | Database name |
| `AUTOFLOW_MYSQL_USER` | string | `autoflow` | Database user |
| `AUTOFLOW_MYSQL_PASSWORD` | string | `null` | Database password |
| `AUTOFLOW_MYSQL_CHARSET` | string | `utf8mb4` | Character set |
| `AUTOFLOW_MYSQL_COLLATION` | string | `utf8mb4_unicode_ci` | Collation |
| `AUTOFLOW_MYSQL_SSL_DISABLED` | bool | `false` | Disable SSL |
| `AUTOFLOW_MYSQL_SSL_CA` | string | `null` | CA certificate path |

### Redis (for caching/queues)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_REDIS_HOST` | string | `localhost` | Redis host |
| `AUTOFLOW_REDIS_PORT` | int | `6379` | Redis port |
| `AUTOFLOW_REDIS_DB` | int | `0` | Redis database number |
| `AUTOFLOW_REDIS_PASSWORD` | string | `null` | Redis password |
| `AUTOFLOW_REDIS_SOCKET_TIMEOUT` | int | `5` | Socket timeout |
| `AUTOFLOW_REDIS_SOCKET_CONNECT_TIMEOUT` | int | `5` | Connection timeout |
| `AUTOFLOW_REDIS_MAX_CONNECTIONS` | int | `50` | Max connections |
| `AUTOFLOW_REDIS_SSL` | bool | `false` | Use SSL |
| `AUTOFLOW_REDIS_URL` | string | `null` | Full Redis URL (overrides other REDIS_ vars) |

### MongoDB

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_MONGODB_HOST` | string | `localhost` | MongoDB host |
| `AUTOFLOW_MONGODB_PORT` | int | `27017` | MongoDB port |
| `AUTOFLOW_MONGODB_DATABASE` | string | `autoflow` | Database name |
| `AUTOFLOW_MONGODB_USER` | string | `null` | Username |
| `AUTOFLOW_MONGODB_PASSWORD` | string | `null` | Password |
| `AUTOFLOW_MONGODB_AUTH_SOURCE` | string | `admin` | Authentication database |
| `AUTOFLOW_MONGODB_REPLICA_SET` | string | `null` | Replica set name |
| `AUTOFLOW_MONGODB_TLS_CA_FILE` | string | `null` | CA file path |
| `AUTOFLOW_MONGODB_TLS_CERTIFICATE_KEY_FILE` | string | `null` | Certificate key file |
| `AUTOFLOW_MONGODB_URL` | string | `null` | Full MongoDB URL |

### ClickHouse (analytics)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_CLICKHOUSE_HOST` | string | `localhost` | ClickHouse host |
| `AUTOFLOW_CLICKHOUSE_PORT` | int | `8123` | HTTP port |
| `AUTOFLOW_CLICKHOUSE_DATABASE` | string | `autoflow` | Database name |
| `AUTOFLOW_CLICKHOUSE_USER` | string | `default` | Username |
| `AUTOFLOW_CLICKHOUSE_PASSWORD` | string | `null` | Password |
| `AUTOFLOW_CLICKHOUSE_SECURE` | bool | `false` | Use HTTPS |
| `AUTOFLOW_CLICKHOUSE_VERIFY` | bool | `true` | Verify certificate |

---

## Vector Database Configuration

### Pinecone

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_PINECONE_ENABLED` | bool | `false` | Enable Pinecone integration |
| `AUTOFLOW_PINECONE_API_KEY` | string | `null` | Pinecone API key |
| `AUTOFLOW_PINECONE_ENVIRONMENT` | string | `us-west1-gcp` | Pinecone environment |
| `AUTOFLOW_PINECONE_INDEX_PREFIX` | string | `autoflow` | Index name prefix |
| `AUTOFLOW_PINECONE_DIMENSION` | int | `1536` | Vector dimension |
| `AUTOFLOW_PINECONE_METRIC` | string | `cosine` | Distance metric (cosine/euclidean/dotproduct) |
| `AUTOFLOW_PINECONE_BATCH_SIZE` | int | `100` | Upsert batch size |
| `AUTOFLOW_PINECONE_TIMEOUT` | int | `30` | Request timeout |

### ChromaDB

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_CHROMADB_ENABLED` | bool | `false` | Enable ChromaDB integration |
| `AUTOFLOW_CHROMADB_PATH` | string | `./chroma_db` | Persistent storage path |
| `AUTOFLOW_CHROMADB_HOST` | string | `localhost` | ChromaDB server host |
| `AUTOFLOW_CHROMADB_PORT` | int | `8000` | ChromaDB server port |
| `AUTOFLOW_CHROMADB_TENANT` | string | `default_tenant` | Default tenant |
| `AUTOFLOW_CHROMADB_DATABASE` | string | `default_database` | Default database |
| `AUTOFLOW_CHROMADB_COLLECTION` | string | `autoflow` | Default collection |
| `AUTOFLOW_CHROMADB_ANONYMIZED_TEASING` | bool | `false` | Enable anonymized telemetry |
| `AUTOFLOW_CHROMADB_ALLOW_RESET` | bool | `true` | Allow database reset |

### Weaviate

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_WEAVIATE_ENABLED` | bool | `false` | Enable Weaviate integration |
| `AUTOFLOW_WEAVIATE_URL` | string | `http://localhost:8080` | Weaviate URL |
| `AUTOFLOW_WEAVIATE_API_KEY` | string | `null` | Weaviate API key |
| `AUTOFLOW_WEAVIATE_CLASS_NAME` | string | `AutoFlowContext` | Default class name |
| `AUTOFLOW_WEAVIATE_BATCH_SIZE` | int | `100` | Batch import size |
| `AUTOFLOW_WEAVIATE_TIMEOUT` | int | `60` | Request timeout |

### Qdrant

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_QDRANT_ENABLED` | bool | `false` | Enable Qdrant integration |
| `AUTOFLOW_QDRANT_URL` | string | `http://localhost:6333` | Qdrant URL |
| `AUTOFLOW_QDRANT_API_KEY` | string | `null` | API key |
| `AUTOFLOW_QDRANT_COLLECTION_NAME` | string | `autoflow` | Collection name |
| `AUTOFLOW_QDRANT_VECTOR_SIZE` | int | `1536` | Vector size |
| `AUTOFLOW_QDRANT_DISTANCE` | string | `Cosine` | Distance metric |
| `AUTOFLOW_QDRANT_TIMEOUT` | int | `30` | Request timeout |

### Milvus

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_MILVUS_ENABLED` | bool | `false` | Enable Milvus integration |
| `AUTOFLOW_MILVUS_HOST` | string | `localhost` | Milvus host |
| `AUTOFLOW_MILVUS_PORT` | int | `19530` | Milvus port |
| `AUTOFLOW_MILVUS_USER` | string | `null` | Username |
| `AUTOFLOW_MILVUS_PASSWORD` | string | `null` | Password |
| `AUTOFLOW_MILVUS_DATABASE` | string | `default` | Database name |
| `AUTOFLOW_MILVUS_COLLECTION` | string | `autoflow` | Collection name |
| `AUTOFLOW_MILVUS_DIMENSION` | int | `1536` | Vector dimension |

### Pgvector (PostgreSQL extension)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_PGVECTOR_ENABLED` | bool | `false` | Enable pgvector |
| `AUTOFLOW_PGVECTOR_TABLE` | string | `autoflow_vectors` | Table name |
| `AUTOFLOW_PGVECTOR_DIMENSION` | int | `1536` | Vector dimension |
| `AUTOFLOW_PGVECTOR_INDEX_TYPE` | string | `hnsw` | Index type (ivfflat/hnsw) |

---

## Message Queue Configuration

### Kafka

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_KAFKA_ENABLED` | bool | `false` | Enable Kafka integration |
| `AUTOFLOW_KAFKA_BOOTSTRAP_SERVERS` | string | `localhost:9092` | Kafka brokers |
| `AUTOFLOW_KAFKA_TOPIC_PREFIX` | string | `autoflow` | Topic prefix |
| `AUTOFLOW_KAFKA_CONSUMER_GROUP` | string | `autoflow_group` | Consumer group ID |
| `AUTOFLOW_KAFKA_AUTO_OFFSET_RESET` | string | `earliest` | Offset reset (earliest/latest) |
| `AUTOFLOW_KAFKA_ENABLE_AUTO_COMMIT` | bool | `true` | Enable auto commit |
| `AUTOFLOW_KAFKA_SESSION_TIMEOUT_MS` | int | `30000` | Session timeout |
| `AUTOFLOW_KAFKA_HEARTBEAT_INTERVAL_MS` | int | `3000` | Heartbeat interval |
| `AUTOFLOW_KAFKA_MAX_POLL_RECORDS` | int | `500` | Max poll records |
| `AUTOFLOW_KAFKA_SECURITY_PROTOCOL` | string | `PLAINTEXT` | Security protocol |
| `AUTOFLOW_KAFKA_SASL_MECHANISM` | string | `null` | SASL mechanism |
| `AUTOFLOW_KAFKA_SASL_USERNAME` | string | `null` | SASL username |
| `AUTOFLOW_KAFKA_SASL_PASSWORD` | string | `null` | SASL password |
| `AUTOFLOW_KAFKA_SSL_CAFILE` | string | `null` | SSL CA file |

### RabbitMQ

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_RABBITMQ_ENABLED` | bool | `false` | Enable RabbitMQ integration |
| `AUTOFLOW_RABBITMQ_URL` | string | `amqp://guest:guest@localhost:5672` | RabbitMQ URL |
| `AUTOFLOW_RABBITMQ_HOST` | string | `localhost` | RabbitMQ host |
| `AUTOFLOW_RABBITMQ_PORT` | int | `5672` | RabbitMQ port |
| `AUTOFLOW_RABBITMQ_USER` | string | `guest` | Username |
| `AUTOFLOW_RABBITMQ_PASSWORD` | string | `guest` | Password |
| `AUTOFLOW_RABBITMQ_VHOST` | string | `/` | Virtual host |
| `AUTOFLOW_RABBITMQ_QUEUE_PREFIX` | string | `autoflow` | Queue prefix |
| `AUTOFLOW_RABBITMQ_EXCHANGE` | string | `autoflow` | Exchange name |
| `AUTOFLOW_RABBITMQ_SSL` | bool | `false` | Use SSL |
| `AUTOFLOW_RABBITMQ_PREFETCH_COUNT` | int | `10` | Prefetch count |

### AWS SQS

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_SQS_ENABLED` | bool | `false` | Enable SQS integration |
| `AUTOFLOW_SQS_REGION` | string | `us-east-1` | AWS region |
| `AUTOFLOW_SQS_QUEUE_PREFIX` | string | `autoflow` | Queue name prefix |
| `AUTOFLOW_SQS_ACCESS_KEY_ID` | string | `null` | AWS access key |
| `AUTOFLOW_SQS_SECRET_ACCESS_KEY` | string | `null` | AWS secret key |
| `AUTOFLOW_SQS_SESSION_TOKEN` | string | `null` | AWS session token |
| `AUTOFLOW_SQS_MAX_MESSAGES` | int | `10` | Max messages per poll |
| `AUTOFLOW_SQS_WAIT_TIME_SECONDS` | int | `20` | Long polling wait time |
| `AUTOFLOW_SQS_VISIBILITY_TIMEOUT` | int | `30` | Visibility timeout |

### Redis Streams

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_REDIS_STREAMS_ENABLED` | bool | `false` | Enable Redis Streams |
| `AUTOFLOW_REDIS_STREAM_PREFIX` | string | `autoflow` | Stream key prefix |
| `AUTOFLOW_REDIS_STREAM_CONSUMER_GROUP` | string | `autoflow` | Consumer group |
| `AUTOFLOW_REDIS_STREAM_BLOCK_MS` | int | `1000` | Blocking timeout |
| `AUTOFLOW_REDIS_STREAM_COUNT` | int | `10` | Messages per read |

---

## Cloud Storage Configuration

### AWS S3

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_S3_ENABLED` | bool | `false` | Enable S3 integration |
| `AUTOFLOW_S3_BUCKET` | string | `autoflow-context` | S3 bucket name |
| `AUTOFLOW_S3_PREFIX` | string | `autoflow/` | Key prefix |
| `AUTOFLOW_S3_REGION` | string | `us-east-1` | AWS region |
| `AUTOFLOW_S3_ACCESS_KEY_ID` | string | `null` | AWS access key ID |
| `AUTOFLOW_S3_SECRET_ACCESS_KEY` | string | `null` | AWS secret key |
| `AUTOFLOW_S3_SESSION_TOKEN` | string | `null` | Session token |
| `AUTOFLOW_S3_ENDPOINT_URL` | string | `null` | Custom endpoint (for S3-compatible) |
| `AUTOFLOW_S3_USE_SSL` | bool | `true` | Use SSL |
| `AUTOFLOW_S3_VERIFY_SSL` | bool | `true` | Verify SSL certificates |
| `AUTOFLOW_S3_MAX_POOL_CONNECTIONS` | int | `10` | Max connections |
| `AUTOFLOW_S3_CONNECT_TIMEOUT` | int | `10` | Connection timeout |
| `AUTOFLOW_S3_READ_TIMEOUT` | int | `60` | Read timeout |

### Google Cloud Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_GCS_ENABLED` | bool | `false` | Enable GCS integration |
| `AUTOFLOW_GCS_BUCKET` | string | `autoflow-context` | GCS bucket name |
| `AUTOFLOW_GCS_PREFIX` | string | `autoflow/` | Object prefix |
| `AUTOFLOW_GCS_CREDENTIALS_PATH` | string | `null` | Service account JSON path |
| `AUTOFLOW_GCS_PROJECT_ID` | string | `null` | GCP project ID |
| `AUTOFLOW_GCS_LOCATION` | string | `US` | Bucket location |

### Azure Blob Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_AZURE_BLOB_ENABLED` | bool | `false` | Enable Azure Blob integration |
| `AUTOFLOW_AZURE_BLOB_CONTAINER` | string | `autoflow` | Container name |
| `AUTOFLOW_AZURE_BLOB_PREFIX` | string | `autoflow/` | Blob prefix |
| `AUTOFLOW_AZURE_STORAGE_ACCOUNT` | string | `null` | Storage account name |
| `AUTOFLOW_AZURE_STORAGE_KEY` | string | `null` | Storage account key |
| `AUTOFLOW_AZURE_CONNECTION_STRING` | string | `null` | Connection string |
| `AUTOFLOW_AZURE_SAS_TOKEN` | string | `null` | SAS token |

### MinIO (S3-compatible local)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_MINIO_ENABLED` | bool | `false` | Enable MinIO integration |
| `AUTOFLOW_MINIO_ENDPOINT` | string | `http://localhost:9000` | MinIO endpoint |
| `AUTOFLOW_MINIO_ACCESS_KEY` | string | `minioadmin` | Access key |
| `AUTOFLOW_MINIO_SECRET_KEY` | string | `minioadmin` | Secret key |
| `AUTOFLOW_MINIO_BUCKET` | string | `autoflow` | Bucket name |
| `AUTOFLOW_MINIO_USE_SSL` | bool | `false` | Use SSL |
| `AUTOFLOW_MINIO_SECURE` | bool | `false` | Verify SSL |

---

## Communication Configuration

### Slack

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_SLACK_ENABLED` | bool | `false` | Enable Slack integration |
| `AUTOFLOW_SLACK_BOT_TOKEN` | string | `null` | Bot user OAuth token (xoxb-...) |
| `AUTOFLOW_SLACK_SIGNING_SECRET` | string | `null` | Signing secret |
| `AUTOFLOW_SLACK_APP_TOKEN` | string | `null` | App-level token (xapp-...) for Socket Mode |
| `AUTOFLOW_SLACK_CHANNEL` | string | `#autoflow` | Default channel |
| `AUTOFLOW_SLACK_USERNAME` | string | `AutoFlow` | Bot username |
| `AUTOFLOW_SLACK_ICON_EMOJI` | string | `:robot_face:` | Bot icon |
| `AUTOFLOW_SLACK_TIMEOUT_SECONDS` | int | `30` | Request timeout |

### Discord

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_DISCORD_ENABLED` | bool | `false` | Enable Discord integration |
| `AUTOFLOW_DISCORD_BOT_TOKEN` | string | `null` | Bot token |
| `AUTOFLOW_DISCORD_GUILD_ID` | string | `null` | Default guild ID |
| `AUTOFLOW_DISCORD_CHANNEL_ID` | string | `null` | Default channel ID |
| `AUTOFLOW_DISCORD_COMMAND_PREFIX` | string | `/` | Command prefix |

### Microsoft Teams

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_TEAMS_ENABLED` | bool | `false` | Enable Teams integration |
| `AUTOFLOW_TEAMS_WEBHOOK_URL` | string | `null` | Incoming webhook URL |
| `AUTOFLOW_TEAMS_APP_ID` | string | `null` | Azure AD app ID |
| `AUTOFLOW_TEAMS_APP_PASSWORD` | string | `null` | App password |

### Email

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_EMAIL_ENABLED` | bool | `false` | Enable email notifications |
| `AUTOFLOW_EMAIL_SMTP_HOST` | string | `localhost` | SMTP host |
| `AUTOFLOW_EMAIL_SMTP_PORT` | int | `587` | SMTP port |
| `AUTOFLOW_EMAIL_USERNAME` | string | `null` | SMTP username |
| `AUTOFLOW_EMAIL_PASSWORD` | string | `null` | SMTP password |
| `AUTOFLOW_EMAIL_FROM` | string | `autoflow@example.com` | From address |
| `AUTOFLOW_EMAIL_TO` | string | `null` | Default recipient |
| `AUTOFLOW_EMAIL_USE_TLS` | bool | `true` | Use TLS |

### PagerDuty

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_PAGERDUTY_ENABLED` | bool | `false` | Enable PagerDuty integration |
| `AUTOFLOW_PAGERDUTY_API_KEY` | string | `null` | API key |
| `AUTOFLOW_PAGERDUTY_USER_ID` | string | `null` | User ID |
| `AUTOFLOW_PAGERDUTY_SERVICE_ID` | string | `null` | Service ID |
| `AUTOFLOW_PAGERDUTY_ESCALATION_POLICY` | string | `null` | Escalation policy ID |

---

## Observability & Telemetry

### General Observability

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_OBSERVABILITY_ENABLED` | bool | `true` | Enable all observability |
| `AUTOFLOW_TRACING_ENABLED` | bool | `true` | Enable distributed tracing |
| `AUTOFLOW_METRICS_ENABLED` | bool | `true` | Enable metrics collection |
| `AUTOFLOW_LOGGING_ENABLED` | bool | `true` | Enable structured logging |
| `AUTOFLOW_PROFILING_ENABLED` | bool | `false` | Enable performance profiling |

---

## OpenTelemetry Configuration

### Core OpenTelemetry

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_SERVICE_NAME` | string | `autoflow-engine` | Service name |
| `OTEL_SERVICE_VERSION` | string | `1.0.0` | Service version |
| `OTEL_SERVICE_NAMESPACE` | string | `default` | Service namespace |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | string | `development` | Deployment environment |
| `OTEL_ENABLED` | bool | `false` | Enable OpenTelemetry |

### OTLP Exporter

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | string | `null` | OTLP endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | string | `grpc` | Protocol (grpc/http) |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | string | `null` | Certificate file |
| `OTEL_EXPORTER_OTLP_HEADERS` | string | `null` | Headers (comma-separated: key1=val1,key2=val2) |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | int | `10` | Request timeout (seconds) |
| `OTEL_EXPORTER_OTLP_COMPRESSION` | string | `none` | Compression (none/gzip) |
| `OTEL_EXPORTER_OTLP_INSECURE` | bool | `false` | Skip TLS verification |

### Batch Processor

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_BSP_SCHEDULE_DELAY_MILLIS` | int | `5000` | Batch schedule delay |
| `OTEL_BSP_MAX_QUEUE_SIZE` | int | `2048` | Max queue size |
| `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` | int | `512` | Max export batch size |
| `OTEL_BSP_EXPORT_TIMEOUT_MILLIS` | int | `30000` | Export timeout |

### Trace Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_TRACES_SAMPLER` | string | `always_on` | Sampler (always_on/never/traceid_ratio/parentbased) |
| `OTEL_TRACES_SAMPLER_ARG` | string | `null` | Sampler argument |
| `OTEL_TRACES_EXPORTER` | string | `otlp` | Trace exporter |

### Resource Attributes

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_RESOURCE_ATTRIBUTES` | string | `null` | Resource attributes (k=v,k=v) |
| `OTEL_RESOURCE_DETECTION_TIMEOUT` | int | `10` | Detection timeout |

### Experimental Features

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OTEL_EXPERIMENTAL_RESOURCE_DETECTORS` | string | `null` | Resource detectors |
| `OTEL_EXPERIMENTAL_RECEIVER_SHARED_MEMORY_ENABLED` | bool | `false` | Enable shared memory |

### Grafana Specific

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GRAFANA_CLOUD_INSTANCE_ID` | string | `null` | Grafana Cloud instance ID |
| `GRAFANA_CLOUD_API_KEY` | string | `null` | Grafana Cloud API key |
| `GRAFANA_CLOUD_ENDPOINT` | string | `https://otlp-gateway-prod-us-central-0.grafana.net:4317` | OTLP endpoint |
| `GRAFANA_CLOUD_ZONE` | string | `prod-us-central-0` | Availability zone |

---

## Policy & Safety Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_POLICY_ENABLED` | bool | `true` | Enable policy enforcement |
| `AUTOFLOW_POLICY_ALLOWED_PATHS` | string | `config/,prompts/` | Allowed paths (comma-separated) |
| `AUTOFLOW_POLICY_DENIED_PATHS` | string | `null` | Denied paths (comma-separated) |
| `AUTOFLOW_POLICY_MAX_RISK` | string | `MEDIUM` | Max risk level (LOW/MEDIUM/HIGH) |
| `AUTOFLOW_POLICY_REQUIRE_APPROVAL` | bool | `false` | Require approval before apply |
| `AUTOFLOW_POLICY_APPROVAL_TIMEOUT` | int | `3600` | Approval timeout (seconds) |
| `AUTOFLOW_POLICY_DRY_RUN` | bool | `false` | Dry-run mode (don't actually apply) |
| `AUTOFLOW_POLICY_MAX_CHANGES_PER_RUN` | int | `10` | Max changes per evaluation |

---

## Performance & Scaling

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_BATCH_SIZE` | int | `100` | Default batch size |
| `AUTOFLOW_MAX_CONCURRENT_PROPOSALS` | int | `5` | Max concurrent proposals |
| `AUTOFLOW_WORKER_THREADS` | int | `4` | Worker thread count |
| `AUTOFLOW_ASYNCIO_WORKERS` | int | `10` | Async worker count |
| `AUTOFLOW_QUEUE_SIZE` | int | `1000` | Internal queue size |
| `AUTOFLOW_EVALUATION_INTERVAL_SECONDS` | int | `300` | Evaluation interval |
| `AUTOFLOW_EVENT_BUFFER_SIZE` | int | `10000` | Event buffer size |
| `AUTOFLOW_GRAPH_MAX_NODES` | int | `100000` | Max graph nodes |
| `AUTOFLOW_GRAPH_MAX_EDGES` | int | `500000` | Max graph edges |
| `AUTOFLOW_QUERY_TIMEOUT_SECONDS` | int | `30` | Query timeout |

---

## Security & Authentication

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_AUTH_ENABLED` | bool | `false` | Enable authentication |
| `AUTOFLOW_AUTH_TYPE` | string | `none` | Auth type (none/apikey/oauth/jwt) |
| `AUTOFLOW_API_KEY` | string | `null` | API key for authentication |
| `AUTOFLOW_JWT_SECRET` | string | `null` | JWT secret |
| `AUTOFLOW_JWT_ALGORITHM` | string | `HS256` | JWT algorithm |
| `AUTOFLOW_JWT_EXPIRATION_HOURS` | int | `24` | JWT expiration |

### Encryption

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_ENCRYPTION_KEY` | string | `null` | Encryption key (for sensitive data) |
| `AUTOFLOW_ENCRYPTION_KEY_PATH` | string | `null` | Path to encryption key file |
| `AUTOFLOW_ENCRYPTION_ALGORITHM` | string | `AES256` | Encryption algorithm |
| `AUTOFLOW_HASH_ALGORITHM` | string | `sha256` | Hash algorithm |

### TLS/SSL

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_TLS_ENABLED` | bool | `false` | Enable TLS for API |
| `AUTOFLOW_TLS_CERT_FILE` | string | `null` | TLS certificate file |
| `AUTOFLOW_TLS_KEY_FILE` | string | `null` | TLS key file |
| `AUTOFLOW_TLS_CA_FILE` | string | `null` | TLS CA file |
| `AUTOFLOW_TLS_CLIENT_AUTH` | bool | `false` | Require client auth |

---

## Logging Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_LOG_LEVEL` | string | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `AUTOFLOW_LOG_FORMAT` | string | `json` | Log format (json/text) |
| `AUTOFLOW_LOG_FILE` | string | `null` | Log file path |
| `AUTOFLOW_LOG_MAX_BYTES` | int | `10485760` | Max log file size (10MB) |
| `AUTOFLOW_LOG_BACKUP_COUNT` | int | `5` | Number of backup logs |
| `AUTOFLOW_LOG_ROTATION` | bool | `true` | Enable log rotation |
| `AUTOFLOW_LOG_STRUCTURED` | bool | `true` | Enable structured logging |
| `AUTOFLOW_LOG_INCLUDE_TRACE_ID` | bool | `true` | Include trace ID in logs |
| `AUTOFLOW_LOG_INCLUDE_TIMESTAMP` | bool | `true` | Include timestamp |

### Log Outputs

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_LOG_TO_CONSOLE` | bool | `true` | Log to console |
| `AUTOFLOW_LOG_TO_FILE` | bool | `false` | Log to file |
| `AUTOFLOW_LOG_TO_SYSLOG` | bool | `false` | Log to syslog |
| `AUTOFLOW_LOG_TO_LOKI` | bool | `false` | Log to Loki |

---

## Advanced Configuration

### Caching

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_CACHE_ENABLED` | bool | `false` | Enable caching |
| `AUTOFLOW_CACHE_BACKEND` | string | `memory` | Cache backend (memory/redis/memcached) |
| `AUTOFLOW_CACHE_TTL_SECONDS` | int | `3600` | Cache TTL |
| `AUTOFLOW_CACHE_MAX_SIZE_MB` | int | `100` | Max cache size |

### Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_RATE_LIMIT_ENABLED` | bool | `false` | Enable rate limiting |
| `AUTOFLOW_RATE_LIMIT_REQUESTS_PER_MINUTE` | int | `60` | Requests per minute |
| `AUTOFLOW_RATE_LIMIT_BURST` | int | `10` | Burst size |

### Timeouts & Retries

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_REQUEST_TIMEOUT_SECONDS` | int | `30` | Default request timeout |
| `AUTOFLOW_CONNECT_TIMEOUT_SECONDS` | int | `10` | Connection timeout |
| `AUTOFLOW_READ_TIMEOUT_SECONDS` | int | `30` | Read timeout |
| `AUTOFLOW_MAX_RETRIES` | int | `3` | Max retry attempts |
| `AUTOFLOW_RETRY_BACKOFF_MS` | int | `100` | Initial retry backoff |
| `AUTOFLOW_RETRY_BACKOFF_MULTIPLIER` | float | `2.0` | Backoff multiplier |

### Graceful Shutdown

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_SHUTDOWN_TIMEOUT_SECONDS` | int | `30` | Shutdown timeout |
| `AUTOFLOW_SHUTDOWN_WAIT_PROPAGATION_SECONDS` | int | `5` | Wait for propagation |
| `AUTOFLOW_DRAIN_TIMEOUT_SECONDS` | int | `10` | Drain timeout |

---

## AI/ML Model Configuration

### OpenAI

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_API_KEY` | string | `null` | OpenAI API key |
| `OPENAI_MODEL` | string | `gpt-4` | Default model |
| `OPENAI_EMBEDDING_MODEL` | string | `text-embedding-ada-002` | Embedding model |
| `OPENAI_TEMPERATURE` | float | `0.7` | Temperature |
| `OPENAI_MAX_TOKENS` | int | `1000` | Max tokens |
| `OPENAI_TIMEOUT_SECONDS` | int | `60` | Request timeout |
| `OPENAI_ORGANIZATION` | string | `null` | Organization ID |
| `OPENAI_BASE_URL` | string | `null` | Base URL (for proxies) |

### Anthropic Claude

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ANTHROPIC_API_KEY` | string | `null` | Anthropic API key |
| `ANTHROPIC_MODEL` | string | `claude-3-opus-20240229` | Default model |
| `ANTHROPIC_MAX_TOKENS` | int | `4096` | Max tokens |
| `ANTHROPIC_TEMPERATURE` | float | `0.7` | Temperature |
| `ANTHROPIC_TIMEOUT_SECONDS` | int | `60` | Request timeout |

### Hugging Face

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HUGGINGFACE_API_KEY` | string | `null` | Hugging Face API key |
| `HUGGINGFACE_MODEL` | string | `null` | Model name |
| `HUGGINGFACE_ENDPOINT` | string | `null` | Inference endpoint |

### Local Models

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_LOCAL_MODEL_PATH` | string | `null` | Local model path |
| `AUTOFLOW_LOCAL_MODEL_DEVICE` | string | `cpu` | Device (cpu/cuda/mps) |
| `AUTOFLOW_LOCAL_MODEL_THREADS` | int | `4` | CPU threads |
| `AUTOFLOW_LOCAL_MODEL_BATCH_SIZE` | int | `1` | Batch size |
| `AUTOFLOW_LOCAL_MODEL_QUANTIZE` | bool | `false` | Quantize model |

---

## Feature Flags

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTOFLOW_FEATURE_PROPOSALS` | bool | `true` | Enable proposal generation |
| `AUTOFLOW_FEATURE_EVALUATION` | bool | `true` | Enable proposal evaluation |
| `AUTOFLOW_FEATURE_AUTO_APPLY` | bool | `false` | Enable automatic application |
| `AUTOFLOW_FEATURE_CONTEXT_ENRICHMENT` | bool | `false` | Enable context enrichment |
| `AUTOFLOW_FEATURE Semantic_SEARCH` | bool | `false` | Enable semantic search |
| `AUTOFLOW_FEATURE_ANOMALY_DETECTION` | bool | `false` | Enable anomaly detection |
| `AUTOFLOW_FEATURE_FORECASTING` | bool | `false` | Enable forecasting |
| `AUTOFLOW_FEATURE_A_B_TESTING` | bool | `false` | Enable A/B testing |

---

## Configuration Priority Order

When multiple configuration sources are available, they are applied in this order (later overrides earlier):

1. **Code defaults** (hardcoded defaults in library)
2. **Configuration file** (YAML/JSON from `AUTOFLOW_CONFIG_FILE`)
3. **Environment variables** (all `AUTOFLOW_*` and `OTEL_*` vars)
4. **Programmatic overrides** (runtime configuration in code)

---

## Example: Complete Production Configuration

```bash
# Core
export AUTOFLOW_ENVIRONMENT=production
export AUTOFLOW_WORKFLOW_ID=ml-pipeline-prod
export AUTOFLOW_DEBUG=false

# Database (PostgreSQL for production)
export AUTOFLOW_DB_TYPE=postgresql
export AUTOFLOW_POSTGRES_HOST=db.example.com
export AUTOFLOW_POSTGRES_PORT=5432
export AUTOFLOW_POSTGRES_DATABASE=autoflow_prod
export AUTOFLOW_POSTGRES_USER=autoflow_user
export AUTOFLOW_POSTGRES_PASSWORD=${AUTOFLOW_DB_PASSWORD}
export AUTOFLOW_POSTGRES_SSL_MODE=require
export AUTOFLOW_POSTGRES_POOL_SIZE=20

# Vector DB (Pinecone for semantic search)
export AUTOFLOW_PINECONE_ENABLED=true
export AUTOFLOW_PINECONE_API_KEY=${PINECONE_API_KEY}
export AUTOFLOW_PINECONE_ENVIRONMENT=us-west1-gcp
export AUTOFLOW_PINECONE_INDEX_PREFIX=autoflow-prod

# Cloud Storage (S3 for archival)
export AUTOFLOW_S3_ENABLED=true
export AUTOFLOW_S3_BUCKET=autoflow-prod-context
export AUTOFLOW_S3_REGION=us-east-1
export AUTOFLOW_S3_PREFIX=autoflow/prod/

# Message Queue (Kafka for events)
export AUTOFLOW_KAFKA_ENABLED=true
export AUTOFLOW_KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092
export AUTOFLOW_KAFKA_TOPIC_PREFIX=autoflow-prod

# Observability (Grafana Cloud)
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=autoflow-engine
export OTEL_SERVICE_VERSION=1.0.0
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic ${GRAFANA_CLOUD_CREDENTIALS}"

# Policy
export AUTOFLOW_POLICY_ALLOWED_PATHS=config/,prompts/,skills/
export AUTOFLOW_POLICY_MAX_RISK=LOW
export AUTOFLOW_POLICY_REQUIRE_APPROVAL=true

# Performance
export AUTOFLOW_BATCH_SIZE=500
export AUTOFLOW_WORKER_THREADS=16
export AUTOFLOW_EVALUATION_INTERVAL_SECONDS=600

# Logging
export AUTOFLOW_LOG_LEVEL=INFO
export AUTOFLOW_LOG_STRUCTURED=true
export AUTOFLOW_LOG_TO_LOKI=true

# AI Models
export OPENAI_API_KEY=${OPENAI_API_KEY}
export OPENAI_MODEL=gpt-4-turbo
```

---

## Example: Development Configuration

```bash
# Development - minimal config
export AUTOFLOW_ENVIRONMENT=development
export AUTOFLOW_DB_PATH=:memory:
export AUTOFLOW_LOG_LEVEL=DEBUG
export AUTOFLOW_POLICY_MAX_RISK=HIGH
export AUTOFLOW_POLICY_DRY_RUN=true
```

---

## Example: Testing Configuration

```bash
# Testing - in-memory everything
export AUTOFLOW_ENVIRONMENT=test
export AUTOFLOW_DB_PATH=:memory:
export AUTOFLOW_CHROMADB_PATH=:memory:
export AUTOFLOW_LOG_LEVEL=WARNING
export AUTOFLOW_TRACING_ENABLED=false
export AUTOFLOW_POLICY_DRY_RUN=true
```

---

## Environment Variable Naming Conventions

- **AUTOFLOW_*** - Core AutoFlow settings
- **OTEL_*** - OpenTelemetry settings (standard)
- **OPENAI_*** - OpenAI integration (standard)
- **ANTHROPIC_*** - Anthropic integration (standard)
- **GRAFANA_CLOUD_*** - Grafana Cloud specific
- **AUTOFLOW_{SERVICE}_ENABLED** - Enable/disable integrations

---

## Secret Management Best Practices

### For Development

```bash
# Use .env file (never commit)
AUTOFLOW_POSTGRES_PASSWORD=dev_password
OPENAI_API_KEY=sk-dev-key
```

### For Production

```bash
# Use secret manager or vault
export AUTOFLOW_POSTGRES_PASSWORD=$(vault kv get -field=password autoflow/db)
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id autoflow/openai --query SecretString --output text)
```

### For Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: autoflow-secrets
type: Opaque
stringData:
  password: ${AUTOFLOW_POSTGRES_PASSWORD}
  api-key: ${OPENAI_API_KEY}
```

---

## Validation

All configuration values are validated on startup. Invalid values will cause an error with helpful message.

Examples:
- Port must be 1-65535
- Batch size must be positive
- Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Risk level must be: LOW, MEDIUM, or HIGH
