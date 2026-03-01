# AutoFlow Examples Summary

Comprehensive example suite demonstrating AutoFlow integrations and use cases.

## 📊 Example Statistics

- **Total Examples**: 13 Python files
- **Lines of Code**: ~8,000+ lines
- **Integrations Covered**: 10+ platforms/services
- **Patterns Demonstrated**: 5 core patterns

## 📁 Complete Directory Structure

```
examples/
├── README.md                                    # Main examples documentation
│
├── basic/                                      # Getting started examples
│   ├── demo.py                                 # Introduction to AutoFlow
│   ├── workflow_demo.py                        # Workflow tracking basics
│   ├── openai_demo.py                          # OpenAI integration
│   ├── multistep_demo.py                       # Multi-step workflows
│   ├── continuous_demo.py                      # Continuous learning (real OpenAI)
│   └── continuous_demo_mock.py                 # Continuous learning (mocked)
│
├── context_sources/                            # External context integrations
│   ├── vector_database_context.py              # Vector DB integration
│   │   ├── Pinecone support
│   │   ├── ChromaDB support
│   │   └── Weaviate support
│   │
│   ├── s3_context_source.py                    # AWS S3 integration
│   │   ├── Dataset storage/retrieval
│   │   ├── Configuration management
│   │   └── Event archival
│   │
│   └── slack_integration.py                    # Slack integration
│       ├── Notifications
│       ├── Approval workflow
│       └── Context retrieval
│
├── integrations/
│   ├── ai_frameworks/
│   │   └── ai_frameworks_integrations.py       # AI framework examples
│   │       ├── Pydantic AI
│   │       ├── LangChain
│   │       └── CrewAI
│   │
│   └── observability/
│       └── otel_grafana_integration.py         # Observability stack
│           ├── OpenTelemetry setup
│           ├── Grafana dashboards
│           ├── Tempo tracing
│           ├── Loki logging
│           └── Alloy collector config
│
├── workflow_patterns/
│   └── workflow_patterns.py                    # Common workflow patterns
│       ├── Retry with exponential backoff
│       ├── A/B testing
│       ├── Multi-stage pipelines
│       └── Circuit breaker
│
└── production/
    └── production_deployment.py                # Production deployment
        ├── Docker configuration
        ├── Kubernetes manifests
        ├── Health checks
        ├── Graceful shutdown
        └── Monitoring setup
```

## 🎯 Examples by Category

### 1. Basic Usage (Getting Started)

**Files:**
- `basic/demo.py` - Simple introduction
- `basic/workflow_demo.py` - Workflow tracking
- `basic/openai_demo.py` - OpenAI integration
- `basic/multistep_demo.py` - Multi-step workflows
- `basic/continuous_demo.py` - Continuous learning
- `basic/continuous_demo_mock.py` - Continuous learning (no API key needed)

**What you'll learn:**
- AutoFlow fundamentals
- Event tracking and observation
- Workflow-aware context building
- Proposal generation and evaluation
- Continuous improvement cycles

**Run:**
```bash
cd basic/
python demo.py
```

### 2. Context Sources (External Integration)

**Vector Database Integration** (`context_sources/vector_database_context.py`)

**Features:**
- Semantic search for similar issues
- RAG (Retrieval-Augmented Generation)
- Historical pattern matching
- Support for multiple backends

**Backends:**
- Pinecone (cloud, scalable)
- ChromaDB (local, free)
- Weaviate (open-source)

**Use case:** "I want to find similar past issues and their resolutions"

**Setup:**
```bash
# For ChromaDB (local, free)
pip install chromadb
python context_sources/vector_database_context.py

# For Pinecone
pip install pinecone-client
export PINECONE_API_KEY=your-key
```

---

**AWS S3 Integration** (`context_sources/s3_context_source.py`)

**Features:**
- Persistent event storage
- Dataset archival and retrieval
- Configuration management
- Cross-region sharing

**Use case:** "I want to store and retrieve large datasets"

**Setup:**
```bash
pip install boto3
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
python context_sources/s3_context_source.py
```

---

**Slack Integration** (`context_sources/slack_integration.py`)

**Features:**
- Team notifications
- Approval workflow for changes
- Context retrieval from conversations
- Interactive buttons

**Use case:** "I want human approval before AutoFlow makes changes"

**Setup:**
```bash
pip install slack-sdk
export SLACK_BOT_TOKEN=xoxb-your-token
python context_sources/slack_integration.py
```

### 3. AI Framework Integrations

**File:** `integrations/ai_frameworks/ai_frameworks_integrations.py`

**Supported Frameworks:**

1. **Pydantic AI**
   - Type-safe agent optimization
   - System prompt improvement
   - Validation rule refinement

2. **LangChain**
   - Chain optimization
   - Prompt template improvement
   - Tool selection optimization

3. **CrewAI**
   - Crew composition optimization
   - Agent role refinement
   - Multi-agent coordination

**What you'll learn:**
- Track AI framework executions
- Automatically optimize prompts
- Monitor agent performance
- A/B test different configurations

**Run:**
```bash
pip install pydantic-ai  # or langchain, crewai
export OPENAI_API_KEY=your-key
python integrations/ai_frameworks/ai_frameworks_integrations.py
```

### 4. Observability Integration

**File:** `integrations/observability/otel_grafana_integration.py`

**Complete observability stack:**

```
AutoFlow → OpenTelemetry → Alloy/OTel Collector → Grafana Cloud
                                         ├→ Tempo (traces)
                                         ├→ Prometheus (metrics)
                                         └→ Loki (logs)
```

**Features:**
- Distributed tracing
- Correlated logs with traces
- Metrics collection
- Grafana dashboards
- Alloy configuration generation

**Benefits:**
- Full request traceability
- Performance monitoring
- Error correlation
- Custom dashboards

**Setup:**
```bash
# Install dependencies
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# For local Grafana Tempo
docker run -d -p 4317:4317 grafana/tempo:latest

# Run example
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python integrations/observability/otel_grafana_integration.py
```

**View in Grafana:**
1. Open Grafana
2. Go to Explore → Tempo
3. Search by `service.name=autoflow-engine`
4. See distributed traces with correlated logs and metrics

### 5. Workflow Patterns

**File:** `workflow_patterns/workflow_patterns.py`

**Patterns:**

1. **Retry with Exponential Backoff**
   - Learns optimal retry intervals
   - Tracks success/failure rates
   - Knows when to give up

2. **A/B Testing**
   - Compare multiple configurations
   - Track success rates
   - Auto-select winner

3. **Multi-Stage Pipelines**
   - Track each stage independently
   - Identify bottlenecks
   - Optimize ordering

4. **Circuit Breaker**
   - Detect failing services
   - Prevent cascading failures
   - Auto-recovery detection

**Run:**
```bash
python workflow_patterns/workflow_patterns.py
```

### 6. Production Deployment

**File:** `production/production_deployment.py`

**What's included:**

1. **Docker Configuration**
   - Multi-stage Dockerfile
   - Health checks
   - Resource limits

2. **Kubernetes Deployment**
   - Deployment manifests
   - Service configuration
   - ConfigMap/Secret management
   - HPA (Horizontal Pod Autoscaler)
   - PDB (Pod Disruption Budget)
   - Probes (liveness, readiness, startup)

3. **Production Features**
   - Graceful shutdown
   - Health check endpoints
   - OpenTelemetry integration
   - Prometheus metrics
   - Structured logging

**Generate manifests:**
```bash
# Generate Kubernetes manifests
python production/production_deployment.py generate-manifests > k8s.yaml

# Generate Dockerfile
python production/production_deployment.py generate-dockerfile > Dockerfile

# Deploy to Kubernetes
kubectl apply -f k8s.yaml
```

**Check status:**
```bash
kubectl get pods -n autoflow
kubectl logs -f deployment/autoflow-engine -n autoflow
```

## 🚀 Quick Start Guide

### For Beginners

1. **Start here:** `basic/demo.py`
2. **Try workflows:** `basic/workflow_demo.py`
3. **See continuous learning:** `basic/continuous_demo_mock.py` (no API key needed!)

### For AI/ML Engineers

1. **Framework integration:** `integrations/ai_frameworks/ai_frameworks_integrations.py`
2. **Continuous improvement:** `basic/continuous_demo.py`
3. **Vector search:** `context_sources/vector_database_context.py`

### For DevOps/SRE

1. **Production deployment:** `production/production_deployment.py`
2. **Observability:** `integrations/observability/otel_grafana_integration.py`
3. **Circuit breaker:** `workflow_patterns/workflow_patterns.py`

### For Data Engineers

1. **S3 storage:** `context_sources/s3_context_source.py`
2. **Pipelines:** `workflow_patterns/workflow_patterns.py`
3. **Vector database:** `context_sources/vector_database_context.py`

## 📝 Key Features Demonstrated

### Across All Examples

✅ **Event Tracking**
- All examples show how to track events
- Structured event attributes
- Workflow correlation

✅ **Context Building**
- Graph-based context
- External context sources
- Semantic search

✅ **Proposal Generation**
- Rule-based improvements
- Pattern detection
- Issue analysis

✅ **Evaluation**
- Safety gates
- Risk assessment
- Policy enforcement

✅ **Observability**
- OpenTelemetry integration
- Structured logging
- Metrics collection

## 🔧 Requirements by Example

### No Dependencies
- `basic/demo.py`
- `basic/workflow_demo.py`
- `basic/continuous_demo_mock.py`
- `workflow_patterns/workflow_patterns.py`

### OpenAI API Key
- `basic/openai_demo.py`
- `basic/continuous_demo.py`
- `basic/multistep_demo.py`
- `integrations/ai_frameworks/ai_frameworks_integrations.py`

### Vector Database (choose one)
- `context_sources/vector_database_context.py`
  - ChromaDB (local, free): `pip install chromadb`
  - Pinecone: `pip install pinecone-client`
  - Weaviate: `pip install weaviate-client`

### AWS Account
- `context_sources/s3_context_source.py`
  - `pip install boto3`
  - AWS credentials required

### Slack App
- `context_sources/slack_integration.py`
  - `pip install slack-sdk`
  - Create Slack app, get bot token

### Observability Stack
- `integrations/observability/otel_grafana_integration.py`
  - `pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp`
  - Grafana Tempo/OTel collector (or use cloud)

### Production Infrastructure
- `production/production_deployment.py`
  - Docker
  - Kubernetes cluster
  - (Optional) Grafana Cloud

## 🎓 Learning Path

### Level 1: Fundamentals (1-2 hours)
1. Read `examples/README.md`
2. Run `basic/demo.py`
3. Run `basic/workflow_demo.py`
4. Run `basic/continuous_demo_mock.py`

### Level 2: Integrations (2-3 hours)
1. Choose your context source (S3, Vector DB, or Slack)
2. Run the example
3. Understand the integration pattern
4. Modify for your use case

### Level 3: AI Frameworks (2-3 hours)
1. Choose your framework (Pydantic AI, LangChain, or CrewAI)
2. Run the example
3. See how AutoFlow optimizes it
4. Build your own optimized workflow

### Level 4: Observability (1-2 hours)
1. Set up local Grafana Tempo
2. Run `otel_grafana_integration.py`
3. View traces in Grafana
4. Understand correlation

### Level 5: Production (2-4 hours)
1. Generate Kubernetes manifests
2. Deploy to local cluster (kind, minikube)
3. Test health probes
4. Configure monitoring

## 📚 Additional Resources

### Documentation
- Main README: `../README.md`
- API Reference: `../docs/api.md`
- Architecture: `../docs/architecture.md`

### Community
- GitHub Issues: Report bugs and request features
- Discord: Live discussion and help
- Examples: Contributed by community

## 🤝 Contributing Examples

We welcome contributions!

1. Place in appropriate subdirectory
2. Add comprehensive comments
3. Include requirements in docstring
4. Document environment variables
5. Test locally before submitting

### Example Categories We'd Love
- Redis integration
- Kafka message queue
- GraphQL API
- gRPC service
- Database query optimization
- ML model monitoring
- Cost optimization

## ❓ FAQ

**Q: Which example should I start with?**
A: Start with `basic/demo.py` for fundamentals.

**Q: Do I need all dependencies?**
A: No! Each example lists its specific requirements.

**Q: Can I run examples without API keys?**
A: Yes! Use `continuous_demo_mock.py` instead of `continuous_demo.py`.

**Q: How do I integrate with my own service?**
A: Start with the basic examples, then adapt the pattern.

**Q: Can I use multiple integrations together?**
A: Absolutely! You can combine vector DB + S3 + Slack + OTEL.

**Q: Do examples work with Windows?**
A: Yes, all examples are cross-platform.

**Q: How can I get help?**
A: GitHub Issues, Discord, or check the documentation.

## 📞 Support

- **Documentation**: https://autoflow.readthedocs.io
- **GitHub**: https://github.com/your-org/autoflow
- **Discord**: https://discord.gg/autoflow
- **Email**: support@autoflow.dev

## 📄 License

All examples are part of the AutoFlow project and share the same license.
