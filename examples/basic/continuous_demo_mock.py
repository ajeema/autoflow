#!/usr/bin/env python3
"""
AutoFlow Continuous Learning Demo (Mock Version)

This demo demonstrates continuous improvement without requiring OpenAI API calls.
It simulates a QA system with realistic quality patterns.

Run this multiple times to see the system improve:
    python3 continuous_demo_mock.py     # Run 1
    python3 continuous_demo_mock.py     # Run 2 (better!)
    python3 continuous_demo_mock.py     # Run 3 (even better!)
"""

import json
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent / "src"))

# AutoFlow imports
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import GraphNode, ProposalKind, RiskLevel, ChangeProposal

from autoflow_ai.schemas import AIRun, ModelCall, RunOutcome
from autoflow_ai.dataset import AIDataset
from autoflow_ai.metrics import compute_metrics


# =============================================================================
# Persistent State Management
# =============================================================================

WORKSPACE = Path(".autoflow_workspace")
DB_PATH = WORKSPACE / "continuous_learning.db"
CONFIG_PATH = WORKSPACE / "prompts.json"
HISTORY_PATH = WORKSPACE / "improvement_history.jsonl"


@dataclass
class PromptConfig:
    """Configuration for the QA prompt (persisted)."""
    system_prompt: str
    temperature: float
    version: int = 1
    last_improved: str = ""
    features: list[str] = field(default_factory=list)  # Track added features


def load_config() -> PromptConfig:
    """Load the current prompt config."""
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        return PromptConfig(**data)

    # Default initial config
    return PromptConfig(
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        version=1,
        last_improved=datetime.now(timezone.utc).isoformat(),
        features=["basic"],
    )


def save_config(config: PromptConfig) -> None:
    """Save the current prompt config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({
        "system_prompt": config.system_prompt,
        "temperature": config.temperature,
        "version": config.version,
        "last_improved": config.last_improved,
        "features": config.features,
    }, indent=2))


def record_improvement(
    old_version: int,
    new_version: int,
    proposal_title: str,
    features: list[str],
    quality_before: float,
    quality_after: float,
) -> None:
    """Record an improvement in the history."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "old_version": old_version,
        "new_version": new_version,
        "proposal_title": proposal_title,
        "features": features,
        "quality_before": quality_before,
        "quality_after": quality_after,
    }

    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def get_improvement_history() -> list[dict]:
    """Load improvement history."""
    if not HISTORY_PATH.exists():
        return []

    history = []
    with HISTORY_PATH.open("r") as f:
        for line in f:
            if line.strip():
                history.append(json.loads(line))
    return history


# =============================================================================
# Mock QA System (Simulates OpenAI)
# =============================================================================

QUESTION_POOL = [
    "What is Python?",
    "What is a variable?",
    "What is a function?",
    "Explain lists in Python.",
    "How do I write a loop?",
    "What is a dictionary?",
    "Explain list comprehensions.",
    "What is a decorator?",
    "How do I handle errors?",
    "What is a generator?",
    "Explain async/await.",
    "What is type hinting?",
    "How do I read files?",
    "What are classes?",
    "Explain inheritance.",
]


class MockQAClient:
    """
    Mock QA client that simulates realistic quality patterns.

    The quality of responses improves based on prompt features:
    - basic: ~50% quality
    - basic + structured: ~65% quality
    - basic + structured + examples: ~80% quality
    - basic + structured + examples + confident: ~90% quality
    """

    def __init__(self, config: PromptConfig):
        self.config = config

    def answer_question(self, question: str) -> tuple[str, dict[str, Any]]:
        """Simulate answering a question."""

        # Calculate base quality from features
        base_quality = 0.5  # 50% for basic prompt

        if "structured" in self.config.features:
            base_quality += 0.15  # +15%
        if "examples" in self.config.features:
            base_quality += 0.15  # +15%
        if "confident" in self.config.features:
            base_quality += 0.10  # +10%
        if "comprehensive" in self.config.features:
            base_quality += 0.05  # +5%

        # Add some randomness (±10%)
        quality = max(0.0, min(1.0, base_quality + random.uniform(-0.10, 0.10)))

        # Simulate issues based on quality
        issues = []
        if quality < 0.6:
            issues.append("too_short")
            if random.random() > 0.5:
                issues.append("unstructured")
        elif quality < 0.75:
            if random.random() > 0.5:
                issues.append("missing_example")
            if random.random() > 0.7:
                issues.append("too_much_hedging")
        elif quality < 0.85:
            if random.random() > 0.6:
                issues.append("could_be_better")
        else:
            # High quality - maybe minor issues
            if random.random() > 0.9:
                issues.append("minor_clarification")

        # Simulate latency (better prompts = slightly slower)
        base_latency = 500 + (len(self.config.features) * 100)
        latency_ms = base_latency + random.uniform(-100, 200)

        # Simulate cost
        cost_usd = 0.001 + (len(self.config.features) * 0.0003)

        # Generate mock answer
        answer = self._generate_answer(question, quality)

        return answer, {
            "success": True,
            "quality_score": quality,
            "issues": issues,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "feature_count": len(self.config.features),
        }

    def _generate_answer(self, question: str, quality: float) -> str:
        """Generate a mock answer based on quality level."""
        if quality < 0.5:
            return f"{question} is a concept in programming."
        elif quality < 0.7:
            return f"{question} refers to an important programming concept. It is used frequently in Python development."
        elif quality < 0.85:
            return f"""## {question}

This is an important concept in Python. Here's what you need to know:

Key aspects:
- It's commonly used in Python programs
- Understanding this will help you write better code

Example:
```python
# Basic usage
example = "demo"
print(example)
```
"""
        else:
            return f"""## {question}

**Summary**: {question} is a fundamental concept that every Python developer should understand.

## Explanation

This concept is essential for writing effective Python code. It allows you to:

1. Organize your code better
2. Improve readability
3. Write more maintainable programs

## Practical Examples

Here's a concrete example:

```python
# Real-world usage
def process_data(items):
    result = []
    for item in items:
        processed = item.upper()
        result.append(processed)
    return result

# Usage
data = ["hello", "world"]
output = process_data(data)
print(output)  # ['HELLO', 'WORLD']
```

This demonstrates the key principles in action.
"""


# =============================================================================
# AutoFlow Rules
# =============================================================================

class ContinuousImprovementRule:
    """Analyzes all historical data and proposes targeted improvements."""

    def __init__(self, workflow_id: str, quality_threshold: float = 0.85):
        self.workflow_id = workflow_id
        self.quality_threshold = quality_threshold

    def propose(self, nodes: list[GraphNode]) -> list[dict]:
        """Analyze all historical events and propose improvements."""
        events = [
            n for n in nodes
            if n.properties.get("workflow_id") == self.workflow_id
            and n.properties.get("name") == "qa_run"
        ]

        if len(events) < 3:
            return []

        # Calculate overall metrics
        qualities = [e.properties.get("quality_score", 1.0) for e in events]
        avg_quality = sum(qualities) / len(qualities)

        # If quality is good enough, no improvement needed
        if avg_quality >= self.quality_threshold:
            return []

        # Analyze common issues across ALL historical runs
        all_issues = []
        for e in events:
            all_issues.extend(e.properties.get("issues", []))

        from collections import Counter
        issue_counts = Counter(all_issues)

        # Get current config to check what features we have
        config = load_config()
        current_features = set(config.features)

        print(f"\n    Historical analysis ({len(events)} runs):")
        print(f"      Average quality: {avg_quality:.1%}")
        print(f"      Top issues: {issue_counts.most_common(3)}")
        print(f"      Current features: {current_features}")

        # Propose based on most common issue and missing features
        most_common = issue_counts.most_common(1)[0][0] if issue_counts else None

        if most_common == "too_short" and "comprehensive" not in current_features:
            return [self._propose_comprehensive_prompt()]
        elif most_common == "unstructured" and "structured" not in current_features:
            return [self._propose_structured_prompt()]
        elif most_common in ["missing_example", "missing_code_example"] and "examples" not in current_features:
            return [self._propose_examples_prompt()]
        elif most_common == "too_much_hedging" and "confident" not in current_features:
            return [self._propose_confident_prompt()]
        else:
            # Generic improvement
            return [self._propose_generic_improvement()]

    def _propose_comprehensive_prompt(self):
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Add comprehensive response requirement",
            description="Historical answers are too short. Require more detailed, comprehensive responses.",
            risk=RiskLevel.LOW,
            target_paths=(str(CONFIG_PATH),),
            payload={
                "system_prompt": "You are a helpful assistant. Provide comprehensive, detailed answers.",
                "temperature": 0.7,
                "add_feature": "comprehensive",
            },
        )

    def _propose_structured_prompt(self):
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Add structured response format",
            description="Historical answers lack structure. Enforcing structured format with sections.",
            risk=RiskLevel.LOW,
            target_paths=(str(CONFIG_PATH),),
            payload={
                "system_prompt": "You are a helpful assistant. Structure answers with: Summary, Explanation, Examples.",
                "temperature": 0.6,
                "add_feature": "structured",
            },
        )

    def _propose_examples_prompt(self):
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Require code examples",
            description="Historical answers lack examples. Making code examples mandatory.",
            risk=RiskLevel.LOW,
            target_paths=(str(CONFIG_PATH),),
            payload={
                "system_prompt": "You are a helpful assistant. Always include practical code examples in answers.",
                "temperature": 0.5,
                "add_feature": "examples",
            },
        )

    def _propose_confident_prompt(self):
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Use more confident language",
            description="Historical answers use too much hedging. Encouraging direct, confident language.",
            risk=RiskLevel.LOW,
            target_paths=(str(CONFIG_PATH),),
            payload={
                "system_prompt": "You are a helpful assistant. Be direct and confident. Avoid uncertain language.",
                "temperature": 0.5,
                "add_feature": "confident",
            },
        )

    def _propose_generic_improvement(self):
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Enhance prompt quality",
            description="Making general prompt improvements based on historical performance.",
            risk=RiskLevel.LOW,
            target_paths=(str(CONFIG_PATH),),
            payload={
                "system_prompt": "You are an expert assistant. Provide clear, accurate, well-structured answers.",
                "temperature": 0.5,
                "add_feature": "enhanced",
            },
        )


# =============================================================================
# Custom Backend
# =============================================================================

class ConfigApplyBackend:
    """Backend that applies changes to the prompt config file."""

    def __init__(self):
        self.applied_count = 0

    def apply(self, proposal: ChangeProposal) -> dict:
        """Apply a proposal to the config."""
        payload = proposal.payload

        # Load current config
        config = load_config()

        # Update
        old_version = config.version
        config.version += 1
        config.last_improved = datetime.now(timezone.utc).isoformat()

        if "system_prompt" in payload:
            config.system_prompt = payload["system_prompt"]
        if "temperature" in payload:
            config.temperature = payload["temperature"]

        # Add feature
        new_feature = payload.get("add_feature")
        if new_feature and new_feature not in config.features:
            config.features.append(new_feature)

        # Save
        save_config(config)

        self.applied_count += 1

        return {
            "reference": f"v{old_version} -> v{config.version}",
            "old_version": old_version,
            "new_version": config.version,
            "title": proposal.title,
            "features": config.features.copy(),
        }


# =============================================================================
# Main Demo
# =============================================================================

def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    print(f"\n--- {title} ---")


def run_continuous_demo() -> None:
    """Run the continuous learning demo."""

    print_section("AutoFlow Continuous Learning Demo (Mock)")

    # Show improvement history
    history = get_improvement_history()
    print(f"Run number: {len(history) + 1}")

    if history:
        print("\n📜 Previous improvements:")
        for h in history[-5:]:
            quality_delta = (h['quality_after'] - h['quality_before']) * 100
            print(f"  v{h['old_version']} → v{h['new_version']}: {h['proposal_title']}")
            print(f"    Features: {h['features']}")
            print(f"    Quality: {h['quality_before']:.1%} → {h['quality_after']:.1%} (+{quality_delta:.1f}%)")

    # Load current config
    config = load_config()

    print_subsection("Current Configuration")
    print(f"  📌 Version: {config.version}")
    print(f"  🔧 Features: {config.features}")
    print(f"  📝 System prompt: {config.system_prompt[:60]}...")
    print(f"  🌡️  Temperature: {config.temperature}")

    # Initialize AutoFlow with persistent storage
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    store = SQLiteGraphStore(db_path=str(DB_PATH))

    engine = AutoImproveEngine(
        store=store,
        graph_builder=ContextGraphBuilder(),
        decision_graph=DecisionGraph(
            rules=[
                ContinuousImprovementRule(
                    workflow_id="qa_system",
                    quality_threshold=0.85,  # Aim for 85% quality
                )
            ]
        ),
        evaluator=ShadowEvaluator(),
        applier=ProposalApplier(
            policy=ApplyPolicy(
                allowed_paths_prefixes=(str(WORKSPACE),),
                max_risk=RiskLevel.LOW
            ),
            backend=ConfigApplyBackend(),
        ),
    )

    # Phase 1: Test current system
    print_subsection("Phase 1: Testing Current System")

    # Get random questions
    random.seed(len(history))  # Different questions each run
    questions = random.sample(QUESTION_POOL, min(5, len(QUESTION_POOL)))
    print(f"Testing {len(questions)} questions...")

    client = MockQAClient(config=config)
    current_runs = []
    current_events = []
    qualities = []

    for i, question in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {question[:40]}...", end=" ")

        answer, metrics = client.answer_question(question)
        quality = metrics["quality_score"]
        qualities.append(quality)

        print(f"✓ quality: {quality:.1%} {metrics['issues']}")

        # Track for AutoFlow
        current_events.append(make_event(
            source="qa_system",
            name="qa_run",
            attributes={
                "workflow_id": "qa_system",
                "version": config.version,
                "quality_score": quality,
                "issues": metrics["issues"],
                "latency_ms": metrics["latency_ms"],
                "cost_usd": metrics["cost_usd"],
                "features": config.features.copy(),
            },
        ))

        current_runs.append(AIRun(
            run_id=f"v{config.version}_{i}",
            workflow_id="qa_system",
            model_calls=[ModelCall(
                model="mock-gpt-4o-mini",
                latency_ms=metrics["latency_ms"],
                input_tokens=100,
                output_tokens=200,
            )],
            outcome=RunOutcome(
                success=True,
                quality_score=quality,
                cost_usd=metrics["cost_usd"],
            ),
        ))

    # Calculate current metrics
    avg_quality = sum(qualities) / len(qualities)

    print_subsection("Current Performance")
    print(f"  ✅ Success rate: 100%")
    print(f"  📊 Average quality: {avg_quality:.1%}")
    print(f"  🎯 Quality range: {min(qualities):.1%} - {max(qualities):.1%}")

    # Get historical context from all previous runs
    all_events = current_events.copy()

    # Phase 2: AutoFlow Analysis
    print_subsection("Phase 2: AutoFlow Analysis")

    # Ingest current events
    engine.ingest(current_events)

    # Propose improvements
    proposals = engine.decision_graph.run(
        list(store.query_nodes("event", limit=1000))
    )

    if not proposals:
        print("\n  ✨ System is performing well! No improvements needed.")
        print(f"  🎉 Quality threshold ({0.85:.0%}) already met!")
        return

    print(f"\n  Generated {len(proposals)} proposal(s):")
    for p in proposals[:1]:  # Just show first proposal
        print(f"    💡 Title: {p.title}")
        print(f"    📋 Description: {p.description}")
        print(f"    ⚠️  Risk: {p.risk}")

    # Phase 3: Evaluate and Apply
    print_subsection("Phase 3: Applying Improvements")

    # Apply first proposal
    proposal = proposals[0]
    result = engine.evaluator.evaluate(proposal)

    print(f"\n  Proposal: {proposal.title}")
    print(f"  Evaluation: {'✅ PASS' if result.passed else '❌ FAIL'}")

    if result.passed:
        applied = engine.applier.backend.apply(proposal)

        print(f"\n  ✅ Applied: {applied['reference']}")
        print(f"     New features: {applied['features']}")

        # Record improvement
        new_config = load_config()

        # Quick validation with new config
        print_subsection("Phase 4: Quick Validation")

        new_client = MockQAClient(config=new_config)
        validation_questions = random.sample(QUESTION_POOL, min(3, len(QUESTION_POOL)))
        validation_qualities = []

        print(f"Testing with {len(validation_questions)} new questions...")

        for i, question in enumerate(validation_questions, 1):
            print(f"  [{i}] {question[:40]}...", end=" ")
            answer, metrics = new_client.answer_question(question)
            quality = metrics["quality_score"]
            validation_qualities.append(quality)
            print(f"✓ quality: {quality:.1%}")

        new_avg_quality = sum(validation_qualities) / len(validation_qualities)

        print(f"\n  Validation metrics:")
        print(f"    Old quality: {avg_quality:.1%}")
        print(f"    New quality: {new_avg_quality:.1%}")

        improvement = new_avg_quality - avg_quality
        emoji = "📈" if improvement > 0 else "📉"
        print(f"    Improvement: {emoji} {improvement:+.1%}")

        # Record in history
        record_improvement(
            old_version=applied['old_version'],
            new_version=applied['new_version'],
            proposal_title=applied['title'],
            features=applied['features'],
            quality_before=avg_quality,
            quality_after=new_avg_quality,
        )

    print_section("Run Complete!")

    print("\n🔄 To continue improving, run this script again:")
    print("   python3 continuous_demo_mock.py")
    print("\n💡 Each run will:")
    print("   1. Remember all previous improvements")
    print("   2. Test the current system")
    print("   3. Analyze ALL historical data")
    print("   4. Propose targeted improvements")
    print("   5. Apply changes only if safe")
    print("\n🎯 Over time, the system will converge on optimal configuration!")


# Import DecisionGraph for type hints
from autoflow.decide.decision_graph import DecisionGraph


if __name__ == "__main__":
    run_continuous_demo()
