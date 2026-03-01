# Evaluation API

## Overview

Evaluation is the **gatekeeping mechanism** in AutoFlow. Before any proposal is applied, it must be evaluated to ensure it's safe and beneficial.

---

## Core Concepts

### EvaluationResult

```python
@dataclass(frozen=True)
class EvaluationResult:
    proposal_id: str
    passed: bool
    score: float
    metrics: Mapping[str, float]
    notes: str = ""
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | `str` | ID of the evaluated proposal |
| `passed` | `bool` | Whether the proposal passed evaluation |
| `score` | `float` | Normalized score (0.0 - 1.0, or any value for custom evaluators) |
| `metrics` | `Mapping[str, float]` | Detailed metrics from evaluation |
| `notes` | `str` | Additional notes or failure reasons |

---

## Evaluator Types

### 1. ShadowEvaluator

**Purpose:** Dry-run evaluation that always passes.

```python
from autoflow.evaluate.shadow import ShadowEvaluator

evaluator = ShadowEvaluator()
result = evaluator.evaluate(proposal)

# result.passed == True
# result.score == 1.0
```

**Use Cases:**
- Initial testing and development
- Policies that handle all safety checks
- Logging proposals without blocking

**Characteristics:**
- ✅ Always passes
- ✅ Zero configuration
- ✅ Fast (no simulation)
- ❌ No actual validation

---

### 2. ReplayEvaluator

**Purpose:** Deterministic offline evaluation on historical data.

```python
from autoflow.evaluate.replay import (
    ReplayEvaluator,
    ReplayDataset,
    ReplayGates,
)

# Define your dataset
dataset = ReplayDataset(runs=[
    {"input": "...", "output": "...", "latency_ms": 1200, "success": True},
    {"input": "...", "output": "...", "latency_ms": 1500, "success": True},
    # ... more historical runs
])

# Define gates (pass/fail criteria)
gates = ReplayGates(
    max_regressions={
        "p95_latency_ms": 100.0,  # Latency can increase by at most 100ms
    },
    min_improvements={
        "success_rate": 0.01,  # Success rate must improve by at least 1%
    },
)

# Define baseline computation
def compute_baseline(dataset: ReplayDataset) -> dict[str, float]:
    latencies = [r["latency_ms"] for r in dataset.runs]
    successes = sum(1 for r in dataset.runs if r["success"])

    return {
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)],
        "success_rate": successes / len(dataset.runs),
    }

# Define candidate simulation
def simulate_candidate(dataset: ReplayDataset, proposal: ChangeProposal) -> dict[str, float]:
    # Apply proposal changes to simulate outcome
    new_timeout = proposal.payload["value"]  # e.g., timeout increase

    simulated_latencies = []
    successes = 0

    for run in dataset.runs:
        # Simulate with new timeout
        if run["latency_ms"] < new_timeout:
            simulated_latencies.append(run["latency_ms"])
            successes += 1
        else:
            # Would timeout with old config, succeed with new
            simulated_latencies.append(new_timeout * 0.9)
            successes += 1

    return {
        "p95_latency_ms": sorted(simulated_latencies)[int(len(simulated_latencies) * 0.95)],
        "success_rate": successes / len(dataset.runs),
    }

# Create evaluator
evaluator = ReplayEvaluator(
    dataset=dataset,
    compute_baseline=compute_baseline,
    simulate_candidate=simulate_candidate,
    gates=gates,
)

# Evaluate
result = evaluator.evaluate(proposal)

print(result.passed)  # True/False
print(result.score)   # Sum of improvements - regressions
print(result.notes)   # "PASS" or "FAIL: ..."
print(result.metrics) # {"baseline.p95_latency_ms": ..., "candidate.p95_latency_ms": ...}
```

**ReplayGates**

Defines pass/fail criteria for evaluation:

```python
@dataclass(frozen=True)
class ReplayGates:
    max_regressions: Mapping[str, float]  # Metrics that may not increase beyond delta
    min_improvements: Mapping[str, float]  # Metrics that must improve by at least delta
```

**Examples:**

```python
# Strict gate: No regressions, require improvement
gates = ReplayGates(
    max_regressions={"p95_latency_ms": 0.0},  # No latency increase allowed
    min_improvements={"success_rate": 0.05},   # Must improve by 5%
)

# Balanced gate: Allow small regression, require small improvement
gates = ReplayGates(
    max_regressions={"p95_latency_ms": 50.0},  # Allow +50ms
    min_improvements={"success_rate": 0.01},    # Must improve by 1%
)

# Permissive gate: Only check for catastrophic regression
gates = ReplayGates(
    max_regressions={"p95_latency_ms": 500.0},  # Allow +500ms
    min_improvements={},                         # No required improvements
)
```

**ReplayDataset**

Generic container for historical data:

```python
@dataclass(frozen=True)
class ReplayDataset:
    runs: Sequence[Mapping[str, object]]
```

**Examples:**

```python
# Workflow dataset
dataset = ReplayDataset(runs=[
    {
        "workflow_id": "etl_pipeline",
        "run_id": "run_001",
        "steps": [
            {"step_name": "extract", "latency_ms": 500, "status": "success"},
            {"step_name": "transform", "latency_ms": 1200, "status": "success"},
            {"step_name": "load", "latency_ms": 800, "status": "success"},
        ],
        "total_latency_ms": 2500,
        "success": True,
    },
    # ... more runs
])

# API dataset
dataset = ReplayDataset(runs=[
    {
        "endpoint": "/api/v1/process",
        "request": {...},
        "response": {...},
        "status_code": 200,
        "latency_ms": 350,
        "tokens_used": 1500,
    },
    # ... more runs
])
```

**Use Cases:**
- Validating config changes on historical data
- A/B testing offline before deployment
- Regression testing for critical systems
- Quality gates for production changes

**Characteristics:**
- ✅ Deterministic (same input = same result)
- ✅ Uses real historical data
- ✅ Configurable gates
- ❌ Requires dataset and simulation logic
- ❌ Only validates on historical data (may not predict future)

---

### 3. CompositeEvaluator

**Purpose:** Combine multiple evaluators with AND logic.

```python
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.evaluate.replay import ReplayEvaluator, ReplayGates

evaluator = CompositeEvaluator(evaluators=[
    ShadowEvaluator(),
    ReplayEvaluator(
        dataset=dataset,
        compute_baseline=compute_baseline,
        simulate_candidate=simulate_candidate,
        gates=ReplayGates(max_regressions={"latency_ms": 100}),
    ),
])

result = evaluator.evaluate(proposal)

# All evaluators must pass
# result.passed == True only if all evaluators pass
# result.score == average of all evaluator scores
```

**Scoring:**

```python
score = sum(evaluator.score for evaluator in evaluators) / len(evaluators)
```

**Use Cases:**
- Multiple validation criteria (performance + correctness)
- Redundant safety checks
- Combining fast pre-check with thorough validation

**Characteristics:**
- ✅ Flexible composition
- ✅ All evaluators must pass (AND logic)
- ✅ Averages scores
- ❌ No OR/NOT logic (use custom evaluator)

---

## Creating Custom Evaluators

### Pattern 1: Threshold-Based Evaluator

```python
from autoflow.types import ChangeProposal, EvaluationResult

class ThresholdEvaluator:
    """Passes if proposal risk is below threshold."""

    def __init__(self, max_risk: RiskLevel):
        self.max_risk = max_risk

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}

        if risk_order[proposal.risk] <= risk_order[self.max_risk]:
            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=True,
                score=1.0,
                metrics={"risk_level": risk_order[proposal.risk]},
                notes=f"Risk {proposal.risk} is within threshold",
            )
        else:
            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=False,
                score=0.0,
                metrics={"risk_level": risk_order[proposal.risk]},
                notes=f"Risk {proposal.risk} exceeds threshold {self.max_risk}",
            )
```

### Pattern 2: External Service Evaluator

```python
import requests

class ExternalAPIEvaluator:
    """Delegates evaluation to external service."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        response = requests.post(
            f"{self.api_url}/evaluate",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "proposal_id": proposal.proposal_id,
                "kind": proposal.kind,
                "title": proposal.title,
                "payload": proposal.payload,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=data["passed"],
            score=data.get("score", 1.0),
            metrics=data.get("metrics", {}),
            notes=data.get("notes", ""),
        )
```

### Pattern 3: Semantic Diff Evaluator

```python
class SemanticDiffEvaluator:
    """Checks if proposal changes are semantically safe."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        if proposal.kind == ProposalKind.TEXT_PATCH:
            # Ask LLM if patch is safe
            prompt = f"""
            Analyze this code patch for safety:

            {proposal.payload.get('patch', '')}

            Description: {proposal.description}

            Is this change safe to apply? Consider:
            1. Does it introduce bugs?
            2. Does it break existing functionality?
            3. Does it have security implications?

            Respond with JSON: {{"safe": true/false, "reason": "..."}}
            """

            response = self.llm.complete(prompt)
            result = json.loads(response)

            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=result["safe"],
                score=1.0 if result["safe"] else 0.0,
                metrics={},
                notes=result["reason"],
            )
        else:
            # Config edits are safe by default
            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=True,
                score=1.0,
                metrics={},
                notes="Config edit - no semantic analysis",
            )
```

### Pattern 4: Time-Window Evaluator

```python
from datetime import datetime, timedelta

class TimeWindowEvaluator:
    """Only passes during allowed time windows."""

    def __init__(self, allowed_hours: tuple[int, int]):
        """Allowed hours in UTC (e.g., (9, 17) for 9am-5pm UTC)."""
        self.allowed_start = allowed_hours[0]
        self.allowed_end = allowed_hours[1]

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        now = datetime.utcnow()
        current_hour = now.hour

        is_allowed = self.allowed_start <= current_hour < self.allowed_end

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=is_allowed,
            score=1.0 if is_allowed else 0.0,
            metrics={"current_hour_utc": current_hour},
            notes=(
                f"Current hour {current_hour} is within allowed window "
                f"{self.allowed_start}-{self.allowed_end} UTC"
                if is_allowed
                else f"Current hour {current_hour} is outside allowed window"
            ),
        )
```

---

## Evaluator Best Practices

### DO ✅

**1. Use ShadowEvaluator for Development**

```python
# Good for quick iteration
evaluator = ShadowEvaluator()
```

**2. Use ReplayEvaluator for Production**

```python
# Validate on historical data
evaluator = ReplayEvaluator(
    dataset=production_dataset,
    compute_baseline=compute_baseline,
    simulate_candidate=simulate_candidate,
    gates=strict_gates,
)
```

**3. Combine Evaluators for Defense in Depth**

```python
evaluator = CompositeEvaluator(evaluators=[
    ShadowEvaluator(),                    # Always passes
    ReplayEvaluator(...),                 # Historical validation
    ThresholdEvaluator(max_risk=RiskLevel.LOW),  # Risk check
])
```

**4. Set Appropriate Gates**

```python
# Match gates to business requirements
gates = ReplayGates(
    max_regressions={
        "latency_p95_ms": 100.0,   # User-facing latency: strict
        "cost_per_request": 0.01,  # Cost: allow small increase
    },
    min_improvements={
        "success_rate": 0.02,      # Reliability: must improve
    },
)
```

### DON'T ❌

**1. Don't Skip Evaluation in Production**

```python
# Avoid
if result.passed:
    applier.apply(proposal)  # Always check!
```

**2. Don't Use Loose Gates for Critical Systems**

```python
# Avoid
gates = ReplayGates(
    max_regressions={"latency_ms": 100000},  # Too permissive
)

# Good
gates = ReplayGates(
    max_regressions={"latency_ms": 100},  # Strict
)
```

**3. Don't Ignore Evaluation Notes**

```python
# Avoid
if result.passed:
    applier.apply(proposal)  # What does result.notes say?

# Good
if result.passed:
    if "concern" in result.notes.lower():
        log_warning(result.notes)
        send_alert(result.notes)
    applier.apply(proposal)
```

**4. Don't Evaluate Without Data**

```python
# Avoid - empty dataset
evaluator = ReplayEvaluator(
    dataset=ReplayDataset(runs=[]),
    ...
)

# Good - meaningful dataset
evaluator = ReplayEvaluator(
    dataset=load_production_data(days=30),
    ...
)
```

---

## Evaluation Patterns

### Pattern 1: Staged Evaluation

```python
# Fast pre-check, slow thorough check
class StagedEvaluator:
    def __init__(self):
        self.fast_check = ThresholdEvaluator(max_risk=RiskLevel.HIGH)
        self.thorough_check = ReplayEvaluator(...)

    def evaluate(self, proposal):
        # Fast check
        fast_result = self.fast_check.evaluate(proposal)
        if not fast_result.passed:
            return fast_result  # Fail fast

        # Thorough check
        return self.thorough_check.evaluate(proposal)
```

### Pattern 2: Conditional Evaluation

```python
class ConditionalEvaluator:
    """Different evaluators for different proposal types."""

    def __init__(self):
        self.config_evaluator = ReplayEvaluator(...)
        self.code_evaluator = SemanticDiffEvaluator(...)

    def evaluate(self, proposal):
        if proposal.kind == ProposalKind.CONFIG_EDIT:
            return self.config_evaluator.evaluate(proposal)
        elif proposal.kind == ProposalKind.TEXT_PATCH:
            return self.code_evaluator.evaluate(proposal)
        else:
            return EvaluationResult(
                proposal_id=proposal.proposal_id,
                passed=False,
                score=0.0,
                notes=f"Unknown proposal kind: {proposal.kind}",
            )
```

### Pattern 3: Ensemble Evaluation

```python
class EnsembleEvaluator:
    """Passes if N evaluators pass (not all)."""

    def __init__(self, evaluators: list, min_passing: int):
        self.evaluators = evaluators
        self.min_passing = min_passing

    def evaluate(self, proposal):
        results = [e.evaluate(proposal) for e in self.evaluators]
        passed_count = sum(1 for r in results if r.passed)

        passed = passed_count >= self.min_passing
        score = passed_count / len(self.evaluators)

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            score=score,
            metrics={"passing_count": passed_count, "total_count": len(self.evaluators)},
            notes=f"{passed_count}/{len(self.evaluators)} evaluators passed",
        )
```

---

## API Reference

### ShadowEvaluator

```python
class ShadowEvaluator:
    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        """
        Always-pass evaluator for development/testing.

        Returns:
            EvaluationResult with passed=True, score=1.0
        """
```

### ReplayEvaluator

```python
@dataclass(frozen=True)
class ReplayEvaluator:
    dataset: ReplayDataset
    compute_baseline: ComputeBaselineFn
    simulate_candidate: SimulateCandidateFn
    gates: ReplayGates

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        """
        Evaluate proposal on historical dataset.

        Args:
            proposal: Proposal to evaluate

        Returns:
            EvaluationResult with metrics and pass/fail based on gates

        Raises:
            EvaluationError: If proposal kind is not supported
        """
```

**Types:**

```python
from typing import Callable, Mapping, Sequence

ReplayDataset = namedtuple("ReplayDataset", ["runs"])
ComputeBaselineFn = Callable[[ReplayDataset], Mapping[str, float]]
SimulateCandidateFn = Callable[[ReplayDataset, ChangeProposal], Mapping[str, float]]

@dataclass(frozen=True)
class ReplayGates:
    max_regressions: Mapping[str, float]  # Metric may not increase by more than this
    min_improvements: Mapping[str, float]  # Metric must improve by at least this
```

### CompositeEvaluator

```python
class CompositeEvaluator:
    def __init__(self, evaluators: Sequence[object]) -> None:
        """
        Initialize with a list of evaluators.

        All evaluators must implement evaluate(proposal) -> EvaluationResult.
        """

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        """
        Run all evaluators and combine results.

        Returns:
            EvaluationResult where:
            - passed == True only if ALL evaluators pass
            - score == average of all evaluator scores
        """
```

---

## See Also

- [Proposals API](proposals.md) - Proposal structure and types
- [Apply API](apply.md) - How to apply evaluated proposals
- [Decision Graph API](decision_graph.md) - How proposals are generated
- [Examples](examples.md) - Complete evaluation examples
