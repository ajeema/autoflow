# Proposals API

## Overview

`ChangeProposal` is a typed, auditable suggestion for improving your system. All proposals flow through evaluation before being applied.

---

## Core Types

### ChangeProposal

```python
@dataclass(frozen=True)
class ChangeProposal:
    proposal_id: str
    kind: ProposalKind
    title: str
    description: str
    risk: RiskLevel
    target_paths: Sequence[str]
    payload: Mapping[str, Any]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | `str` | Unique identifier (UUID) |
| `kind` | `ProposalKind` | Type of change (TEXT_PATCH or CONFIG_EDIT) |
| `title` | `str` | Human-readable title |
| `description` | `str` | Detailed description of what and why |
| `risk` | `RiskLevel` | LOW, MEDIUM, or HIGH |
| `target_paths` | `Sequence[str]` | Files/configs to modify |
| `payload` | `Mapping[str, Any]` | Change details |

### ProposalKind

```python
class ProposalKind(str, Enum):
    TEXT_PATCH = "text_patch"      # Apply a text diff/patch
    CONFIG_EDIT = "config_edit"      # Edit configuration values
```

### RiskLevel

```python
class RiskLevel(str, Enum):
    LOW = "low"      # Safe changes (add retries, increase timeouts)
    MEDIUM = "medium"  # Moderate risk (change logic, add dependencies)
    HIGH = "high"     # Risky changes (schema changes, breaking changes)
```

---

## Creating Proposals

### Text Patch Proposal

```python
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from uuid import uuid4

proposal = ChangeProposal(
    proposal_id=str(uuid4()),
    kind=ProposalKind.TEXT_PATCH,
    title="Fix error handling in data loader",
    description="Add try-catch blocks to database connection logic",
    risk=RiskLevel.LOW,
    target_paths=("src/data_loader.py",),
    payload={
        "patch": """
--- a/src/data_loader.py
+++ b/src/data_loader.py
@@ -15,7 +15,11 @@
     try:
         connection = db.connect()
-        data = connection.query("SELECT * FROM users")
+        data = connection.query("SELECT * FROM users")
+    except DatabaseError as e:
+        logger.error(f"Database error: {e}")
+        raise
     finally:
         connection.close()
""",
        "format": "unified",
    },
)
```

### Config Edit Proposal

```python
proposal = ChangeProposal(
    proposal_id=str(uuid4()),
    kind=ProposalKind.CONFIG_EDIT,
    title="Increase retry limit",
    description="Observed 5 timeout errors in the last hour",
    risk=RiskLevel.LOW,
    target_paths=("config/workflows/api.yaml",),
    payload={
        "op": "set",
        "path": "workflows.api.retry_policy.max_retries",
        "value": 5,
        "old_value": 2,
    },
)
```

### JSON Path Proposal

```python
proposal = ChangeProposal(
    proposal_id=str(uuid4()),
    kind=ProposalKind.CONFIG_EDIT,
    title="Adjust cache TTL",
    description="Reduce cache hits to improve data freshness",
    risk=RiskLevel.LOW,
    target_paths=("config/cache.yaml",),
    payload={
        "op": "set",
        "path": "cache.default_ttl",
        "value": 300,
        "old_value": 600,
    },
)
```

---

## Proposal Payload Patterns

### Retry Policy Change

```python
payload={
    "step": "api_call",
    "setting": "retry_policy",
    "value": {
        "max_retries": 3,
        "backoff_ms": [1000, 2000, 5000],
        "jitter": True,
    },
}
```

### Timeout Adjustment

```python
payload={
    "step": "extract",
    "setting": "timeout_ms",
    "value": 15000,
    "old_value": 5000,
}
```

### Prompt Change

```python
payload={
    "prompt_name": "summarization",
    "setting": "system_prompt",
    "value": "You are a helpful assistant. Be concise and accurate.",
}
```

### Feature Flag Toggle

```python
payload={
    "feature_flag": "new_algorithm_v2",
    "enabled": True,
}
```

### Configuration Addition

```python
payload={
    "op": "append",
    "path": "load_balancer.pools",
    "value": {
        "name": "pool_4",
        "host": "server4.example.com",
        "port": 8080,
    },
}
```

---

## Proposal Best Practices

### DO ✅

**1. Use Clear, Descriptive Titles**
```python
# Good
title="Increase timeout for external API calls"

# Avoid
title="Fix timeout"
```

**2. Provide Context in Description**
```python
# Good
description=(
    "External API timeouts have increased from 2% to 15% in the last 24h. "
    "Current timeout of 5000ms is insufficient for peak loads. "
    "Increasing to 15000ms to accommodate P95 latency."
)

# Avoid
description="Timeout is too low"
```

**3. Match Risk to Impact**
```python
# Safe changes
risk=RiskLevel.LOW
title="Add cache for expensive queries"

# Moderate changes
risk=RiskLevel.MEDIUM
title="Change database schema (add index)"

# Risky changes
risk=RiskLevel.HIGH
title="Migrate database to new schema version"
```

**4. Target Specific Paths**
```python
# Good - specific
target_paths=("config/services/database.yaml",)

# Avoid - too broad
target_paths=("config/",)  # Could affect multiple services

# Avoid - root directory
target_paths=("*",)  # DANGEROUS
```

### DON'T ❌

**1. Don't Omit Context**
```python
# Avoid
description="Fix config"  # What config? Why?

# Good
description="Increase max_retries in API workflow config"
```

**2. Don't Hardcode Paths**
```python
# Avoid
payload={"path": "/home/user/app/config.yaml"}

# Good
payload={"path": "config/workflows.yaml"}
```

**3. Don't Mix Concerns**
```python
# Avoid - does two things
proposal = ChangeProposal(
    title="Fix multiple issues",
    payload={
        "fix_timeout": True,
        "add_cache": True,
        "change_prompt": "...",
    },
)

# Good - one proposal per issue
```

---

## Proposal Lifecycle

```
┌──────────────┐
│  Generated   │  By DecisionGraph rules
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Evaluated   │  By Evaluator (shadow/replay)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Policy Check│  By ApplyPolicy
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Applied      │  By Backend (git, etc.)
└──────────────┘
```

### Evaluation

```python
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.types import EvaluationResult

evaluator = ShadowEvaluator()
result = evaluator.evaluate(proposal)

print(result.passed)   # True/False
print(result.score)    # 0.0 - 1.0
print(result.notes)    # Additional notes
```

### Policy Check

```python
from autoflow.apply.policy import ApplyPolicy
from autoflow.types import RiskLevel

policy = ApplyPolicy(
    allowed_paths_prefixes=("config/", "prompts/"),
    max_risk=RiskLevel.LOW,
)

policy.assert_allowed(proposal)  # Raises PolicyViolation if not allowed
```

### Application

```python
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend

applier = ProposalApplier(
    policy=policy,
    backend=GitApplyBackend(repo_path=Path(".")),
)

applier.apply(proposal)  # Applies the proposal
```

---

## Proposal Examples

### Example 1: Database Optimization

```python
ChangeProposal(
    proposal_id="prop_001",
    kind=ProposalKind.CONFIG_EDIT,
    title="Add database connection pooling",
    description="Current single-connection mode causes slow queries. Adding pool will improve performance.",
    risk=RiskLevel.LOW,
    target_paths=("config/database.yaml",),
    payload={
        "setting": "connection_pool",
        "value": {
            "max_connections": 10,
            "idle_timeout_ms": 30000,
        },
    },
)
```

### Example 2: Prompt Improvement

```python
ChangeProposal(
    proposal_id="prop_002",
    kind=ProposalKind.TEXT_PATCH,
    title="Improve prompt clarity",
    description="Current prompt generates verbose responses. Revised prompt improves conciseness.",
    risk=RiskLevel.LOW,
    target_paths=("prompts/summarization.txt",),
    payload={
        "patch": """
--- a/prompts/summarization.txt
+++ b/prompts/summarization.txt
@@ -1,3 +1,2 @@
-You are a helpful assistant. Provide detailed summaries.
+You are a helpful assistant. Provide concise 2-3 sentence summaries.
""",
        "format": "unified",
    },
)
```

### Example 3: Infrastructure Change

```python
ChangeProposal(
    proposal_id="prop_003",
    kind=ProposalKind.CONFIG_EDIT,
    title="Enable CDN for static assets",
    description="Serving static assets from origin increases latency. CDN will improve load times.",
    risk=RiskLevel.MEDIUM,
    target_paths=("config/infrastructure.yaml",),
    payload={
        "cdn": {
            "enabled": True,
            "provider": "cloudflare",
            "zone": "example.com",
            "cache_ttl_seconds": 86400,
        },
    },
)
```

---

## API Reference

### Creating Proposals

```python
from uuid import uuid4
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

proposal = ChangeProposal(
    proposal_id=str(uuid4()),
    kind=ProposalKind.CONFIG_EDIT,
    title="Your title",
    description="Your description",
    risk=RiskLevel.LOW,
    target_paths=("target/path",),
    payload={"key": "value"},
)
```

### Proposal Helper Functions

```python
from autoflow.propose.proposals import create_retry_proposal

proposal = create_retry_proposal(
    workflow_id="my_workflow",
    step_name="api_call",
    current_max_retries=2,
    recommended_max_retries=5,
)
```

---

## See Also

- [Decision Graph API](decision_graph.md) - How proposals are generated
- [Evaluation API](evaluation.md) - How proposals are validated
- [Apply API](apply.md) - How proposals are applied
- [Examples](examples.md) - Complete proposal examples
