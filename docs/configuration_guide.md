# AutoFlow Configuration Guide

This guide explains how to configure AutoFlow when importing the library into your project.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Methods](#configuration-methods)
3. [Environment Variables](#environment-variables)
4. [Configuration Files](#configuration-files)
5. [Programmatic Configuration](#programmatic-configuration)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Quick Start

### Minimal Configuration (Defaults)

```python
from autoflow import AutoImproveEngine
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore

# All defaults - works out of the box
engine = AutoImproveEngine(
    store=SQLiteGraphStore(),              # Default: in-memory database
    graph_builder=ContextGraphBuilder(),   # Default builder
    decision_graph=None,                   # Optional
    evaluator=ShadowEvaluator(),           # Default: passes all proposals
    applier=None,                          # No automatic application
)
```

---

## Configuration Methods

AutoFlow supports multiple configuration approaches:

| Method | Best For | Complexity | Flexibility |
|--------|----------|------------|-------------|
| **Environment Variables** | Containerized/deployed apps | Low | Medium |
| **Configuration Files** | Multi-environment setups | Medium | High |
| **Programmatic** | Complex/conditional logic | High | Very High |
| **Pydantic Settings** | Type-safe configuration | Medium | Very High |
| **Dependency Injection** | Testing/mocking | Low | Very High |

---

## Method 1: Environment Variables

### Supported Environment Variables

```bash
# Core AutoFlow Settings
AUTOFLOW_DB_PATH=/path/to/database.db           # Default: :memory:
AUTOFLOW_WORKFLOW_ID=my_workflow                 # Default: default
AUTOFLOW_LOG_LEVEL=INFO                          # Default: INFO
AUTOFLOW_BATCH_SIZE=100                          # Default: 100

# Policy Settings
AUTOFLOW_ALLOWED_PATHS=config/,prompts/,skills/  # Paths that can be modified
AUTOFLOW_MAX_RISK=MEDIUM                         # LOW, MEDIUM, HIGH
AUTOFLOW_REQUIRE_APPROVAL=false                  # Require approval before applying

# OpenTelemetry Settings
OTEL_SERVICE_NAME=autoflow-engine                # Service name for tracing
OTEL_SERVICE_VERSION=1.0.0                       # Service version
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # OTLP endpoint
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic...  # Auth headers
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production  # Resource attrs

# AWS S3 Settings (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET=autoflow-context

# Slack Settings (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#autoflow
```

### Usage Example

```python
import os
from autoflow import AutoImproveEngine

# Set via environment
# export AUTOFLOW_DB_PATH=/data/autoflow.db
# export AUTOFLOW_MAX_RISK=MEDIUM

engine = AutoImproveEngine(
    store=SQLiteGraphStore(
        db_path=os.getenv("AUTOFLOW_DB_PATH", ":memory:")
    ),
    # ... other components
)
```

---

## Method 2: Configuration Files

### Using YAML Configuration

Create `config/autoflow.yaml`:

```yaml
# AutoFlow Configuration

# Database settings
database:
  path: "/data/autoflow.db"
  # For PostgreSQL (future):
  # url: "postgresql://user:pass@localhost/autoflow"

# Workflow settings
workflow:
  id: "my_workflow"
  batch_size: 100
  log_level: "INFO"

# Policy settings
policy:
  allowed_paths:
    - "config/"
    - "prompts/"
    - "skills/"
  max_risk: "MEDIUM"
  require_approval: false

# Decision rules
rules:
  - type: "HighErrorRateRetryRule"
    workflow_id: "my_workflow"
    threshold: 3

  - type: "SlowStepRule"
    workflow_id: "my_workflow"
    threshold_ms: 5000

# Observability
observability:
  enabled: true
  traces:
    exporter: "otlp"
    endpoint: "http://localhost:4317"
    headers: null  # or "Authorization=Basic ..."
  metrics:
    enabled: true
    exporter: "prometheus"
    port: 9090
  logging:
    level: "INFO"
    format: "json"

# Integrations (optional)
integrations:
  s3:
    enabled: false
    bucket: "autoflow-context"
    region: "us-east-1"

  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"  # Environment variable reference
    channel: "#autoflow"

  vector_db:
    enabled: false
    backend: "chromadb"  # chromadb, pinecone, weaviate
    path: "./chroma_db"
```

### Load Configuration

```python
import yaml
import os
from pathlib import Path
from autoflow import AutoImproveEngine
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore

def load_config(config_path: str = "config/autoflow.yaml"):
    """Load AutoFlow configuration from YAML file."""

    config_path = Path(config_path)
    if not config_path.exists():
        config_path = Path("config/autoflow.yaml")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config

def create_engine_from_config(config: dict):
    """Create AutoFlow engine from configuration dict."""

    # Parse database config
    db_config = config.get("database", {})
    store = SQLiteGraphStore(
        db_path=db_config.get("path", ":memory:")
    )

    # Parse workflow config
    workflow_config = config.get("workflow", {})
    log_level = workflow_config.get("log_level", "INFO")

    # Set up logging
    import logging
    logging.basicConfig(level=getattr(logging, log_level))

    # Parse policy config
    policy_config = config.get("policy", {})
    from autoflow.apply.policy import ApplyPolicy
    from autoflow.types import RiskLevel

    policy = ApplyPolicy(
        allowed_paths_prefixes=tuple(policy_config.get("allowed_paths", ())),
        max_risk=RiskLevel[policy_config.get("max_risk", "MEDIUM")]
    )

    # Parse rules config
    from autoflow.decide.decision_graph import DecisionGraph
    from autoflow.decide.rules import HighErrorRateRetryRule, SlowStepRule

    rules = []
    for rule_config in config.get("rules", []):
        rule_type = rule_config.get("type")

        if rule_type == "HighErrorRateRetryRule":
            rules.append(HighErrorRateRetryRule(
                workflow_id=rule_config["workflow_id"],
                threshold=rule_config.get("threshold", 3)
            ))

        elif rule_type == "SlowStepRule":
            rules.append(SlowStepRule(
                workflow_id=rule_config["workflow_id"],
                threshold_ms=rule_config.get("threshold_ms", 5000)
            ))

    # Configure observability
    observability_config = config.get("observability", {})
    if observability_config.get("enabled", False):
        setup_observability(observability_config)

    # Create engine
    engine = AutoImproveEngine(
        store=store,
        graph_builder=ContextGraphBuilder(),
        decision_graph=DecisionGraph(rules=rules) if rules else None,
        evaluator=ShadowEvaluator(),
        applier=None,  # Configure separately if needed
    )

    return engine

def setup_observability(config: dict):
    """Setup OpenTelemetry from config."""

    traces_config = config.get("traces", {})
    if traces_config.get("exporter") == "otlp":
        import os

        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = traces_config["endpoint"]
        if traces_config.get("headers"):
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = traces_config["headers"]

        # Initialize OTEL
        from autoflow.otel import trace
        if trace:  # Only if opentelemetry is installed
            from opentelemetry import trace as otel_trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({
                "service.name": os.getenv("OTEL_SERVICE_NAME", "autoflow-engine")
            })

            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=traces_config["endpoint"])
            provider.add_span_processor(BatchSpanProcessor(exporter))
            otel_trace.set_tracer_provider(provider)

# Usage
config = load_config()
engine = create_engine_from_config(config)
```

---

## Method 3: Pydantic Settings (Type-Safe)

### Using Pydantic for Configuration

```python
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, validator

class AutoFlowConfig(BaseModel):
    """Type-safe AutoFlow configuration."""

    # Database
    db_path: str = Field(default=":memory:", description="Database file path")

    # Workflow
    workflow_id: str = Field(default="default", description="Workflow identifier")
    batch_size: int = Field(default=100, ge=1, le=10000)
    log_level: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Policy
    allowed_paths: List[str] = Field(default_factory=list)
    max_risk: str = Field(default="MEDIUM", regex="^(LOW|MEDIUM|HIGH)$")
    require_approval: bool = Field(default=False)

    # OpenTelemetry
    otel_enabled: bool = Field(default=False)
    otel_endpoint: Optional[str] = Field(default=None)
    otel_headers: Optional[str] = Field(default=None)

    # Integrations
    s3_enabled: bool = Field(default=False)
    s3_bucket: Optional[str] = Field(default=None)

    slack_enabled: bool = Field(default=False)
    slack_token: Optional[str] = Field(default=None)
    slack_channel: str = Field(default="#autoflow")

    @validator('log_level')
    def uppercase_log_level(cls, v):
        return v.upper()

    @validator('max_risk')
    def uppercase_max_risk(cls, v):
        return v.upper()

    @classmethod
    def from_env(cls) -> "AutoFlowConfig":
        """Load configuration from environment variables."""
        import os

        return cls(
            db_path=os.getenv("AUTOFLOW_DB_PATH", ":memory:"),
            workflow_id=os.getenv("AUTOFLOW_WORKFLOW_ID", "default"),
            batch_size=int(os.getenv("AUTOFLOW_BATCH_SIZE", "100")),
            log_level=os.getenv("AUTOFLOW_LOG_LEVEL", "INFO"),
            allowed_paths=os.getenv("AUTOFLOW_ALLOWED_PATHS", "").split(","),
            max_risk=os.getenv("AUTOFLOW_MAX_RISK", "MEDIUM"),
            require_approval=os.getenv("AUTOFLOW_REQUIRE_APPROVAL", "false").lower() == "true",
            otel_enabled=os.getenv("OTEL_ENABLED", "false").lower() == "true",
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otel_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
            s3_enabled=os.getenv("S3_ENABLED", "false").lower() == "true",
            s3_bucket=os.getenv("S3_BUCKET"),
            slack_enabled=os.getenv("SLACK_ENABLED", "false").lower() == "true",
            slack_token=os.getenv("SLACK_BOT_TOKEN"),
            slack_channel=os.getenv("SLACK_CHANNEL", "#autoflow"),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "AutoFlowConfig":
        """Load configuration from YAML file."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_env(self) -> dict:
        """Export to environment variables dict."""
        return {
            "AUTOFLOW_DB_PATH": self.db_path,
            "AUTOFLOW_WORKFLOW_ID": self.workflow_id,
            "AUTOFLOW_BATCH_SIZE": str(self.batch_size),
            "AUTOFLOW_LOG_LEVEL": self.log_level,
            "AUTOFLOW_ALLOWED_PATHS": ",".join(self.allowed_paths),
            "AUTOFLOW_MAX_RISK": self.max_risk,
            "AUTOFLOW_REQUIRE_APPROVAL": str(self.require_approval).lower(),
            "OTEL_ENABLED": str(self.otel_enabled).lower(),
            "OTEL_EXPORTER_OTLP_ENDPOINT": self.otel_endpoint or "",
            "OTEL_EXPORTER_OTLP_HEADERS": self.otel_headers or "",
            "S3_ENABLED": str(self.s3_enabled).lower(),
            "S3_BUCKET": self.s3_bucket or "",
            "SLACK_ENABLED": str(self.slack_enabled).lower(),
            "SLACK_BOT_TOKEN": self.slack_token or "",
            "SLACK_CHANNEL": self.slack_channel,
        }

# Usage examples:

# 1. Load from environment
config = AutoFlowConfig.from_env()
print(config)

# 2. Load from YAML
config = AutoFlowConfig.from_yaml("config/autoflow.yaml")
print(config)

# 3. Create manually
config = AutoFlowConfig(
    db_path="/data/autoflow.db",
    workflow_id="my_workflow",
    otel_enabled=True,
    otel_endpoint="http://localhost:4317",
)
print(config)

# 4. Export to environment
env_vars = config.to_env()
import os
for key, value in env_vars.items():
    os.environ[key] = value

# 5. Use with AutoFlow
from autoflow import AutoImproveEngine
from autoflow.graph.sqlite_store import SQLiteGraphStore

engine = AutoImproveEngine(
    store=SQLiteGraphStore(db_path=config.db_path),
    # ... other components
)
```

---

## Method 4: Programmatic Configuration

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AutoFlowSettings:
    """Simple programmatic configuration."""
    db_path: str = ":memory:"
    workflow_id: str = "default"
    enable_tracing: bool = False
    otel_endpoint: Optional[str] = None
    log_level: str = "INFO"

    @classmethod
    def development(cls) -> "AutoFlowSettings":
        """Development environment settings."""
        return cls(
            db_path=":memory:",
            workflow_id="dev_workflow",
            enable_tracing=True,
            otel_endpoint="http://localhost:4317",
            log_level="DEBUG",
        )

    @classmethod
    def production(cls) -> "AutoFlowSettings":
        """Production environment settings."""
        import os
        return cls(
            db_path=os.getenv("AUTOFLOW_DB_PATH", "/data/autoflow.db"),
            workflow_id=os.getenv("AUTOFLOW_WORKFLOW_ID", "prod_workflow"),
            enable_tracing=True,
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            log_level="INFO",
        )

# Usage
settings = AutoFlowSettings.development()

# or
import os
if os.getenv("ENV") == "production":
    settings = AutoFlowSettings.production()
else:
    settings = AutoFlowSettings.development()
```

---

## Best Practices

### 1. Environment-Specific Configuration

```python
import os

def get_config(env: str = None):
    """Get configuration for environment."""

    env = env or os.getenv("ENV", "development")

    if env == "production":
        return AutoFlowConfig(
            db_path="/data/autoflow.db",
            log_level="INFO",
            otel_enabled=True,
            otel_endpoint=os.getenv("OTEL_ENDPOINT"),
        )

    elif env == "staging":
        return AutoFlowConfig(
            db_path=":memory:",
            log_level="DEBUG",
            otel_enabled=True,
            otel_endpoint="http://staging-tempo:4317",
        )

    else:  # development
        return AutoFlowConfig(
            db_path=":memory:",
            log_level="DEBUG",
            otel_enabled=False,
        )

config = get_config()
```

### 2. Configuration Validation

```python
from pydantic import BaseModel, Field, validator

class ValidatedAutoFlowConfig(BaseModel):
    """Configuration with validation."""

    db_path: str
    batch_size: int = Field(default=100, ge=1, le=10000)

    @validator('db_path')
    def db_path_must_be_valid(cls, v):
        from pathlib import Path

        if v != ":memory:" and not Path(v).parent.exists():
            raise ValueError(f"Database directory does not exist: {v}")

        return v

# This will raise ValidationError if invalid
try:
    config = ValidatedAutoFlowConfig(
        db_path="/invalid/path/autoflow.db",
        batch_size=50000,  # Too large!
    )
except Exception as e:
    print(f"Configuration error: {e}")
```

### 3. Secret Management

```python
import os
from pathlib import Path

def load_secrets():
    """Load secrets from multiple sources."""

    # 1. Environment variables (preferred for containers)
    slack_token = os.getenv("SLACK_BOT_TOKEN")

    # 2. .env file (for local development)
    if not slack_token:
        from dotenv import load_dotenv
        load_dotenv()
        slack_token = os.getenv("SLACK_BOT_TOKEN")

    # 3. Secrets file (never commit this!)
    if not slack_token:
        secrets_file = Path("secrets.txt")
        if secrets_file.exists():
            with open(secrets_file) as f:
                for line in f:
                    if line.startswith("SLACK_BOT_TOKEN="):
                        slack_token = line.split("=", 1)[1].strip()

    # 4. Secret manager (AWS Secrets Manager, etc.)
    if not slack_token:
        try:
            import boto3
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId="autoflow/slack")
            import json
            secret = json.loads(response["SecretString"])
            slack_token = secret["SLACK_BOT_TOKEN"]
        except:
            pass

    return slack_token
```

### 4. Multi-Stage Configuration

```python
# config/base.py
BASE_CONFIG = {
    "batch_size": 100,
    "log_level": "INFO",
}

# config/development.py
DEV_CONFIG = {
    **BASE_CONFIG,
    "log_level": "DEBUG",
    "db_path": ":memory:",
}

# config/production.py
PROD_CONFIG = {
    **BASE_CONFIG,
    "db_path": "/data/autoflow.db",
    "otel_enabled": True,
}

# Usage
import os
env = os.getenv("ENV", "development")

if env == "production":
    from config.production import PROD_CONFIG as config
else:
    from config.development import DEV_CONFIG as config

engine = AutoImproveEngine(**config)
```

---

## Complete Example: Production-Ready Setup

```python
"""
production_app.py

Complete example showing how to configure and use AutoFlow in production.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from autoflow import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.decide.rules import HighErrorRateRetryRule
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import RiskLevel

class AutoFlowApp:
    """Production AutoFlow application."""

    def __init__(self, config_path: str = "config/autoflow.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_observability()
        self.engine = self._create_engine()

    def _load_config(self, config_path: str):
        """Load configuration from file or environment."""

        # Try YAML file first
        config_file = Path(config_path)
        if config_file.exists():
            import yaml
            with open(config_file) as f:
                return yaml.safe_load(f)

        # Fall back to environment
        import os

        return {
            "database": {
                "path": os.getenv("AUTOFLOW_DB_PATH", ":memory:"),
            },
            "workflow": {
                "id": os.getenv("AUTOFLOW_WORKFLOW_ID", "default"),
                "log_level": os.getenv("AUTOFLOW_LOG_LEVEL", "INFO"),
            },
            "policy": {
                "allowed_paths": os.getenv("AUTOFLOW_ALLOWED_PATHS", "").split(","),
                "max_risk": os.getenv("AUTOFLOW_MAX_RISK", "MEDIUM"),
            },
            "observability": {
                "enabled": os.getenv("OTEL_ENABLED", "false").lower() == "true",
                "traces": {
                    "endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
                    "headers": os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
                },
            },
        }

    def _setup_logging(self):
        """Configure logging."""

        log_level = self.config.get("workflow", {}).get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

    def _setup_observability(self):
        """Setup OpenTelemetry if configured."""

        obs_config = self.config.get("observability", {})

        if not obs_config.get("enabled", False):
            return

        traces_config = obs_config.get("traces", {})
        if not traces_config.get("endpoint"):
            return

        # Set environment for autoflow.otel module
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = traces_config["endpoint"]
        if traces_config.get("headers"):
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = traces_config["headers"]

        # Initialize OpenTelemetry
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({
                "service.name": "autoflow-engine",
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("ENV", "production"),
            })

            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(
                endpoint=traces_config["endpoint"],
                headers=self._parse_headers(traces_config.get("headers")),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

            logging.info("OpenTelemetry initialized")

        except ImportError:
            logging.warning("OpenTelemetry not installed")

    def _parse_headers(self, headers_str: Optional[str]) -> Optional[dict]:
        """Parse OTLP headers from string."""

        if not headers_str:
            return None

        headers = {}
        for part in headers_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                headers[key.strip()] = value.strip()

        return headers

    def _create_engine(self) -> AutoImproveEngine:
        """Create AutoFlow engine from configuration."""

        # Database
        db_config = self.config.get("database", {})
        store = SQLiteGraphStore(db_path=db_config.get("path", ":memory:"))

        # Policy
        policy_config = self.config.get("policy", {})
        policy = ApplyPolicy(
            allowed_paths_prefixes=tuple(policy_config.get("allowed_paths", ())),
            max_risk=RiskLevel[policy_config.get("max_risk", "MEDIUM")]
        )

        # Create engine
        engine = AutoImproveEngine(
            store=store,
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(
                rules=[
                    HighErrorRateRetryRule(
                        workflow_id=self.config.get("workflow", {}).get("id", "default"),
                        threshold=5,
                    )
                ]
            ),
            evaluator=ShadowEvaluator(),
            applier=ProposalApplier(
                policy=policy,
                backend=GitApplyBackend(repo_path=Path(".")),
            ),
        )

        logging.info("AutoFlow engine created")
        return engine

# Usage
if __name__ == "__main__":
    # Load configuration from environment or file
    app = AutoFlowApp()

    # Use the engine
    app.engine.ingest([
        make_event(
            source="my_app",
            name="request_processed",
            attributes={"status": "success"},
        )
    ])

    proposals = app.engine.propose()
    print(f"Generated {len(proposals)} proposals")
```

---

## Quick Reference

### Environment Variables Quick Reference

```bash
# Core
export AUTOFLOW_DB_PATH=/data/autoflow.db
export AUTOFLOW_WORKFLOW_ID=my_workflow
export AUTOFLOW_LOG_LEVEL=INFO

# Policy
export AUTOFLOW_ALLOWED_PATHS=config/,prompts/
export AUTOFLOW_MAX_RISK=MEDIUM

# OpenTelemetry (Local)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# OpenTelemetry (Grafana Cloud)
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net:4317
export OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64-creds>

# S3 (optional)
export S3_BUCKET=autoflow-context
export AWS_REGION=us-east-1

# Slack (optional)
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_CHANNEL=#autoflow
```

### Configuration File Quick Reference

```yaml
database:
  path: "/data/autoflow.db"

workflow:
  id: "my_workflow"
  log_level: "INFO"

policy:
  allowed_paths: ["config/", "prompts/"]
  max_risk: "MEDIUM"

observability:
  enabled: true
  traces:
    endpoint: "http://localhost:4317"
```

This gives you complete flexibility to configure AutoFlow for any environment!
