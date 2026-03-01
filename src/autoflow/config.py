"""
AutoFlow Configuration Module

Comprehensive configuration system supporting multiple backends and integrations through environment variables.

Usage:
    from autoflow.config import get_config

    # Load from environment
    config = get_config()

    # Access configuration
    print(config.database.url)
    print(config.observability.enabled)

    # Or use specific sections
    from autoflow.config import DatabaseConfig, ObservabilityConfig
    db_config = DatabaseConfig.from_env()
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    from pydantic import BaseModel, Field, validator, root_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback to dataclasses
    BaseModel = object
    Field = lambda default=None, **kwargs: default
    validator = lambda *args, **kwargs: lambda f: f
    root_validator = lambda *args, **kwargs: lambda f: f


# =============================================================================
# Enums
# =============================================================================

class DatabaseType(str, Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRES = "postgresql"
    MYSQL = "mysql"
    REDIS = "redis"
    MONGODB = "mongodb"
    CLICKHOUSE = "clickhouse"


class LogFormat(str, Enum):
    """Log formats."""
    JSON = "json"
    TEXT = "text"


class RiskLevel(str, Enum):
    """Risk levels for proposals."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CompressionType(str, Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    SNAPPY = "snappy"
    LZ4 = "lz4"


# =============================================================================
# Database Configuration
# =============================================================================

class DatabaseConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Database configuration from environment variables."""

    # Core settings
    type: str = Field(default="sqlite", description="Database type")
    path: Optional[str] = Field(default=None, description="Database path (for SQLite)")

    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=100, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout (seconds)")
    pool_recycle: int = Field(default=3600, ge=60, description="Pool recycle time (seconds)")

    # Query settings
    query_timeout: int = Field(default=30, ge=1, description="Query timeout (seconds)")

    # PostgreSQL specific
    postgres_host: Optional[str] = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    postgres_database: str = Field(default="autoflow", description="PostgreSQL database name")
    postgres_user: str = Field(default="autoflow", description="PostgreSQL user")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL password")
    postgres_ssl_mode: str = Field(default="prefer", description="SSL mode")
    postgres_schema: str = Field(default="public", description="Database schema")

    # MySQL specific
    mysql_host: Optional[str] = Field(default="localhost", description="MySQL host")
    mysql_port: int = Field(default=3306, ge=1, le=65535, description="MySQL port")
    mysql_database: str = Field(default="autoflow", description="MySQL database name")
    mysql_user: str = Field(default="autoflow", description="MySQL user")
    mysql_password: Optional[str] = Field(default=None, description="MySQL password")
    mysql_charset: str = Field(default="utf8mb4", description="Character set")
    mysql_ssl_disabled: bool = Field(default=False, description="Disable SSL")

    # Redis specific
    redis_host: Optional[str] = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_socket_timeout: int = Field(default=5, ge=1, description="Socket timeout")
    redis_url: Optional[str] = Field(default=None, description="Full Redis URL")

    # MongoDB specific
    mongodb_host: Optional[str] = Field(default="localhost", description="MongoDB host")
    mongodb_port: int = Field(default=27017, ge=1, le=65535, description="MongoDB port")
    mongodb_database: str = Field(default="autoflow", description="MongoDB database name")
    mongodb_user: Optional[str] = Field(default=None, description="MongoDB username")
    mongodb_password: Optional[str] = Field(default=None, description="MongoDB password")
    mongodb_auth_source: str = Field(default="admin", description="Auth database")
    mongodb_replica_set: Optional[str] = Field(default=None, description="Replica set name")

    # ClickHouse specific
    clickhouse_host: Optional[str] = Field(default="localhost", description="ClickHouse host")
    clickhouse_port: int = Field(default=8123, ge=1, le=65535, description="ClickHouse port")
    clickhouse_database: str = Field(default="autoflow", description="ClickHouse database")
    clickhouse_user: str = Field(default="default", description="ClickHouse user")
    clickhouse_password: Optional[str] = Field(default=None, description="ClickHouse password")
    clickhouse_secure: bool = Field(default=False, description="Use HTTPS")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        return cls(
            type=os.getenv("AUTOFLOW_DB_TYPE", "sqlite"),
            path=os.getenv("AUTOFLOW_DB_PATH", ":memory:"),
            pool_size=int(os.getenv("AUTOFLOW_DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("AUTOFLOW_DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("AUTOFLOW_DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("AUTOFLOW_DB_POOL_RECYCLE", "3600")),
            query_timeout=int(os.getenv("AUTOFLOW_DB_QUERY_TIMEOUT", "30")),
            # PostgreSQL
            postgres_host=os.getenv("AUTOFLOW_POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("AUTOFLOW_POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("AUTOFLOW_POSTGRES_DATABASE", "autoflow"),
            postgres_user=os.getenv("AUTOFLOW_POSTGRES_USER", "autoflow"),
            postgres_password=os.getenv("AUTOFLOW_POSTGRES_PASSWORD"),
            postgres_ssl_mode=os.getenv("AUTOFLOW_POSTGRES_SSL_MODE", "prefer"),
            postgres_schema=os.getenv("AUTOFLOW_POSTGRES_SCHEMA", "public"),
            # MySQL
            mysql_host=os.getenv("AUTOFLOW_MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("AUTOFLOW_MYSQL_PORT", "3306")),
            mysql_database=os.getenv("AUTOFLOW_MYSQL_DATABASE", "autoflow"),
            mysql_user=os.getenv("AUTOFLOW_MYSQL_USER", "autoflow"),
            mysql_password=os.getenv("AUTOFLOW_MYSQL_PASSWORD"),
            mysql_charset=os.getenv("AUTOFLOW_MYSQL_CHARSET", "utf8mb4"),
            mysql_ssl_disabled=os.getenv("AUTOFLOW_MYSQL_SSL_DISABLED", "false").lower() == "true",
            # Redis
            redis_host=os.getenv("AUTOFLOW_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("AUTOFLOW_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("AUTOFLOW_REDIS_DB", "0")),
            redis_password=os.getenv("AUTOFLOW_REDIS_PASSWORD"),
            redis_socket_timeout=int(os.getenv("AUTOFLOW_REDIS_SOCKET_TIMEOUT", "5")),
            redis_url=os.getenv("AUTOFLOW_REDIS_URL"),
            # MongoDB
            mongodb_host=os.getenv("AUTOFLOW_MONGODB_HOST", "localhost"),
            mongodb_port=int(os.getenv("AUTOFLOW_MONGODB_PORT", "27017")),
            mongodb_database=os.getenv("AUTOFLOW_MONGODB_DATABASE", "autoflow"),
            mongodb_user=os.getenv("AUTOFLOW_MONGODB_USER"),
            mongodb_password=os.getenv("AUTOFLOW_MONGODB_PASSWORD"),
            mongodb_auth_source=os.getenv("AUTOFLOW_MONGODB_AUTH_SOURCE", "admin"),
            mongodb_replica_set=os.getenv("AUTOFLOW_MONGODB_REPLICA_SET"),
            # ClickHouse
            clickhouse_host=os.getenv("AUTOFLOW_CLICKHOUSE_HOST", "localhost"),
            clickhouse_port=int(os.getenv("AUTOFLOW_CLICKHOUSE_PORT", "8123")),
            clickhouse_database=os.getenv("AUTOFLOW_CLICKHOUSE_DATABASE", "autoflow"),
            clickhouse_user=os.getenv("AUTOFLOW_CLICKHOUSE_USER", "default"),
            clickhouse_password=os.getenv("AUTOFLOW_CLICKHOUSE_PASSWORD"),
            clickhouse_secure=os.getenv("AUTOFLOW_CLICKHOUSE_SECURE", "false").lower() == "true",
        )

    @property
    def url(self) -> str:
        """Get database connection URL based on type."""
        if self.type == DatabaseType.SQLITE:
            return f"sqlite:///{self.path}" if self.path != ":memory:" else "sqlite:///:memory:"

        elif self.type == DatabaseType.POSTGRES:
            password_part = f":{self.postgres_password}" if self.postgres_password else ""
            return f"postgresql://{self.postgres_user}{password_part}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

        elif self.type == DatabaseType.MYSQL:
            password_part = f":{self.mysql_password}" if self.mysql_password else ""
            ssl_part = "?ssl=false" if self.mysql_ssl_disabled else ""
            return f"mysql://{self.mysql_user}{password_part}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}{ssl_part}"

        elif self.type == DatabaseType.REDIS:
            if self.redis_url:
                return self.redis_url
            password_part = f":{self.redis_password}" if self.redis_password else ""
            default_db = f"/{self.redis_db}" if self.redis_db > 0 else ""
            return f"redis://{password_part}@{self.redis_host}:{self.redis_port}{default_db}"

        elif self.type == DatabaseType.MONGODB:
            password_part = f":{self.mongodb_password}" if self.mongodb_password else ""
            user_part = f"{self.mongodb_user}{password_part}@" if self.mongodb_user else ""
            auth_part = f"?authSource={self.mongodb_auth_source}" if self.mongodb_auth_source else ""
            return f"mongodb://{user_part}{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_database}{auth_part}"

        elif self.type == DatabaseType.CLICKHOUSE:
            protocol = "https" if self.clickhouse_secure else "http"
            return f"{protocol}://{self.clickhouse_user}:{self.clickhouse_password}@{self.clickhouse_host}:{self.clickhouse_port}/{self.clickhouse_database}"

        else:
            raise ValueError(f"Unsupported database type: {self.type}")

    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled for the database."""
        if self.type == DatabaseType.POSTGRES:
            return self.postgres_ssl_mode in ("require", "verify-ca", "verify-full")
        elif self.type == DatabaseType.MYSQL:
            return not self.mysql_ssl_disabled
        elif self.type == DatabaseType.CLICKHOUSE:
            return self.clickhouse_secure
        return False


# =============================================================================
# Vector Database Configuration
# =============================================================================

class VectorDatabaseConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Vector database configuration for semantic search."""

    # Pinecone
    pinecone_enabled: bool = Field(default=False, description="Enable Pinecone")
    pinecone_api_key: Optional[str] = Field(default=None, description="Pinecone API key")
    pinecone_environment: str = Field(default="us-west1-gcp", description="Pinecone environment")
    pinecone_index_prefix: str = Field(default="autoflow", description="Index name prefix")
    pinecone_dimension: int = Field(default=1536, description="Vector dimension")
    pinecone_metric: str = Field(default="cosine", description="Distance metric")
    pinecone_batch_size: int = Field(default=100, description="Upsert batch size")

    # ChromaDB
    chromadb_enabled: bool = Field(default=False, description="Enable ChromaDB")
    chromadb_path: str = Field(default="./chroma_db", description="Storage path")
    chromadb_host: Optional[str] = Field(default="localhost", description="Server host")
    chromadb_port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    chromadb_tenant: str = Field(default="default_tenant", description="Tenant")
    chromadb_database: str = Field(default="default_database", description="Database")
    chromadb_collection: str = Field(default="autoflow", description="Collection")

    # Weaviate
    weaviate_enabled: bool = Field(default=False, description="Enable Weaviate")
    weaviate_url: str = Field(default="http://localhost:8080", description="Weaviate URL")
    weaviate_api_key: Optional[str] = Field(default=None, description="API key")
    weaviate_class_name: str = Field(default="AutoFlowContext", description="Class name")

    # Qdrant
    qdrant_enabled: bool = Field(default=False, description="Enable Qdrant")
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(default=None, description="API key")
    qdrant_collection: str = Field(default="autoflow", description="Collection")
    qdrant_vector_size: int = Field(default=1536, description="Vector size")

    # Milvus
    milvus_enabled: bool = Field(default=False, description="Enable Milvus")
    milvus_host: str = Field(default="localhost", description="Host")
    milvus_port: int = Field(default=19530, description="Port")
    milvus_user: Optional[str] = Field(default=None, description="User")
    milvus_password: Optional[str] = Field(default=None, description="Password")
    milvus_database: str = Field(default="default", description="Database")
    milvus_collection: str = Field(default="autoflow", description="Collection")
    milvus_dimension: int = Field(default=1536, description="Vector dimension")

    @classmethod
    def from_env(cls) -> "VectorDatabaseConfig":
        """Load from environment."""
        return cls(
            pinecone_enabled=os.getenv("AUTOFLOW_PINECONE_ENABLED", "false").lower() == "true",
            pinecone_api_key=os.getenv("AUTOFLOW_PINECONE_API_KEY"),
            pinecone_environment=os.getenv("AUTOFLOW_PINECONE_ENVIRONMENT", "us-west1-gcp"),
            pinecone_index_prefix=os.getenv("AUTOFLOW_PINECONE_INDEX_PREFIX", "autoflow"),
            pinecone_dimension=int(os.getenv("AUTOFLOW_PINECONE_DIMENSION", "1536")),
            pinecone_metric=os.getenv("AUTOFLOW_PINECONE_METRIC", "cosine"),
            pinecone_batch_size=int(os.getenv("AUTOFLOW_PINECONE_BATCH_SIZE", "100")),
            # ChromaDB
            chromadb_enabled=os.getenv("AUTOFLOW_CHROMADB_ENABLED", "false").lower() == "true",
            chromadb_path=os.getenv("AUTOFLOW_CHROMADB_PATH", "./chroma_db"),
            chromadb_host=os.getenv("AUTOFLOW_CHROMADB_HOST", "localhost"),
            chromadb_port=int(os.getenv("AUTOFLOW_CHROMADB_PORT", "8000")),
            chromadb_tenant=os.getenv("AUTOFLOW_CHROMADB_TENANT", "default_tenant"),
            chromadb_database=os.getenv("AUTOFLOW_CHROMADB_DATABASE", "default_database"),
            chromadb_collection=os.getenv("AUTOFLOW_CHROMADB_COLLECTION", "autoflow"),
            # Weaviate
            weaviate_enabled=os.getenv("AUTOFLOW_WEAVIATE_ENABLED", "false").lower() == "true",
            weaviate_url=os.getenv("AUTOFLOW_WEAVIATE_URL", "http://localhost:8080"),
            weaviate_api_key=os.getenv("AUTOFLOW_WEAVIATE_API_KEY"),
            weaviate_class_name=os.getenv("AUTOFLOW_WEAVIATE_CLASS_NAME", "AutoFlowContext"),
            # Qdrant
            qdrant_enabled=os.getenv("AUTOFLOW_QDRANT_ENABLED", "false").lower() == "true",
            qdrant_url=os.getenv("AUTOFLOW_QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("AUTOFLOW_QDRANT_API_KEY"),
            qdrant_collection=os.getenv("AUTOFLOW_QDRANT_COLLECTION_NAME", "autoflow"),
            qdrant_vector_size=int(os.getenv("AUTOFLOW_QDRANT_VECTOR_SIZE", "1536")),
            # Milvus
            milvus_enabled=os.getenv("AUTOFLOW_MILVUS_ENABLED", "false").lower() == "true",
            milvus_host=os.getenv("AUTOFLOW_MILVUS_HOST", "localhost"),
            milvus_port=int(os.getenv("AUTOFLOW_MILVUS_PORT", "19530")),
            milvus_user=os.getenv("AUTOFLOW_MILVUS_USER"),
            milvus_password=os.getenv("AUTOFLOW_MILVUS_PASSWORD"),
            milvus_database=os.getenv("AUTOFLOW_MILVUS_DATABASE", "default"),
            milvus_collection=os.getenv("AUTOFLOW_MILVUS_COLLECTION", "autoflow"),
            milvus_dimension=int(os.getenv("AUTOFLOW_MILVUS_DIMENSION", "1536")),
        )


# =============================================================================
# Observability Configuration
# =============================================================================

class ObservabilityConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Observability and telemetry configuration."""

    enabled: bool = Field(default=True, description="Enable observability")
    tracing_enabled: bool = Field(default=True, description="Enable tracing")
    metrics_enabled: bool = Field(default=True, description="Enable metrics")
    logging_enabled: bool = Field(default=True, description="Enable logging")

    # OpenTelemetry
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_service_name: str = Field(default="autoflow-engine", description="Service name")
    otel_service_version: str = Field(default="1.0.0", description="Service version")
    otel_service_namespace: str = Field(default="default", description="Service namespace")
    otel_deployment_environment: str = Field(default="development", description="Deployment env")

    # OTLP Exporter
    otel_exporter_otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint")
    otel_exporter_otlp_protocol: str = Field(default="grpc", description="Protocol (grpc/http)")
    otel_exporter_otlp_headers: Optional[str] = Field(default=None, description="Headers")
    otel_exporter_otlp_timeout: int = Field(default=10, ge=1, description="Timeout (seconds)")
    otel_exporter_otlp_insecure: bool = Field(default=False, description="Skip TLS")

    # Batch processor
    otel_bsp_schedule_delay_millis: int = Field(default=5000, description="Batch delay")
    otel_bsp_max_queue_size: int = Field(default=2048, description="Max queue size")
    otel_bsp_max_export_batch_size: int = Field(default=512, description="Max batch size")

    # Sampling
    otel_traces_sampler: str = Field(default="always_on", description="Sampler type")
    otel_traces_sampler_arg: Optional[str] = Field(default=None, description="Sampler arg")

    # Grafana Cloud
    grafana_cloud_instance_id: Optional[str] = Field(default=None, description="Instance ID")
    grafana_cloud_api_key: Optional[str] = Field(default=None, description="API key")
    grafana_cloud_endpoint: str = Field(
        default="https://otlp-gateway-prod-us-central-0.grafana.net:4317",
        description="Grafana Cloud endpoint"
    )
    grafana_cloud_zone: str = Field(default="prod-us-central-0", description="Availability zone")

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Load from environment."""
        return cls(
            enabled=os.getenv("AUTOFLOW_OBSERVABILITY_ENABLED", "true").lower() == "true",
            tracing_enabled=os.getenv("AUTOFLOW_TRACING_ENABLED", "true").lower() == "true",
            metrics_enabled=os.getenv("AUTOFLOW_METRICS_ENABLED", "true").lower() == "true",
            logging_enabled=os.getenv("AUTOFLOW_LOGGING_ENABLED", "true").lower() == "true",
            # OTEL
            otel_enabled=os.getenv("OTEL_ENABLED", "false").lower() == "true",
            otel_service_name=os.getenv("OTEL_SERVICE_NAME", "autoflow-engine"),
            otel_service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            otel_service_namespace=os.getenv("OTEL_SERVICE_NAMESPACE", "default"),
            otel_deployment_environment=os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", "development"),
            # OTLP
            otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otel_exporter_otlp_protocol=os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc"),
            otel_exporter_otlp_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
            otel_exporter_otlp_timeout=int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10")),
            otel_exporter_otlp_insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true",
            # BSP
            otel_bsp_schedule_delay_millis=int(os.getenv("OTEL_BSP_SCHEDULE_DELAY_MILLIS", "5000")),
            otel_bsp_max_queue_size=int(os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048")),
            otel_bsp_max_export_batch_size=int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")),
            # Sampling
            otel_traces_sampler=os.getenv("OTEL_TRACES_SAMPLER", "always_on"),
            otel_traces_sampler_arg=os.getenv("OTEL_TRACES_SAMPLER_ARG"),
            # Grafana Cloud
            grafana_cloud_instance_id=os.getenv("GRAFANA_CLOUD_INSTANCE_ID"),
            grafana_cloud_api_key=os.getenv("GRAFANA_CLOUD_API_KEY"),
            grafana_cloud_endpoint=os.getenv("GRAFANA_CLOUD_ENDPOINT", "https://otlp-gateway-prod-us-central-0.grafana.net:4317"),
            grafana_cloud_zone=os.getenv("GRAFANA_CLOUD_ZONE", "prod-us-central-0"),
        )


# =============================================================================
# Policy Configuration
# =============================================================================

class PolicyConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Policy and safety configuration."""

    enabled: bool = Field(default=True, description="Enable policy enforcement")
    allowed_paths: List[str] = Field(default_factory=lambda: ["config/", "prompts/"], description="Allowed paths")
    denied_paths: List[str] = Field(default_factory=list, description="Denied paths")
    max_risk: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Max risk level")
    require_approval: bool = Field(default=False, description="Require approval")
    approval_timeout: int = Field(default=3600, ge=1, description="Approval timeout (seconds)")
    dry_run: bool = Field(default=False, description="Dry-run mode")
    max_changes_per_run: int = Field(default=10, ge=1, description="Max changes per run")

    @classmethod
    def from_env(cls) -> "PolicyConfig":
        """Load from environment."""
        allowed_paths_str = os.getenv("AUTOFLOW_POLICY_ALLOWED_PATHS", "config/,prompts/,skills/")
        denied_paths_str = os.getenv("AUTOFLOW_POLICY_DENIED_PATHS", "")

        return cls(
            enabled=os.getenv("AUTOFLOW_POLICY_ENABLED", "true").lower() == "true",
            allowed_paths=[p.strip() for p in allowed_paths_str.split(",") if p.strip()],
            denied_paths=[p.strip() for p in denied_paths_str.split(",") if p.strip()],
            max_risk=RiskLevel(os.getenv("AUTOFLOW_POLICY_MAX_RISK", "MEDIUM").upper()),
            require_approval=os.getenv("AUTOFLOW_POLICY_REQUIRE_APPROVAL", "false").lower() == "true",
            approval_timeout=int(os.getenv("AUTOFLOW_POLICY_APPROVAL_TIMEOUT", "3600")),
            dry_run=os.getenv("AUTOFLOW_POLICY_DRY_RUN", "false").lower() == "true",
            max_changes_per_run=int(os.getenv("AUTOFLOW_POLICY_MAX_CHANGES_PER_RUN", "10")),
        )


# =============================================================================
# Performance Configuration
# =============================================================================

class PerformanceConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Performance and scaling configuration."""

    batch_size: int = Field(default=100, ge=1, description="Batch size")
    max_concurrent_proposals: int = Field(default=5, ge=1, description="Max concurrent proposals")
    worker_threads: int = Field(default=4, ge=1, description="Worker threads")
    asyncio_workers: int = Field(default=10, ge=1, description="Async workers")
    queue_size: int = Field(default=1000, ge=1, description="Queue size")
    evaluation_interval_seconds: int = Field(default=300, ge=1, description="Evaluation interval")
    event_buffer_size: int = Field(default=10000, ge=1, description="Event buffer size")
    graph_max_nodes: int = Field(default=100000, ge=1, description="Max graph nodes")
    graph_max_edges: int = Field(default=500000, ge=1, description="Max graph edges")
    query_timeout_seconds: int = Field(default=30, ge=1, description="Query timeout")

    @classmethod
    def from_env(cls) -> "PerformanceConfig":
        """Load from environment."""
        return cls(
            batch_size=int(os.getenv("AUTOFLOW_BATCH_SIZE", "100")),
            max_concurrent_proposals=int(os.getenv("AUTOFLOW_MAX_CONCURRENT_PROPOSALS", "5")),
            worker_threads=int(os.getenv("AUTOFLOW_WORKER_THREADS", "4")),
            asyncio_workers=int(os.getenv("AUTOFLOW_ASYNCIO_WORKERS", "10")),
            queue_size=int(os.getenv("AUTOFLOW_QUEUE_SIZE", "1000")),
            evaluation_interval_seconds=int(os.getenv("AUTOFLOW_EVALUATION_INTERVAL_SECONDS", "300")),
            event_buffer_size=int(os.getenv("AUTOFLOW_EVENT_BUFFER_SIZE", "10000")),
            graph_max_nodes=int(os.getenv("AUTOFLOW_GRAPH_MAX_NODES", "100000")),
            graph_max_edges=int(os.getenv("AUTOFLOW_GRAPH_MAX_EDGES", "500000")),
            query_timeout_seconds=int(os.getenv("AUTOFLOW_QUERY_TIMEOUT_SECONDS", "30")),
        )


# =============================================================================
# Logging Configuration
# =============================================================================

class LoggingConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: LogFormat = Field(default=LogFormat.JSON, description="Log format")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_bytes: int = Field(default=10485760, ge=1, description="Max file size (default 10MB)")
    backup_count: int = Field(default=5, ge=0, description="Backup count")
    rotation: bool = Field(default=True, description="Enable rotation")
    structured: bool = Field(default=True, description="Structured logging")
    include_trace_id: bool = Field(default=True, description="Include trace ID")
    include_timestamp: bool = Field(default=True, description="Include timestamp")

    # Outputs
    to_console: bool = Field(default=True, description="Log to console")
    to_file: bool = Field(default=False, description="Log to file")
    to_syslog: bool = Field(default=False, description="Log to syslog")
    to_loki: bool = Field(default=False, description="Log to Loki")

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Load from environment."""
        return cls(
            level=os.getenv("AUTOFLOW_LOG_LEVEL", "INFO"),
            format=LogFormat(os.getenv("AUTOFLOW_LOG_FORMAT", "json")),
            file_path=os.getenv("AUTOFLOW_LOG_FILE"),
            max_bytes=int(os.getenv("AUTOFLOW_LOG_MAX_BYTES", "10485760")),
            backup_count=int(os.getenv("AUTOFLOW_LOG_BACKUP_COUNT", "5")),
            rotation=os.getenv("AUTOFLOW_LOG_ROTATION", "true").lower() == "true",
            structured=os.getenv("AUTOFLOW_LOG_STRUCTURED", "true").lower() == "true",
            include_trace_id=os.getenv("AUTOFLOW_LOG_INCLUDE_TRACE_ID", "true").lower() == "true",
            include_timestamp=os.getenv("AUTOFLOW_LOG_INCLUDE_TIMESTAMP", "true").lower() == "true",
            to_console=os.getenv("AUTOFLOW_LOG_TO_CONSOLE", "true").lower() == "true",
            to_file=os.getenv("AUTOFLOW_LOG_TO_FILE", "false").lower() == "true",
            to_syslog=os.getenv("AUTOFLOW_LOG_TO_SYSLOG", "false").lower() == "true",
            to_loki=os.getenv("AUTOFLOW_LOG_TO_LOKI", "false").lower() == "true",
        )


# =============================================================================
# Integration Configurations
# =============================================================================

class S3Config(BaseModel if PYDANTIC_AVAILABLE else object):
    """AWS S3 configuration."""

    enabled: bool = Field(default=False, description="Enable S3")
    bucket: str = Field(default="autoflow-context", description="Bucket name")
    prefix: str = Field(default="autoflow/", description="Key prefix")
    region: str = Field(default="us-east-1", description="AWS region")
    access_key_id: Optional[str] = Field(default=None, description="Access key")
    secret_access_key: Optional[str] = Field(default=None, description="Secret key")
    session_token: Optional[str] = Field(default=None, description="Session token")
    endpoint_url: Optional[str] = Field(default=None, description="Custom endpoint")
    use_ssl: bool = Field(default=True, description="Use SSL")
    max_pool_connections: int = Field(default=10, description="Max connections")

    @classmethod
    def from_env(cls) -> "S3Config":
        """Load from environment."""
        return cls(
            enabled=os.getenv("AUTOFLOW_S3_ENABLED", "false").lower() == "true",
            bucket=os.getenv("AUTOFLOW_S3_BUCKET", "autoflow-context"),
            prefix=os.getenv("AUTOFLOW_S3_PREFIX", "autoflow/"),
            region=os.getenv("AUTOFLOW_S3_REGION", "us-east-1"),
            access_key_id=os.getenv("AUTOFLOW_S3_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AUTOFLOW_S3_SECRET_ACCESS_KEY"),
            session_token=os.getenv("AUTOFLOW_S3_SESSION_TOKEN"),
            endpoint_url=os.getenv("AUTOFLOW_S3_ENDPOINT_URL"),
            use_ssl=os.getenv("AUTOFLOW_S3_USE_SSL", "true").lower() == "true",
            max_pool_connections=int(os.getenv("AUTOFLOW_S3_MAX_POOL_CONNECTIONS", "10")),
        )


class SlackConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Slack integration configuration."""

    enabled: bool = Field(default=False, description="Enable Slack")
    bot_token: Optional[str] = Field(default=None, description="Bot token (xoxb-...)")
    signing_secret: Optional[str] = Field(default=None, description="Signing secret")
    app_token: Optional[str] = Field(default=None, description="App token (xapp-...)")
    channel: str = Field(default="#autoflow", description="Default channel")
    username: str = Field(default="AutoFlow", description="Bot username")
    icon_emoji: str = Field(default=":robot_face:", description="Bot icon")
    timeout_seconds: int = Field(default=30, description="Request timeout")

    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Load from environment."""
        return cls(
            enabled=os.getenv("AUTOFLOW_SLACK_ENABLED", "false").lower() == "true",
            bot_token=os.getenv("AUTOFLOW_SLACK_BOT_TOKEN"),
            signing_secret=os.getenv("AUTOFLOW_SLACK_SIGNING_SECRET"),
            app_token=os.getenv("AUTOFLOW_SLACK_APP_TOKEN"),
            channel=os.getenv("AUTOFLOW_SLACK_CHANNEL", "#autoflow"),
            username=os.getenv("AUTOFLOW_SLACK_USERNAME", "AutoFlow"),
            icon_emoji=os.getenv("AUTOFLOW_SLACK_ICON_EMOJI", ":robot_face:"),
            timeout_seconds=int(os.getenv("AUTOFLOW_SLACK_TIMEOUT_SECONDS", "30")),
        )


# =============================================================================
# Complete AutoFlow Configuration
# =============================================================================

class AutoFlowConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Complete AutoFlow configuration."""

    # Core settings
    enabled: bool = Field(default=True, description="Enable AutoFlow")
    workspace: str = Field(default=".autoflow_workspace", description="Workspace directory")
    workflow_id: str = Field(default="default", description="Workflow ID")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    vector_db: VectorDatabaseConfig = Field(default_factory=VectorDatabaseConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    s3: S3Config = Field(default_factory=S3Config)
    slack: SlackConfig = Field(default_factory=SlackConfig)

    @classmethod
    def from_env(cls) -> "AutoFlowConfig":
        """Load complete configuration from environment."""
        return cls(
            enabled=os.getenv("AUTOFLOW_ENABLED", "true").lower() == "true",
            workspace=os.getenv("AUTOFLOW_WORKSPACE", ".autoflow_workspace"),
            workflow_id=os.getenv("AUTOFLOW_WORKFLOW_ID", "default"),
            environment=os.getenv("AUTOFLOW_ENVIRONMENT", "development"),
            debug=os.getenv("AUTOFLOW_DEBUG", "false").lower() == "true",
            # Sub-configs
            database=DatabaseConfig.from_env(),
            vector_db=VectorDatabaseConfig.from_env(),
            observability=ObservabilityConfig.from_env(),
            policy=PolicyConfig.from_env(),
            performance=PerformanceConfig.from_env(),
            logging=LoggingConfig.from_env(),
            s3=S3Config.from_env(),
            slack=SlackConfig.from_env(),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "AutoFlowConfig":
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
            return cls(**data)
        except ImportError:
            raise ImportError("PyYAML required: pip install pyyaml")

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate database connection string can be created
        try:
            _ = self.database.url
        except Exception as e:
            errors.append(f"Database URL error: {e}")

        # Validate workspace directory exists or can be created
        workspace_path = Path(self.workspace)
        if workspace_path.exists() and not os.access(workspace_path, os.W_OK):
            errors.append(f"Workspace directory not writable: {self.workspace}")

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_levels:
            errors.append(f"Invalid log level: {self.logging.level}")

        return errors

    def setup_logging(self):
        """Set up logging based on configuration."""
        import logging

        log_level = getattr(logging, self.logging.level.upper())

        handlers = []

        if self.logging.to_console:
            import sys
            console_handler = logging.StreamHandler(sys.stdout)
            handlers.append(console_handler)

        if self.logging.to_file and self.logging.file_path:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.logging.file_path,
                maxBytes=self.logging.max_bytes,
                backupCount=self.logging.backup_count,
            )
            handlers.append(file_handler)

        # Configure formatter
        if self.logging.format == LogFormat.JSON:
            from pythonjsonlogger import jsonlogger
            formatter = jsonlogger.JsonFormatter
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        for handler in handlers:
            handler.setFormatter(formatter)
            logging.root.addHandler(handler)

        logging.root.setLevel(log_level)

    def setup_observability(self):
        """Set up observability (tracing, metrics, logging)."""
        if not self.observability.enabled:
            return

        # Set up logging first
        self.setup_logging()

        # Set up OpenTelemetry if enabled
        if self.observability.otel_enabled:
            try:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.sdk.resources import Resource

                # Create resource
                resource_attrs = {
                    "service.name": self.observability.otel_service_name,
                    "service.version": self.observability.otel_service_version,
                    "deployment.environment": self.observability.otel_deployment_environment,
                }
                if self.observability.otel_service_namespace != "default":
                    resource_attrs["service.namespace"] = self.observability.otel_service_namespace

                resource = Resource.create(resource_attrs)

                # Create provider
                provider = TracerProvider(resource=resource)

                # Add OTLP exporter if endpoint configured
                if self.observability.otel_exporter_otlp_endpoint:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                    exporter = OTLPSpanExporter(
                        endpoint=self.observability.otel_exporter_otlp_endpoint,
                        headers=self._parse_headers(self.observability.otel_exporter_otlp_headers),
                        insecure=self.observability.otel_exporter_otlp_insecure,
                        timeout=int(self.observability.otel_exporter_otlp_timeout),
                    )
                    provider.add_span_processor(BatchSpanProcessor(exporter))

                trace.set_tracer_provider(provider)

                import logging
                logging.info(f"OpenTelemetry initialized: {self.observability.otel_service_name}")

            except ImportError:
                import logging
                logging.warning("OpenTelemetry packages not installed")

    def _parse_headers(self, headers_str: Optional[str]) -> Optional[Dict[str, str]]:
        """Parse OTLP headers from string."""
        if not headers_str:
            return None

        headers = {}
        for part in headers_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                headers[key.strip()] = value.strip()

        return headers


# =============================================================================
# Convenience Functions
# =============================================================================

def get_config() -> AutoFlowConfig:
    """
    Get AutoFlow configuration from environment.

    This is the main entry point for getting configuration.

    Returns:
        AutoFlowConfig: Loaded configuration

    Example:
        >>> config = get_config()
        >>> print(config.database.url)
        >>> print(config.observability.enabled)
    """
    return AutoFlowConfig.from_env()


def load_config_file(path: str) -> AutoFlowConfig:
    """
    Load configuration from YAML file.

    Args:
        path: Path to YAML file

    Returns:
        AutoFlowConfig: Loaded configuration

    Example:
        >>> config = load_config_file("config/autoflow.yaml")
    """
    return AutoFlowConfig.from_yaml(path)


def setup_autoflow(config: Optional[AutoFlowConfig] = None):
    """
    Set up AutoFlow with the given configuration.

    This configures:
    - Logging
    - Observability (tracing, metrics)
    - Validates configuration

    Args:
        config: Configuration object (uses get_config() if None)

    Returns:
        AutoFlowConfig: The configuration that was set up

    Example:
        >>> config = setup_autoflow()
        >>> # Or with custom config
        >>> custom_config = AutoFlowConfig.from_yaml("config/prod.yaml")
        >>> setup_autoflow(custom_config)
    """
    if config is None:
        config = get_config()

    # Validate
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    # Set up observability
    config.setup_observability()

    return config


# =============================================================================
# Configuration Profile Presets
# =============================================================================

class ConfigProfiles:
    """Predefined configuration profiles for common scenarios."""

    @staticmethod
    def development() -> AutoFlowConfig:
        """Development profile - in-memory, verbose logging."""
        return AutoFlowConfig(
            environment="development",
            debug=True,
            database=DatabaseConfig(
                type="sqlite",
                path=":memory:",
            ),
            logging=LoggingConfig(
                level="DEBUG",
                to_console=True,
                to_file=False,
            ),
            policy=PolicyConfig(
                max_risk=RiskLevel.HIGH,
                dry_run=True,
            ),
            observability=ObservabilityConfig(
                enabled=False,
            ),
        )

    @staticmethod
    def testing() -> AutoFlowConfig:
        """Testing profile - fast, minimal dependencies."""
        return AutoFlowConfig(
            environment="test",
            debug=False,
            database=DatabaseConfig(
                type="sqlite",
                path=":memory:",
            ),
            logging=LoggingConfig(
                level="WARNING",
                to_console=False,
            ),
            policy=PolicyConfig(
                dry_run=True,
            ),
            observability=ObservabilityConfig(
                enabled=False,
            ),
            performance=PerformanceConfig(
                batch_size=10,
                worker_threads=1,
            ),
        )

    @staticmethod
    def production() -> AutoFlowConfig:
        """Production profile - PostgreSQL, observability, optimized."""
        return AutoFlowConfig(
            environment="production",
            debug=False,
            database=DatabaseConfig(
                type="postgresql",
                pool_size=20,
                max_overflow=40,
            ),
            logging=LoggingConfig(
                level="INFO",
                format=LogFormat.JSON,
                to_console=True,
                to_file=True,
                to_loki=True,
            ),
            policy=PolicyConfig(
                max_risk=RiskLevel.LOW,
                require_approval=True,
            ),
            observability=ObservabilityConfig(
                enabled=True,
                tracing_enabled=True,
                metrics_enabled=True,
                otel_enabled=True,
            ),
            performance=PerformanceConfig(
                batch_size=500,
                worker_threads=16,
                queue_size=5000,
            ),
        )

    @staticmethod
    def serverless() -> AutoFlowConfig:
        """Serverless profile (AWS Lambda) - minimal state."""
        return AutoFlowConfig(
            environment="serverless",
            database=DatabaseConfig(
                type="sqlite",
                path="/tmp/autoflow.db",
            ),
            logging=LoggingConfig(
                level="INFO",
                format=LogFormat.JSON,
                to_console=True,
            ),
            observability=ObservabilityConfig(
                enabled=True,
                otel_enabled=True,
            ),
            performance=PerformanceConfig(
                batch_size=50,
                worker_threads=1,
            ),
        )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Example usage
    config = get_config()

    print("AutoFlow Configuration:")
    print(f"  Environment: {config.environment}")
    print(f"  Workflow ID: {config.workflow_id}")
    print(f"  Database: {config.database.type} @ {config.database.url}")
    print(f"  Observability: {config.observability.enabled}")
    print(f"  Tracing: {config.observability.tracing_enabled}")
    print(f"  Logging: {config.logging.level} -> {config.logging.format}")
    print()

    # Validate
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  ✗ {error}")
    else:
        print("✓ Configuration is valid")
