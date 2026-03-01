#!/usr/bin/env python3
"""
AutoFlow Continuous Learning Demo

This demo demonstrates how AutoFlow can continuously improve a system over time.
Each time you run this script, it:
1. Remembers previous improvements (via persistent database)
2. Tests the current system on new questions
3. Observes the outcomes
4. Proposes further improvements
5. Applies changes only if they pass safety gates

Over multiple runs, you'll see the system progressively improve!

Usage:
    Run this script multiple times to see continuous improvement:
    python3 continuous_demo.py     # Run 1
    python3 continuous_demo.py     # Run 2 (will be better)
    python3 continuous_demo.py     # Run 3 (even better)
    ...

Requirements:
    pip install openai "autoflow[ai]"
    export OPENAI_API_KEY=your_key_here
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent / "src"))

import openai

# AutoFlow imports
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import GraphNode, ProposalKind, RiskLevel

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
    max_tokens: int = 500
    model: str = "gpt-4o-mini"
    version: int = 1
    last_improved: str = ""


def load_config() -> PromptConfig:
    """Load the current prompt config."""
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        # Filter out unexpected fields (like 'features' from mock demo)
        valid_fields = {k: v for k, v in data.items()
                       if k in ['system_prompt', 'temperature', 'max_tokens', 'model', 'version', 'last_improved']}
        return PromptConfig(**valid_fields)

    # Default initial config
    return PromptConfig(
        system_prompt="You are a helpful assistant. Answer the question.",
        temperature=0.7,
        version=1,
        last_improved=datetime.now(timezone.utc).isoformat(),
    )


def save_config(config: PromptConfig) -> None:
    """Save the current prompt config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(vars(config), indent=2))


def record_improvement(
    old_version: int,
    new_version: int,
    proposal_title: str,
    metrics_before: dict,
    metrics_after: dict,
) -> None:
    """Record an improvement in the history."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "old_version": old_version,
        "new_version": new_version,
        "proposal_title": proposal_title,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
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
# Test Questions Pool (larger pool for continuous testing)
# =============================================================================

QUESTION_POOL = [
    # Basics
    "What is Python?",
    "What is a variable in programming?",
    "What is a function?",
    "What is a loop?",
    "What is a conditional statement?",

    # Python specifics
    "What is the difference between a list and a tuple?",
    "How do I create a dictionary in Python?",
    "What is a Python decorator?",
    "How do I handle exceptions in Python?",
    "What is __init__ used for?",

    # Intermediate
    "Explain list comprehensions in Python.",
    "What is a generator in Python?",
    "What is the GIL in Python?",
    "How does Python's garbage collection work?",
    "What are Python's magic methods?",

    # Advanced
    "Explain how to implement a context manager in Python.",
    "What is metaprogramming in Python?",
    "How do I use async/await in Python?",
    "What is type hinting in Python?",
    "Explain the difference between == and is in Python.",

    # Practical
    "How do I read a file in Python?",
    "How do I make an HTTP request in Python?",
    "What is the best way to parse JSON in Python?",
    "How do I write unit tests in Python?",
    "What virtual environment tool should I use for Python?",
]


def get_test_questions(count: int = 5) -> list[str]:
    """Get random test questions from the pool."""
    import random
    return random.sample(QUESTION_POOL, min(count, len(QUESTION_POOL)))


# =============================================================================
# OpenAI Client
# =============================================================================

class OpenAIQAClient:
    """Client for QA system using OpenAI."""

    def __init__(self, config: PromptConfig):
        self.config = config
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def answer_question(self, question: str) -> tuple[str, dict[str, Any]]:
        """Answer a question using the configured prompt."""
        start_time = time()

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            answer = response.choices[0].message.content or ""
            usage = response.usage
            latency_ms = (time() - start_time) * 1000
            cost_usd = (usage.prompt_tokens / 1_000_000) * 0.15 + (usage.completion_tokens / 1_000_000) * 0.60

            return answer, {
                "success": True,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_usd": cost_usd,
                "answer_length": len(answer),
            }

        except Exception as e:
            latency_ms = (time() - start_time) * 1000
            return "", {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
            }


def evaluate_answer_quality(question: str, answer: str) -> dict[str, Any]:
    """Evaluate answer quality."""
    if not answer:
        return {"quality_score": 0.0, "issues": ["empty_answer"]}

    issues = []
    score = 1.0

    # Length checks
    if len(answer) < 50:
        issues.append("too_short")
        score -= 0.3
    elif len(answer) > 2000:
        issues.append("too_long")
        score -= 0.1

    # Structure checks for technical questions
    if any(word in question.lower() for word in ["python", "code", "how", "what is"]):
        has_structure = any(marker in answer for marker in ["1.", "2.", "-", "*", "First", "However", "##"])
        if not has_structure:
            issues.append("unstructured")
            score -= 0.15

    # Code example check
    if any(word in question.lower() for word in ["code", "example", "how to", "implement"]):
        if "```" not in answer:
            issues.append("missing_code_example")
            score -= 0.2

    # Hedging check
    hedging = ["might", "could", "possibly", "perhaps", "may be"]
    if sum(1 for h in hedging if h in answer.lower()) > 2:
        issues.append("too_much_hedging")
        score -= 0.1

    return {
        "quality_score": max(0.0, score),
        "issues": issues,
    }


# =============================================================================
# AutoFlow Rules
# =============================================================================

class ContinuousImprovementRule:
    """Detects issues and proposes improvements based on all historical data."""

    def __init__(self, workflow_id: str, quality_threshold: float = 0.75):
        self.workflow_id = workflow_id
        self.quality_threshold = quality_threshold

    def propose(self, nodes: list[GraphNode]) -> list:
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

        print(f"\n    Historical analysis ({len(events)} runs):")
        print(f"      Average quality: {avg_quality:.1%}")
        print(f"      Top issues: {issue_counts.most_common(3)}")

        # Propose based on most common issue
        most_common = issue_counts.most_common(1)[0][0] if issue_counts else None

        if most_common == "too_short":
            return [self._propose_longer_prompt()]
        elif most_common == "unstructured":
            return [self._propose_structured_prompt()]
        elif most_common == "missing_code_example":
            return [self._propose_code_prompt()]
        elif most_common == "too_much_hedging":
            return [self._propose_direct_prompt()]
        else:
            return [self._propose_enhanced_prompt()]

    def _propose_longer_prompt(self):
        return {
            "proposal_id": str(uuid4()),
            "kind": ProposalKind.CONFIG_EDIT,
            "title": "Require more detailed responses",
            "description": "Historical answers are too short. Increasing minimum response length requirement.",
            "risk": RiskLevel.LOW,
            "target_paths": [str(CONFIG_PATH)],
            "payload": {
                "system_prompt": (
                    "You are an expert technical assistant. Provide comprehensive, detailed answers. "
                    "Each answer should be 3-5 paragraphs covering: explanation, key details, and examples. "
                    "Aim for 300-500 words minimum. Be thorough but concise."
                ),
                "temperature": 0.6,
            },
        }

    def _propose_structured_prompt(self):
        return {
            "proposal_id": str(uuid4()),
            "kind": ProposalKind.CONFIG_EDIT,
            "title": "Enforce structured response format",
            "description": "Historical answers lack structure. Adding structured format requirements.",
            "risk": RiskLevel.LOW,
            "target_paths": [str(CONFIG_PATH)],
            "payload": {
                "system_prompt": (
                    "You are a precise technical assistant. Structure every answer with:\n\n"
                    "## Summary\nA brief 1-2 sentence overview.\n\n"
                    "## Explanation\nDetailed explanation of the concept.\n\n"
                    "## Examples\nPractical code examples where applicable.\n\n"
                    "Use markdown formatting throughout."
                ),
                "temperature": 0.5,
            },
        }

    def _propose_code_prompt(self):
        return {
            "proposal_id": str(uuid4()),
            "kind": ProposalKind.CONFIG_EDIT,
            "title": "Require code examples for technical questions",
            "description": "Historical technical answers lack code examples. Making examples mandatory.",
            "risk": RiskLevel.LOW,
            "target_paths": [str(CONFIG_PATH)],
            "payload": {
                "system_prompt": (
                    "You are a practical coding expert. ALWAYS include runnable code examples "
                    "in your answers. Use ```python``` code blocks. Show concrete examples "
                    "that demonstrate the concept or solution. Examples are essential."
                ),
                "temperature": 0.4,
            },
        }

    def _propose_direct_prompt(self):
        return {
            "proposal_id": str(uuid4()),
            "kind": ProposalKind.CONFIG_EDIT,
            "title": "Use more direct, confident language",
            "description": "Historical answers use too much hedging. Encouraging direct responses.",
            "risk": RiskLevel.LOW,
            "target_paths": [str(CONFIG_PATH)],
            "payload": {
                "system_prompt": (
                    "You are a confident expert. Give direct, authoritative answers. "
                    "Avoid uncertain language like 'might', 'could', 'possibly'. "
                    "State facts clearly and confidently. If you're not sure, say so directly "
                    "rather than hedging."
                ),
                "temperature": 0.5,
            },
        }

    def _propose_enhanced_prompt(self):
        return {
            "proposal_id": str(uuid4()),
            "kind": ProposalKind.CONFIG_EDIT,
            "title": "Enhance prompt for better quality",
            "description": "Improving prompt based on historical performance data.",
            "risk": RiskLevel.LOW,
            "target_paths": [str(CONFIG_PATH)],
            "payload": {
                "system_prompt": (
                    "You are an expert technical assistant. Provide clear, accurate, well-structured answers. "
                    "Include examples when relevant. Be comprehensive but stay focused on the question. "
                    "Use markdown for formatting."
                ),
                "temperature": 0.5,
            },
        }


# =============================================================================
# Custom Filesystem Backend
# =============================================================================

class ConfigApplyBackend:
    """Backend that applies changes to the prompt config file."""

    def __init__(self):
        self.applied_count = 0

    def apply(self, proposal: dict) -> dict:
        """Apply a proposal to the config."""
        payload = proposal.get("payload", {})

        # Load current config
        config = load_config()

        # Update with new values
        old_version = config.version
        config.version += 1
        config.last_improved = datetime.now(timezone.utc).isoformat()

        if "system_prompt" in payload:
            config.system_prompt = payload["system_prompt"]
        if "temperature" in payload:
            config.temperature = payload["temperature"]

        # Save
        save_config(config)

        self.applied_count += 1

        return {
            "reference": f"v{old_version} -> v{config.version}",
            "old_version": old_version,
            "new_version": config.version,
            "title": proposal.get("title", ""),
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

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)

    print_section("AutoFlow Continuous Learning Demo")

    # Show improvement history
    history = get_improvement_history()
    print(f"Run number: {len(history) + 1}")

    if history:
        print("\nPrevious improvements:")
        for h in history[-5:]:  # Show last 5
            print(f"  v{h['old_version']} → v{h['new_version']}: {h['proposal_title']}")

    # Load current config
    config = load_config()

    print_subsection("Current Configuration")
    print(f"  Version: {config.version}")
    print(f"  Last improved: {config.last_improved or 'Never'}")
    print(f"  System prompt: {config.system_prompt[:80]}...")
    print(f"  Temperature: {config.temperature}")

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
                    quality_threshold=0.80,  # Aim for 80% quality
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

    questions = get_test_questions(count=5)
    print(f"Testing {len(questions)} questions...")

    client = OpenAIQAClient(config=config)
    current_runs = []
    current_events = []

    for i, question in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {question[:50]}...", end=" ")

        answer, metrics = client.answer_question(question)

        if metrics["success"]:
            quality = evaluate_answer_quality(question, answer)
            print(f"✓ quality: {quality['quality_score']:.1%}")

            # Track for AutoFlow
            current_events.append(make_event(
                source="qa_system",
                name="qa_run",
                attributes={
                    "workflow_id": "qa_system",
                    "version": config.version,
                    "quality_score": quality["quality_score"],
                    "issues": quality["issues"],
                    "latency_ms": metrics["latency_ms"],
                    "cost_usd": metrics["cost_usd"],
                },
            ))

            current_runs.append(AIRun(
                run_id=f"v{config.version}_{i}",
                workflow_id="qa_system",
                model_calls=[ModelCall(
                    model=config.model,
                    latency_ms=metrics["latency_ms"],
                    input_tokens=metrics["prompt_tokens"],
                    output_tokens=metrics["completion_tokens"],
                )],
                outcome=RunOutcome(
                    success=True,
                    quality_score=quality["quality_score"],
                    cost_usd=metrics["cost_usd"],
                ),
            ))

    # Calculate current metrics
    dataset = AIDataset(runs=tuple(current_runs))
    current_metrics = compute_metrics(dataset, workflow_id="qa_system")

    print_subsection("Current Performance")
    print(f"  Success rate: {current_metrics.success_rate:.1%}")
    print(f"  P95 latency: {current_metrics.p95_model_latency_ms:.0f}ms")
    print(f"  Avg cost: ${current_metrics.avg_cost_usd:.4f}")

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
        print("\n  ✓ System is performing well! No improvements needed.")
        print("  (Quality threshold already met)")
        return

    print(f"\n  Generated {len(proposals)} proposal(s):")
    for p in proposals[:1]:  # Just show first proposal
        print(f"    Title: {p['title']}")
        print(f"    Description: {p['description']}")
        print(f"    Risk: {p['risk']}")

    # Phase 3: Evaluate and Apply
    print_subsection("Phase 3: Applying Improvements")

    # Apply first proposal
    proposal = proposals[0]
    result = engine.evaluator.evaluate(proposal)

    print(f"\n  Proposal: {proposal['title']}")
    print(f"  Evaluation: {'PASS ✓' if result.passed else 'FAIL ✗'}")

    if result.passed:
        applied = engine.applier.backend.apply(proposal)

        print(f"\n  ✓ Applied: {applied['reference']}")
        print(f"    Old version: {applied['old_version']}")
        print(f"    New version: {applied['new_version']}")

        # Record improvement
        record_improvement(
            old_version=applied['old_version'],
            new_version=applied['new_version'],
            proposal_title=applied['title'],
            metrics_before=current_metrics.as_dict(),
            metrics_after={},  # Will be validated on next run
        )

        # Phase 4: Quick validation
        print_subsection("Phase 4: Quick Validation")

        new_config = load_config()
        new_client = OpenAIQAClient(config=new_config)

        validation_questions = get_test_questions(count=3)
        validation_runs = []

        print(f"Testing with {len(validation_questions)} new questions...")

        for i, question in enumerate(validation_questions, 1):
            print(f"  [{i}] {question[:50]}...", end=" ")

            answer, metrics = new_client.answer_question(question)

            if metrics["success"]:
                quality = evaluate_answer_quality(question, answer)
                print(f"✓ quality: {quality['quality_score']:.1%}")

                validation_runs.append(AIRun(
                    run_id=f"v{new_config.version}_val_{i}",
                    workflow_id="qa_system",
                    model_calls=[ModelCall(
                        model=new_config.model,
                        latency_ms=metrics["latency_ms"],
                        input_tokens=metrics["prompt_tokens"],
                        output_tokens=metrics["completion_tokens"],
                    )],
                    outcome=RunOutcome(
                        success=True,
                        quality_score=quality["quality_score"],
                        cost_usd=metrics["cost_usd"],
                    ),
                ))

        if validation_runs:
            new_metrics = compute_metrics(
                AIDataset(runs=tuple(validation_runs)),
                workflow_id="qa_system"
            )

            print(f"\n  Validation metrics:")
            print(f"    Success rate: {new_metrics.success_rate:.1%} (was {current_metrics.success_rate:.1%})")
            print(f"    P95 latency: {new_metrics.p95_model_latency_ms:.0f}ms (was {current_metrics.p95_model_latency_ms:.0f}ms)")
            print(f"    Avg cost: ${new_metrics.avg_cost_usd:.4f} (was ${current_metrics.avg_cost_usd:.4f})")

            improvement = new_metrics.success_rate - current_metrics.success_rate
            print(f"\n    Improvement: {improvement:+.1%}")

    print_section("Run Complete!")

    print("\nTo continue improving, run this script again:")
    print("  python3 continuous_demo.py")
    print("\nEach run will:")
    print("  1. Remember all previous improvements")
    print("  2. Test the current system")
    print("  3. Analyze all historical data")
    print("  4. Propose targeted improvements")
    print("  5. Apply changes only if safe")
    print("\nOver time, the system will converge on optimal configuration!")


if __name__ == "__main__":
    run_continuous_demo()
