# AutoFlow Examples

This directory contains comprehensive examples demonstrating how to integrate and use AutoFlow in various scenarios.

## 📁 Directory Structure

```
examples/
├── basic/                      # Basic AutoFlow usage examples
│   ├── demo.py                 # Simple introduction demo
│   ├── workflow_demo.py        # Workflow-aware tracking
│   ├── continuous_demo.py      # Continuous learning demo
│   └── ...
│
├── context_sources/            # Context source integrations
│   ├── vector_database_context.py    # Vector DB (Pinecone, ChromaDB, Weaviate)
│   ├── s3_context_source.py          # AWS S3 integration
│   └── slack_integration.py          # Slack notifications and approval
│
├── integrations/
│   ├── ai_frameworks/          # AI framework integrations
│   │   └── ai_frameworks_integrations.py  # Pydantic AI, LangChain, CrewAI
│   │
│   └── observability/          # Observability integrations
│       └── otel_grafana_integration.py   # OpenTelemetry + Grafana
│
├── workflow_patterns/          # Common workflow patterns
│   ├── retry_with_backoff.py   # Intelligent retry logic
│   ├── ab_testing.py           # A/B testing workflows
│   └── multi_stage_pipelines.py # Multi-stage pipelines
│
└── production/                 # Production deployment examples
    ├── docker_deployment.py    # Docker-based deployment
    ├── kubernetes_deployment.py # Kubernetes deployment
    └── monitoring_setup.py     # Production monitoring
```

## 🚀 Quick Start

### 1. Basic Usage

Start with the basic examples to understand AutoFlow fundamentals:

```bash
cd basic/
python demo.py                  # Introduction to AutoFlow
python workflow_demo.py         # Workflow tracking
python continuous_demo.py       # Continuous learning (requires OPENAI_API_KEY)
```

### 2. Context Sources

Learn how to enrich AutoFlow with external context:

```bash
# Vector database for semantic search
pip install chromadb  # or pinecone-client, weaviate-client
python context_sources/vector_database_context.py

# S3 for persistent storage
pip install boto3
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python context_sources/s3_context_source.py

# Slack for notifications and approval
pip install slack-sdk
export SLACK_BOT_TOKEN=xoxb-your-token
python context_sources/slack_integration.py
```

### 3. AI Framework Integrations

Integrate AutoFlow with popular AI frameworks:

```bash
# Install your preferred framework
pip install pydantic-ai        # or langchain, crewai
export OPENAI_API_KEY=your_key

python integrations/ai_frameworks/ai_frameworks_integrations.py
```

### 4. Observability

Set up comprehensive observability:

```bash
# OpenTelemetry + Grafana
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# For local development
docker run -d -p 4317:4317 grafana/tempo:latest

# Run the example
python integrations/observability/otel_grafana_integration.py
```

## 📚 Examples by Use Case

### For AI/ML Teams

**Improve Prompt Engineering:**
- `basic/continuous_demo.py` - Automatically optimize prompts
- `integrations/ai_frameworks/ai_frameworks_integrations.py` - Framework-specific integration

**Optimize Model Performance:**
- `context_sources/vector_database_context.py` - Semantic search for similar issues
- `workflow_patterns/ab_testing.py` - A/B test different configurations

### For DevOps/SRE Teams

**Improve System Reliability:**
- `context_sources/slack_integration.py` - Get approval before changes
- `workflow_patterns/retry_with_backoff.py` - Intelligent retry logic

**Monitor and Debug:**
- `integrations/observability/otel_grafana_integration.py` - Full observability stack
- `context_sources/s3_context_source.py` - Archive events for analysis

### For Data Engineering Teams

**Pipeline Optimization:**
- `workflow_patterns/multi_stage_pipelines.py` - Optimize data pipelines
- `context_sources/s3_context_source.py` - Store and retrieve datasets

**Data Quality:**
- `basic/workflow_demo.py` - Track data processing steps
- `basic/multistep_demo.py` - Multi-stage workflow tracking

## 🔧 Configuration

### Environment Variables

Most examples require environment variables:

```bash
# OpenAI API (for AI examples)
export OPENAI_API_KEY=sk-...

# AWS (for S3 examples)
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Slack (for Slack integration)
export SLACK_BOT_TOKEN=xoxb-...

# OpenTelemetry (for observability)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=autoflow-engine
```

### Local Development Setup

For local development with all dependencies:

```bash
# Install AutoFlow with all optional dependencies
pip install -e ".[all]"

# Or use uv
uv pip install -e ".[all]"
```

## 📊 Key Features Demonstrated

### 1. Continuous Learning
- `basic/continuous_demo.py` shows how AutoFlow improves over time
- Each run learns from previous executions
- Proposes targeted improvements
- Applies changes safely with policy gates

### 2. Context Enrichment
- **Vector Databases**: Semantic search for similar issues
- **S3**: Persistent storage and archival
- **Slack**: Team collaboration and approval
- Combine multiple sources for rich context

### 3. Observability
- **OpenTelemetry**: Distributed tracing
- **Grafana**: Visualization and dashboards
- **Structured Logging**: Correlated logs with traces
- **Metrics**: Prometheus-compatible metrics

### 4. AI Framework Integration
- **Pydantic AI**: Type-safe agent optimization
- **LangChain**: Chain optimization
- **CrewAI**: Multi-agent coordination
- Automatic prompt improvement
- Performance monitoring

### 5. Production Patterns
- **Retry Logic**: Intelligent exponential backoff
- **A/B Testing**: Compare configurations
- **Multi-stage Pipelines**: Complex workflow orchestration
- **Docker/Kubernetes**: Production deployment

## 🎯 Choosing the Right Example

### I'm new to AutoFlow...
→ Start with `basic/demo.py` to understand fundamentals

### I want to optimize prompts...
→ Try `basic/continuous_demo.py` for AI prompt optimization

### I need to integrate with my vector DB...
→ Check `context_sources/vector_database_context.py`

### I want team approval for changes...
→ See `context_sources/slack_integration.py`

### I need full observability...
→ Run `integrations/observability/otel_grafana_integration.py`

### I'm using Pydantic AI/LangChain/CrewAI...
→ Check `integrations/ai_frameworks/ai_frameworks_integrations.py`

### I'm deploying to production...
→ Review `production/docker_deployment.py`

## 🔍 Common Patterns

### Pattern 1: Track and Optimize

```python
from autoflow import AutoImproveEngine
from autoflow.observe.events import make_event

# Create engine
engine = AutoImproveEngine(...)

# Track events
engine.ingest([
    make_event(source="my_app", name="request", attributes={...}),
    make_event(source="my_app", name="error", attributes={...}),
])

# Get improvements
proposals = engine.propose()

# Apply safely
results = engine.evaluate(proposals)
applied = engine.apply(proposals, results)
```

### Pattern 2: Context Enrichment

```python
from autoflow.graph.context_graph import ContextGraphBuilder

# Build graph with external context
builder = ContextGraphBuilder()
graph = builder.build_from_events(events, store)

# Query for relevant context
related_nodes = store.query_nodes(
    node_type="context",
    properties={"issue_type": "timeout"},
)
```

### Pattern 3: Observability

```python
from autoflow.otel import span
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("workflow"):
    with span("processing"):
        # Your code here
        pass
```

## 📖 Additional Resources

- **Main Documentation**: `../README.md`
- **API Reference**: `../docs/api.md`
- **Architecture**: `../docs/architecture.md`
- **Contributing**: `../CONTRIBUTING.md`

## 🤝 Contributing Examples

Have a great example? We'd love to add it!

1. Place it in the appropriate subdirectory
2. Add comprehensive comments
3. Include requirements in docstring
4. Add environment variable documentation
5. Test with local development setup

## ❓ Getting Help

- **GitHub Issues**: https://github.com/your-org/autoflow/issues
- **Discord**: Join our Discord community
- **Documentation**: https://autoflow.readthedocs.io

## 📝 License

All examples are part of the AutoFlow project and share the same license.
