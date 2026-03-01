# AutoFlow Notifications & Human-in-the-Loop Guide

## Overview

AutoFlow now has **comprehensive notification and human-in-the-loop** support:

✅ **Multiple notification channels** (console, file, webhook, etc.)
✅ **LLM-as-Judge evaluation** (GPT-4, Claude, Grok, Ollama, etc. review your proposals)
✅ **Flexible approval modes** (auto, manual, hybrid, LLM judge)
✅ **Proposal tracking** (persistent storage of all proposals and decisions)
✅ **Rich context** (triggering events, graph state, evaluation results)
✅ **Provider-agnostic LLM support** (OpenAI, Anthropic, AWS Bedrock, xAI, Ollama, Azure)
✅ **Graph visualizations** (Mermaid diagrams with issues and proposals highlighted)

## 🎯 Quick Start

### 1. Simple Manual Review (Default)
```python
from autoflow.notifications import autoflow_manual_review
from autoflow.observe.events import make_event

# Create workflow with console notifications
workflow = autoflow_manual_review()

# Generate proposals
events = [make_event(source="agent", name="error", attributes={...})]
proposals = await engine.propose()  # Your existing code

# Send to human review
await workflow.propose(proposals, context={"triggering_events": events})

# Later, review and approve
pending = await workflow.list_pending()
await workflow.approve_all(reviewer="admin")
```

### 2. LLM-as-Judge (Automatic with AI Review)
```python
from autoflow.notifications import autoflow_llm_judge

# LLM evaluates and auto-approves high-confidence proposals
workflow = autoflow_llm_judge(
    model="gpt-4",
    auto_approve_threshold=0.8,
)

await workflow.propose(proposals, context)

# LLM provides:
# - Safety assessment
# - Correctness evaluation
# - Side effect analysis
# - Best practices check
# - Overall recommendation
```

**Supported LLM Providers:**

```python
# OpenAI (GPT-4, GPT-3.5)
workflow = autoflow_llm_judge(model="gpt-4")

# Anthropic (Claude 3, Claude 3.5 Sonnet)
workflow = autoflow_llm_judge(model="claude-3-5-sonnet-20241022")

# AWS Bedrock
workflow = autoflow_llm_judge(
    model="amazon.titan-text-express-v1",
    region="us-east-1",
)

# xAI (Grok)
workflow = autoflow_llm_judge(model="grok-beta")

# Ollama (local models)
workflow = autoflow_llm_judge(model="llama3:8b")
workflow = autoflow_llm_judge(model="deepseek-coder")

# Azure OpenAI
workflow = autoflow_llm_judge(model="azure/gpt-4")
```

### 3. Hybrid Mode (Balance)
```python
from autoflow.notifications import autoflow_hybrid

workflow = autoflow_hybrid()

# Low-risk: auto-approved
# High-risk: requires human review
await workflow.propose(proposals, context)
```

## 📢 Notification Channels

### Console Notifications (Default)
```python
from autoflow.notify.notifier import create_notifier

notifier = create_notifier("console")

# Output looks like:
# ======================================================================
# 📋 2 New Proposal(s) Generated
# ======================================================================
#
# [1] Increase retry threshold for API workflow
#     ID: 550e8400-e29b-41d4-a716-446655440000
#     Kind: config_edit
#     Risk: low
#     Paths: config/workflows.yaml
#     Description: The API workflow is failing frequently...
#
#     📊 Context:
#     Recent events (3):
#       - execution_failed from agent
#       - execution_failed from agent
#       - execution_failed from agent
```

### File Notifications
```python
# JSONL format (one proposal per line)
notifier = create_notifier(
    "file",
    output_path="proposals.jsonl",
)

# Markdown format
notifier = create_notifier(
    "file",
    output_path="proposals.md",
    format="markdown",
)
```

### Webhook Notifications
```python
notifier = create_notifier(
    "webhook",
    webhook_url="https://your-domain.com/autoflow/webhook",
    headers={"Authorization": "Bearer token123"},
)
```

### Multiple Channels
```python
notifier = create_notifier([
    "console",           # Print to terminal
    "file",              # Save to file
    "webhook",           # Send to API
])
```

## 📊 Graph Visualizations

AutoFlow can automatically generate **Mermaid diagrams** showing:
- Current code structure and dependencies
- Issues highlighted (red dashed borders)
- Proposed changes highlighted (green thick borders)
- Before/after comparisons

### Enable Visualizations in Notifications

```python
from autoflow.notifications import autoflow_manual_review

workflow = autoflow_manual_review(
    notify="console",
    include_visualizations=True,  # Enable visualizations
)

# Provide graph data in context
await workflow.propose(proposals, context={
    "graph_nodes": nodes,  # List[GraphNode]
    "graph_edges": edges,  # List[GraphEdge]
    "triggering_events": events,
})
```

### Console Output with Visualizations

```
📋 1 New Proposal Generated

[1] Add retry logic to API client
    ID: 123e4567-e89b-12d3-a456-426614174000
    Risk: low
    Description: The API client is failing intermittently...

    📊 Context:
    Recent events (3):
      - timeout from api

    📈 Graph Visualization:
    ------------------------------------------------------------------
    graph TB
        A[API Client] --> B[Database]
        style B stroke:#f44336,stroke-width:3px,stroke-dasharray: 5 5
    ------------------------------------------------------------------

    Legend:
      🔴 Red dashed = Issue detected
      🟢 Green thick = Proposed change
```

### File Notifications with Visualizations

```python
workflow = autoflow_manual_review(
    notify="file",
    notification_config={
        "output_path": "proposals.md",
        "format": "markdown",
        "include_visualizations": True,
        "visualization_dir": "autoflow_viz",
    },
)

# This creates:
# - proposals.md with proposal details and mermaid diagrams
# - autoflow_viz/ directory with .mmd files
```

### Standalone Visualization

```python
from autoflow.viz.mermaid import visualize_context_graph, visualize_proposals

# Basic visualization
viz = visualize_context_graph(nodes, edges)
print(viz.to_markdown())
viz.save("my_graph.mmd")

# With issues highlighted
viz = visualize_context_graph(
    nodes,
    edges,
    issue_node_ids={"api_client", "database"},
)

# With proposals
viz = visualize_context_graph(
    nodes,
    edges,
    proposals=[proposal1, proposal2],
)

# Before/after comparison
visualizations = visualize_proposals(nodes, edges, proposals)
visualizations["before"].save("before.mmd")
visualizations["after"].save("after.mmd")
visualizations["diff"].save("diff.mmd")
```

### Viewing Mermaid Diagrams

Mermaid diagrams can be viewed in:

- **GitHub/GitLab**: Native support in markdown files
- **Mermaid Live Editor**: https://mermaid.live
- **VS Code**: Install "Mermaid Preview" extension
- **Command line**: `npx @mermaid-js/mermaid-cli -i input.mmd -o output.png`

For complete visualization documentation, see [VISUALIZATION.md](VISUALIZATION.md).

## 🤖 LLM-as-Judge Details

### What LLM Judge Evaluates

For each proposal, the LLM assesses:

1. **Safety** (30% weight)
   - Could this introduce bugs?
   - Security vulnerabilities?
   - Breaking changes?

2. **Correctness** (30% weight)
   - Does it address the issue?
   - Is the approach sound?
   - Are there edge cases?

3. **Side Effects** (20% weight)
   - What else could be affected?
   - Any unintended consequences?

4. **Best Practices** (20% weight)
   - Follows language conventions?
   - Good code structure?
   - Proper error handling?

### LLM Response Format
```json
{
  "safety_score": 0.9,
  "correctness_score": 0.8,
  "side_effects_score": 0.7,
  "best_practices_score": 0.85,
  "reasoning": "Detailed analysis...",
  "concerns": "Minor concern about...",
  "suggestions": "Consider adding..."
}
```

### Configuration
```python
from autoflow.evaluate.llm_judge import LLMJudgeEvaluator, LLMJudgeConfig

config = LLMJudgeConfig(
    model="gpt-4",  # Auto-detects provider from model name
    provider=None,  # Optional: force specific provider
    api_key="sk-...",
    check_safety=True,
    check_correctness=True,
    check_side_effects=True,
    check_best_practices=True,
    safety_weight=0.3,
    pass_threshold=0.6,
    auto_approve_threshold=0.8,
)

evaluator = LLMJudgeEvaluator(config=config)

# Or use environment variables:
# export AUTOFLOW_LLM_JUDGE_MODEL="claude-3-5-sonnet-20241022"
# export AUTOFLOW_LLM_JUDGE_API_KEY="sk-ant-..."
# export AUTOFLOW_LLM_JUDGE_PROVIDER="anthropic"
evaluator = LLMJudgeEvaluator(config=LLMJudgeConfig.from_env())
```

**Environment Variables:**

```bash
# Model selection
export AUTOFLOW_LLM_JUDGE_MODEL="gpt-4"  # or claude-3-5-sonnet-20241022, etc.

# Provider (optional, auto-detected from model name)
export AUTOFLOW_LLM_JUDGE_PROVIDER="openai"  # or anthropic, bedrock, xai, ollama

# API credentials
export AUTOFLOW_LLM_JUDGE_API_KEY="sk-..."
export AUTOFLOW_LLM_JUDGE_BASE_URL="https://api.example.com"

# AWS Bedrock (if using Bedrock)
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI (default)
export OPENAI_API_KEY="sk-..."

# xAI (Grok)
export XAI_API_KEY="..."

# Ollama (local)
export OLLAMA_BASE_URL="http://localhost:11434"
```

### Using LLM Judge Standalone
```python
from autoflow.evaluate.llm_judge import LLMJudgeEvaluator
from autoflow.types import ChangeProposal

# With default (GPT-4)
evaluator = LLMJudgeEvaluator()

result = evaluator.evaluate(proposal)

print(f"Passed: {result.passed}")
print(f"Score: {result.score}")
print(f"Notes: {result.notes}")
print(f"Model: {result.metrics.get('judge_model')}")
print(f"Provider: {result.metrics.get('judge_provider')}")
```

**Examples with Different Providers:**

```python
# Anthropic Claude
evaluator = LLMJudgeEvaluator(
    config=LLMJudgeConfig(
        model="claude-3-5-sonnet-20241022",
        api_key="sk-ant-...",
    )
)

# AWS Bedrock
evaluator = LLMJudgeEvaluator(
    config=LLMJudgeConfig(
        model="amazon.titan-text-express-v1",
        region="us-east-1",
    )
)

# Ollama local model
evaluator = LLMJudgeEvaluator(
    config=LLMJudgeConfig(
        model="llama3:8b",
        base_url="http://localhost:11434",
    )
)

# xAI Grok
evaluator = LLMJudgeEvaluator(
    config=LLMJudgeConfig(
        model="grok-beta",
        api_key="...",
    )
)
```

## 🔄 Approval Modes

### 1. Auto Mode
```python
workflow = autoflow_with_notifications(approval_mode="auto")

# All proposals auto-approved
# Best for: Fully automated pipelines, testing environments
```

### 2. Manual Mode
```python
workflow = autoflow_with_notifications(approval_mode="manual")

# All proposals require human approval
# Best for: Production, critical systems
```

### 3. Hybrid Mode
```python
workflow = autoflow_with_notifications(approval_mode="hybrid")

# Low-risk: auto-approved
# High-risk: manual review required
# Best for: Balance of automation and safety
```

### 4. LLM Judge Mode
```python
workflow = autoflow_with_notifications(approval_mode="llm_judge")

# LLM evaluates all proposals
# High confidence (>0.8): auto-approved
# Low confidence: requires human review
# Best for: AI-assisted code review
```

## 📋 Information Provided in Notifications

### For Each Proposal:
```python
ProposalNotification {
    # Core proposal data
    proposal_id: "uuid",
    title: "Fix timeout issue",
    kind: "config_edit",
    risk: "low",
    description: "Detailed description...",

    # Status and evaluation
    status: "pending",  # pending, approved, rejected, applied, failed
    evaluator: "human",  # human, llm_judge, auto
    evaluation_result: {score: 0.85, ...},

    # Context (why was this proposed?)
    triggering_events: [
        {source: "agent", name: "error", attributes: {...}}
    ],
    graph_context: {
        "error_rate": 0.15,
        "affected_nodes": 5,
    },

    # Human-friendly summaries
    summary: "LLM recommendation...",
    risk_explanation: "Low risk because...",
    implementation_plan: "Step 1: Do X, Step 2: Do Y...",
}
```

## 🎨 Usage Examples

### Example 1: Agent Factory with LLM Judge
```python
from autoflow.notifications import autoflow_llm_judge
from autoflow.track import track_agent

class AgentFactory:
    def __init__(self):
        # One-time setup with your preferred LLM
        self.autoflow = autoflow_llm_judge(
            model="claude-3-5-sonnet-20241022",  # Or gpt-4, llama3:8b, etc.
            auto_approve_threshold=0.75,
        )

    @track_agent(agent_id="my_agent")
    async def create_agent(self, config):
        async def agent(query):
            return await self._run_agent(config, query)
        return agent

    async def _run_agent(self, config, query):
        # ... agent logic ...
        # If errors occur, AutoFlow proposes fixes
        # LLM judge evaluates them automatically
        return result
```

### Example 2: Interactive CLI for Review
```python
from autoflow.notifications import autoflow_manual_review
from autoflow.human_in_the_loop import review_pending_proposals

workflow = autoflow_manual_review(
    notify="console",
    proposal_store_path="proposals.json",
)

# ... proposals are generated ...

# Interactive review
await review_pending_proposals(workflow, interactive=True)

# CLI prompts:
# [1] Fix timeout issue
#     ID: 123
#     Risk: low
#     Approve? [y/n/a=skip] y
#     ✅ Approved
```

### Example 3: Webhook Integration (Slack/Discord)
```python
from autoflow.notify.notifier import WebhookNotificationChannel
from autoflow.human_in_the_loop import HumanInTheLoopWorkflow

# Set up webhook (e.g., to Slack)
notifier = WebhookNotificationChannel(
    webhook_url=os.environ["SLACK_WEBHOOK_URL"],
)

workflow = HumanInTheLoopWorkflow(
    approval_mode="manual",
    notifier=notifier,
)

# Proposals will be posted to Slack channel
# Users can click buttons to approve/reject
await workflow.propose(proposals, context)
```

### Example 4: File-Based Review (Async)
```python
from autoflow.notifications import autoflow_manual_review

workflow = autoflow_manual_review(
    notify=["console", "file"],
    notification_config={"output_path": "pending.jsonl"},
)

# Proposals written to file
await workflow.propose(proposals, context)

# Later, read and approve
import json
with open("pending.jsonl") as f:
    for line in f:
        notif = ProposalNotification(**json.loads(line))
        if notif.proposal.risk == "low":
            await workflow.submit_decision(
                notif.proposal.proposal_id,
                approved=True,
                reviewer="batch-script",
            )
```

## 🔧 Advanced Configuration

### Custom Notification Channel
```python
from autoflow.notify.notifier import NotificationChannel

class SlackNotificationChannel(NotificationChannel):
    async def notify_proposals(self, proposals, context):
        # Your Slack integration logic
        for proposal in proposals:
            await self._send_to_slack(proposal)

    async def notify_evaluation(self, proposal, result):
        await self._send_to_slack(f"Evaluation: {result.passed}")

workflow = HumanInTheLoopWorkflow(
    notifier=SlackNotificationChannel(),
)
```

### Custom Evaluator
```python
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.llm_judge import LLMJudgeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator

evaluator = CompositeEvaluator(evaluators=[
    ShadowEvaluator(),           # Shadow testing
    LLMJudgeEvaluator(),         # LLM review
    MyCustomEvaluator(),          # Your custom logic
])

workflow = HumanInTheLoopWorkflow(
    approval_mode="llm_judge",
    notifier=create_notifier("console"),
)
```

## 📊 Summary Table

| Feature | Implementation |
|---------|----------------|
| **Console Notifications** | ✅ `create_notifier("console")` |
| **File Notifications** | ✅ `create_notifier("file", output_path="...")` |
| **Webhook Notifications** | ✅ `create_notifier("webhook", webhook_url="...")` |
| **Multiple Channels** | ✅ `create_notifier(["console", "file", "webhook"])` |
| **LLM-as-Judge** | ✅ `autoflow_llm_judge(model="gpt-4")` |
| **Human-in-the-Loop** | ✅ `autoflow_manual_review()` |
| **Hybrid Mode** | ✅ `autoflow_hybrid()` |
| **Auto-Approve** | ✅ `autoflow_auto_approve()` |
| **Proposal Tracking** | ✅ Persistent JSON store |
| **Rich Context** | ✅ Events, graph state, evaluation |
| **Interactive CLI** | ✅ `review_pending_proposals()` |

## 🎯 What Makes It Strong

1. **Multiple Approval Modes**: Auto, manual, hybrid, LLM judge
2. **Rich Notifications**: Console, file, webhook, or custom
3. **Full Context**: Proposals include triggering events and graph state
4. **LLM Integration**: GPT-4 evaluates safety, correctness, side effects
5. **Persistent Tracking**: All proposals and decisions stored
6. **Async-First**: Native async/await throughout
7. **Minimal Code**: One-line setup for common cases
8. **Factory-Ready**: Works great with agent/tool factories
9. **Extensible**: Easy to add custom channels and evaluators
10. **Human-Friendly**: Rich formatting and summaries

## 🚀 Next Steps

1. **Install dependencies**:
   - OpenAI: `pip install openai`
   - Anthropic: `pip install anthropic`
   - AWS Bedrock: `pip install boto3`
   - xAI/Ollama: `pip install openai` (OpenAI-compatible API)

2. **Set API key** (choose your provider):
   - OpenAI: `export OPENAI_API_KEY=sk-...`
   - Anthropic: `export ANTHROPIC_API_KEY=sk-ant-...`
   - AWS: `export AWS_ACCESS_KEY_ID=...`
   - xAI: `export XAI_API_KEY=...`

3. **Choose mode**: Pick approval mode based on your use case
4. **Start simple**: Use `autoflow_manual_review()` for production
5. **Iterate**: Add LLM judge or hybrid mode as you get comfortable

The system is designed to be **safe by default** (manual review) while allowing **automation** when you're ready!

## 🤖 Provider-Agnostic LLM Support

AutoFlow's LLM-as-Judge now supports **multiple LLM providers** through a unified interface:

### Supported Providers

| Provider | Model Examples | Notes |
|----------|---------------|-------|
| **OpenAI** | `gpt-4`, `gpt-3.5-turbo` | Default |
| **Anthropic** | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229` | Requires `anthropic` package |
| **AWS Bedrock** | `amazon.titan-text-express-v1`, `anthropic.claude-3-sonnet-20240229-v1:0` | Requires `boto3` package |
| **xAI (Grok)** | `grok-beta` | OpenAI-compatible API |
| **Ollama** | `llama3:8b`, `deepseek-coder`, `mistral` | Local models, OpenAI-compatible API |
| **Azure OpenAI** | `azure/gpt-4` | Requires Azure OpenAI endpoint |

### Auto-Detection

The provider is automatically detected from the model name:

```python
# Automatically detected as Anthropic
autoflow_llm_judge(model="claude-3-5-sonnet-20241022")

# Automatically detected as OpenAI
autoflow_llm_judge(model="gpt-4")

# Automatically detected as Ollama (has colon)
autoflow_llm_judge(model="llama3:8b")

# Automatically detected as Bedrock
autoflow_llm_judge(model="amazon.titan-text-express-v1")

# Automatically detected as xAI
autoflow_llm_judge(model="grok-beta")
```

### Manual Provider Selection

You can also explicitly specify the provider:

```python
autoflow_llm_judge(
    model="my-custom-model",
    provider="anthropic",  # Force Anthropic client
    api_key="sk-ant-...",
)
```

### Low-Level Client Usage

For advanced use cases, you can use the UniversalLLMClient directly:

```python
from autoflow.llm.client import create_llm_client

# Create client (auto-detects provider)
client = create_llm_client(model="claude-3-5-sonnet-20241022")

# Or explicitly
client = create_llm_client(
    model="gpt-4",
    provider="openai",
    api_key="sk-...",
)

# Send chat completion
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"},
    ],
    response_format={"type": "json_object"},  # For structured output
)
```

### Provider-Specific Notes

**Anthropic (Claude):**
- Install: `pip install anthropic`
- API key: `export ANTHROPIC_API_KEY=sk-ant-...`
- System prompts are handled separately (following Anthropic's API)
- JSON mode is achieved through prompt engineering

**AWS Bedrock:**
- Install: `pip install boto3`
- Credentials: Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Region: Set `AWS_DEFAULT_REGION` (default: `us-east-1`)
- Model IDs follow Bedrock conventions

**Ollama (Local):**
- Install Ollama: https://ollama.ai
- Pull models: `ollama pull llama3:8b`
- Default URL: `http://localhost:11434`
- No API key required

**xAI (Grok):**
- Uses OpenAI-compatible API
- Base URL: `https://api.x.ai/v1`
- API key from xAI platform

**Azure OpenAI:**
- Set `base_url` to your Azure endpoint
- Model names prefixed with `azure/`
- Requires Azure OpenAI API key
