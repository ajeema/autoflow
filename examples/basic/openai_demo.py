#!/usr/bin/env python3
"""
AutoFlow + OpenAI Demo: Prompt Optimization Workflow

This demo demonstrates a real AI workflow where:
1. We run a QA system using OpenAI
2. Track outcomes (success, quality, latency, cost)
3. AutoFlow observes and detects improvement opportunities
4. Proposes prompt/parameter changes
5. Validates via replay on historical data
6. Applies changes if gates pass

Requirements:
    pip install openai "autoflow[ai]"

Set environment variable:
    export OPENAI_API_KEY=your_key_here

Run:
    python openai_demo.py
"""

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent / "src"))

import openai
from openai.types.chat import ChatCompletion

# AutoFlow imports
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.apply.policy import ApplyPolicy
from autoflow.decide.decision_graph import DecisionGraph
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.evaluate.shadow import ShadowEvaluator
from autoflow.evaluate.replay import ReplayGates
from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.sqlite_store import SQLiteGraphStore
from autoflow.observe.events import make_event
from autoflow.types import ChangeProposal, GraphNode, ProposalKind, RiskLevel

# AutoFlow AI imports
from autoflow_ai.dataset import load_jsonl_dataset, AIDataset
from autoflow_ai.eval.replay_ai import AIReplayEvaluator
from autoflow_ai.schemas import AIRun, ModelCall, RunOutcome, ToolCall
from autoflow_ai.metrics import compute_metrics


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class PromptConfig:
    """Configuration for a prompt variant."""
    name: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 500
    model: str = "gpt-4o-mini"


# Initial prompt variants to test
PROMPT_VARIANTS = [
    PromptConfig(
        name="baseline",
        system_prompt="You are a helpful assistant. Answer the user's question concisely.",
        temperature=0.7,
    ),
    PromptConfig(
        name="detailed",
        system_prompt="You are an expert assistant. Provide detailed, accurate answers with examples.",
        temperature=0.5,
    ),
    PromptConfig(
        name="structured",
        system_prompt="""You are a precise assistant. Answer questions using this structure:
1. Direct answer (1-2 sentences)
2. Key details
3. Example (if applicable)

Be accurate and concise.""",
        temperature=0.3,
    ),
]

# Test questions for our QA system
TEST_QUESTIONS = [
    "What is Python and why is it popular?",
    "Explain the difference between a list and a tuple in Python.",
    "What is a decorator in Python?",
    "How do I handle exceptions in Python?",
    "What is the difference between == and is in Python?",
    "Explain list comprehensions in Python.",
    "What is a generator in Python?",
    "How do I read a file in Python?",
    "What is the purpose of __init__ in Python classes?",
    "Explain the Global Interpreter Lock (GIL) in Python.",
]


# =============================================================================
# OpenAI Client Wrapper
# =============================================================================

class OpenAIQAClient:
    """Client for QA system using OpenAI."""

    def __init__(self, config: PromptConfig):
        self.config = config
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def answer_question(self, question: str) -> tuple[str, dict[str, Any]]:
        """
        Answer a question using the configured prompt.

        Returns:
            (answer, metrics) tuple
        """
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

            # Extract metrics
            usage = response.usage
            latency_ms = (time() - start_time) * 1000
            cost_usd = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            metrics = {
                "success": True,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_usd": cost_usd,
                "answer_length": len(answer),
                "finish_reason": response.choices[0].finish_reason,
            }

            return answer, metrics

        except Exception as e:
            latency_ms = (time() - start_time) * 1000
            return "", {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms,
            }

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD for gpt-4o-mini."""
        # Pricing as of 2024: $0.15/M input, $0.60/M output
        input_cost = (prompt_tokens / 1_000_000) * 0.15
        output_cost = (completion_tokens / 1_000_000) * 0.60
        return input_cost + output_cost


# =============================================================================
# Quality Evaluation
# =============================================================================

def evaluate_answer_quality(question: str, answer: str) -> dict[str, Any]:
    """
    Evaluate answer quality using heuristics.

    In production, this could use:
    - LLM-as-judge
    - Human feedback
    - Automated tests
    """
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

    # Content checks
    answer_lower = answer.lower()

    # Check for code examples in technical questions
    if any(word in question.lower() for word in ["code", "example", "how", "python"]):
        if "```" not in answer and "`" not in answer:
            issues.append("missing_code_example")
            score -= 0.2

    # Check for structured response in complex questions
    if len(question.split()) > 10:
        has_structure = any(marker in answer for marker in ["1.", "2.", "3.", "-", "*", "First", "Second"])
        if not has_structure:
            issues.append("unstructured")
            score -= 0.1

    # Check for hedging (overuse of uncertain language)
    hedging_phrases = ["might be", "could be", "possibly", "perhaps", "it depends"]
    hedge_count = sum(1 for phrase in hedging_phrases if phrase in answer_lower)
    if hedge_count > 2:
        issues.append("too_much_hedging")
        score -= 0.15

    # Check for "I don't know" or similar
    refusal_phrases = ["i don't know", "i'm not sure", "cannot", "unable to"]
    if any(phrase in answer_lower for phrase in refusal_phrases):
        issues.append("refusal")
        score -= 0.4

    return {
        "quality_score": max(0.0, score),
        "issues": issues,
    }


# =============================================================================
# AutoFlow Rules
# =============================================================================

class LowQualityRule:
    """Detects low quality answers and proposes prompt improvements."""

    def __init__(self, workflow_id: str, quality_threshold: float = 0.6):
        self.workflow_id = workflow_id
        self.quality_threshold = quality_threshold

    def propose(self, nodes: list[GraphNode]) -> list[ChangeProposal]:
        """Analyze nodes and propose improvements."""
        # Filter events for this workflow
        events = [
            n for n in nodes
            if n.properties.get("workflow_id") == self.workflow_id
            and n.properties.get("name") == "qa_run"
        ]

        if len(events) < 3:
            return []

        # Calculate average quality
        qualities = [
            e.properties.get("quality_score", 1.0)
            for e in events
        ]

        avg_quality = sum(qualities) / len(qualities)

        if avg_quality >= self.quality_threshold:
            return []

        # Analyze common issues
        all_issues = []
        for e in events:
            all_issues.extend(e.properties.get("issues", []))

        from collections import Counter
        issue_counts = Counter(all_issues)
        most_common_issue = issue_counts.most_common(1)[0][0] if issue_counts else None

        # Propose based on issue type
        proposals = []

        if most_common_issue == "too_short":
            proposals.append(self._propose_longer_prompt())
        elif most_common_issue == "unstructured":
            proposals.append(self._propose_structured_prompt())
        elif most_common_issue == "missing_code_example":
            proposals.append(self._propose_code_focused_prompt())
        elif most_common_issue == "too_much_hedging":
            proposals.append(self._propose_confident_prompt())
        else:
            proposals.append(self._propose_generic_improvement(avg_quality))

        return proposals

    def _propose_longer_prompt(self) -> ChangeProposal:
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Increase response length requirement",
            description=f"Answers are too short. Proposing prompt change to encourage more detailed responses.",
            risk=RiskLevel.LOW,
            target_paths=("config/prompts.yaml",),
            payload={
                "op": "set",
                "path": "prompts.qa.system_prompt",
                "value": (
                    "You are an expert assistant. Provide comprehensive answers. "
                    "Each answer should be 3-5 paragraphs with examples. "
                    "Aim for 300-500 words minimum."
                ),
            },
        )

    def _propose_structured_prompt(self) -> ChangeProposal:
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Add structured response format",
            description="Answers lack structure. Proposing prompt change to enforce structured output.",
            risk=RiskLevel.LOW,
            target_paths=("config/prompts.yaml",),
            payload={
                "op": "set",
                "path": "prompts.qa.system_prompt",
                "value": (
                    "You are a precise assistant. Always structure your answers as:\n"
                    "## Summary\n"
                    "## Key Points\n"
                    "## Example\n"
                    "## Additional Context\n\n"
                    "Use markdown formatting throughout."
                ),
            },
        )

    def _propose_code_focused_prompt(self) -> ChangeProposal:
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Add code example requirement",
            description="Technical answers missing code examples. Proposing prompt to require code snippets.",
            risk=RiskLevel.LOW,
            target_paths=("config/prompts.yaml",),
            payload={
                "op": "set",
                "path": "prompts.qa.system_prompt",
                "value": (
                    "You are a coding expert. Always include code examples in your answers. "
                    "Use ```python code blocks for Python code. "
                    "Provide runnable examples that demonstrate the concept."
                ),
            },
        )

    def _propose_confident_prompt(self) -> ChangeProposal:
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Reduce hedging language",
            description="Answers use too much uncertain language. Proposing prompt to be more direct.",
            risk=RiskLevel.LOW,
            target_paths=("config/prompts.yaml",),
            payload={
                "op": "set",
                "path": "prompts.qa.system_prompt",
                "value": (
                    "You are a confident expert. Give direct, clear answers. "
                    "Avoid phrases like 'might be', 'could be', 'possibly'. "
                    "State facts clearly and confidently."
                ),
            },
        )

    def _propose_generic_improvement(self, avg_quality: float) -> ChangeProposal:
        return ChangeProposal(
            proposal_id=str(uuid4()),
            kind=ProposalKind.CONFIG_EDIT,
            title="Improve prompt quality",
            description=f"Average quality score {avg_quality:.1%} is below threshold. Proposing enhanced prompt.",
            risk=RiskLevel.LOW,
            target_paths=("config/prompts.yaml",),
            payload={
                "op": "set",
                "path": "prompts.qa.system_prompt",
                "value": (
                    "You are an expert technical assistant. Provide clear, accurate, "
                    "well-structured answers with examples when relevant. "
                    "Be thorough but concise."
                ),
            },
        )


# =============================================================================
# Simulation Functions
# =============================================================================

def simulate_candidate_metrics(
    dataset: AIDataset,
    proposal: ChangeProposal,
    workflow_id: str,
) -> dict[str, float]:
    """
    Simulate the effect of a proposal on historical data.

    This is a simplified simulation - in production you might:
    - Actually re-run the candidate prompt on historical inputs
    - Use a smaller model to approximate
    - Use cached responses
    """
    baseline = compute_metrics(dataset, workflow_id=workflow_id)
    baseline_dict = baseline.as_dict()

    # Extract proposed prompt
    new_prompt = proposal.payload.get("value", "")
    prompt_len = len(new_prompt)

    # Simple heuristics for impact
    candidate = dict(baseline_dict)

    # Longer prompts tend to improve quality but increase latency/cost
    if "example" in new_prompt.lower() or "code" in new_prompt.lower():
        # Code-focused prompts improve quality
        candidate["success_rate"] = min(1.0, baseline_dict["success_rate"] + 0.15)
        candidate["p95_model_latency_ms"] *= 1.15  # 15% slower
        candidate["avg_cost_usd"] *= 1.10  # 10% more expensive

    elif "structure" in new_prompt.lower() or "format" in new_prompt.lower():
        # Structured prompts improve consistency
        candidate["success_rate"] = min(1.0, baseline_dict["success_rate"] + 0.10)
        candidate["p95_model_latency_ms"] *= 1.08

    elif "comprehensive" in new_prompt.lower() or "detailed" in new_prompt.lower():
        # Detailed prompts improve quality but are slower
        candidate["success_rate"] = min(1.0, baseline_dict["success_rate"] + 0.12)
        candidate["p95_model_latency_ms"] *= 1.20
        candidate["avg_cost_usd"] *= 1.15

    else:
        # Generic improvement
        candidate["success_rate"] = min(1.0, baseline_dict["success_rate"] + 0.08)
        candidate["p95_model_latency_ms"] *= 1.05
        candidate["avg_cost_usd"] *= 1.05

    return candidate


def create_ai_replay_evaluator(
    dataset: AIDataset,
    workflow_id: str,
):
    """Create a replay evaluator for the AI workflow."""

    from autoflow.evaluate.replay import ReplayEvaluator, ReplayDataset

    # Convert AIDataset to core ReplayDataset format
    core_dataset = ReplayDataset(runs=[{"run": r} for r in dataset.runs])

    def compute_baseline(_: ReplayDataset) -> dict[str, float]:
        return dict(compute_metrics(dataset, workflow_id=workflow_id).as_dict())

    def simulate_candidate(_: ReplayDataset, proposal: ChangeProposal) -> dict[str, float]:
        return simulate_candidate_metrics(dataset, proposal, workflow_id)

    return ReplayEvaluator(
        dataset=core_dataset,
        compute_baseline=compute_baseline,
        simulate_candidate=simulate_candidate,
        gates=ReplayGates(
            max_regressions={
                "p95_model_latency_ms": 200.0,  # Allow 200ms latency increase
                "avg_cost_usd": 0.005,  # Allow 0.5 cent increase
            },
            min_improvements={
                "success_rate": 0.05,  # Require 5% improvement in success rate
            },
        ),
    )


# =============================================================================
# Main Demo
# =============================================================================

def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    print(f"\n--- {title} ---\n")


def run_openai_demo() -> None:
    """Run the OpenAI + AutoFlow demo."""

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)

    print_section("AutoFlow + OpenAI: Prompt Optimization Demo")

    # Setup workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "autoflow_openai.db"
        replay_file = tmpdir / "qa_replay.jsonl"

        print_subsection("Configuration")
        print(f"Workspace: {tmpdir}")
        print(f"Questions: {len(TEST_QUESTIONS)}")
        print(f"Prompt variants: {len(PROMPT_VARIANTS)}")

        # Run initial experiments with different prompts
        print_subsection("Phase 1: Initial Data Collection")

        all_runs = []
        all_events = []

        for variant in PROMPT_VARIANTS:
            print(f"\nTesting variant: {variant.name}")
            print(f"  Prompt: {variant.system_prompt[:60]}...")
            print(f"  Temperature: {variant.temperature}")

            client = OpenAIQAClient(config=variant)

            for i, question in enumerate(TEST_QUESTIONS[:5], 1):  # Start with 5 questions
                print(f"  [{i}/{len(TEST_QUESTIONS[:5])}] {question[:50]}...", end=" ")

                answer, metrics = client.answer_question(question)

                if metrics["success"]:
                    # Evaluate quality
                    quality = evaluate_answer_quality(question, answer)

                    print(f"✓ (tokens: {metrics['total_tokens']}, quality: {quality['quality_score']:.1%})")

                    # Create AI run record
                    run = AIRun(
                        run_id=f"{variant.name}_{i}",
                        workflow_id="qa_system",
                        model_calls=[
                            ModelCall(
                                model=variant.model,
                                latency_ms=metrics["latency_ms"],
                                input_tokens=metrics["prompt_tokens"],
                                output_tokens=metrics["completion_tokens"],
                            )
                        ],
                        outcome=RunOutcome(
                            success=metrics["success"],
                            quality_score=quality["quality_score"],
                            cost_usd=metrics["cost_usd"],
                        ),
                        attributes={
                            "variant": variant.name,
                            "question": question,
                            "answer_length": metrics["answer_length"],
                            "issues": quality["issues"],
                        },
                    )
                    all_runs.append(run)

                    # Create AutoFlow event
                    event = make_event(
                        source="qa_system",
                        name="qa_run",
                        attributes={
                            "workflow_id": "qa_system",
                            "variant": variant.name,
                            "quality_score": quality["quality_score"],
                            "issues": quality["issues"],
                            "latency_ms": metrics["latency_ms"],
                            "cost_usd": metrics["cost_usd"],
                        },
                    )
                    all_events.append(event)
                else:
                    print(f"✗ ({metrics.get('error', 'unknown error')})")

        # Save dataset
        dataset = AIDataset(runs=tuple(all_runs))

        # Calculate baseline metrics
        print_subsection("Phase 2: Baseline Metrics")
        baseline = compute_metrics(dataset, workflow_id="qa_system")
        print(f"Total runs: {len(all_runs)}")
        print(f"Success rate: {baseline.success_rate:.1%}")
        print(f"Quality-adjusted success: {baseline.success_rate:.1%}")
        print(f"P95 model latency: {baseline.p95_model_latency_ms:.0f}ms")
        print(f"Avg cost per run: ${baseline.avg_cost_usd:.4f}")

        # Setup AutoFlow engine
        print_subsection("Phase 3: AutoFlow Analysis")

        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=str(db_path)),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(
                rules=[
                    LowQualityRule(
                        workflow_id="qa_system",
                        quality_threshold=0.70  # Trigger if quality below 70%
                    )
                ]
            ),
            evaluator=CompositeEvaluator(evaluators=[ShadowEvaluator()]),
            applier=ProposalApplier(
                policy=ApplyPolicy(
                    allowed_paths_prefixes=("config/",),
                    max_risk=RiskLevel.LOW
                ),
                backend=GitApplyBackend(repo_path=tmpdir),
            ),
        )

        # Ingest events
        engine.ingest(all_events)
        print(f"Ingested {len(all_events)} events")

        # Generate proposals
        proposals = engine.propose()
        print(f"\nGenerated {len(proposals)} proposal(s):")

        for p in proposals:
            print(f"\n  Proposal: {p.title}")
            print(f"    Description: {p.description}")
            print(f"    Risk: {p.risk}")
            print(f"    Target: {p.target_paths[0]}")
            print(f"    New prompt preview: {p.payload.get('value', '')[:100]}...")

        # Replay evaluation
        if proposals:
            print_subsection("Phase 4: Replay Evaluation")

            # Create custom replay evaluator
            replay_eval = create_ai_replay_evaluator(dataset, "qa_system")

            results = [replay_eval.evaluate(p) for p in proposals]

            for proposal, result in zip(proposals, results):
                print(f"\n  Proposal: {proposal.title[:50]}...")
                print(f"    Result: {'PASS ✓' if result.passed else 'FAIL ✗'}")
                print(f"    Score: {result.score:.4f}")

                # Show metrics
                print(f"\n    Metrics:")
                for key in ["success_rate", "p95_model_latency_ms", "avg_cost_usd"]:
                    baseline_val = result.metrics.get(f"baseline.{key}")
                    candidate_val = result.metrics.get(f"candidate.{key}")
                    delta_val = result.metrics.get(f"delta.{key}")

                    if baseline_val is not None:
                        if "rate" in key or "success" in key:
                            print(f"      {key}:")
                            print(f"        Baseline: {float(baseline_val):.1%}")
                            print(f"        Candidate: {float(candidate_val):.1%}")
                            print(f"        Delta: {float(delta_val):+.1%}")
                        elif "latency" in key:
                            print(f"      {key}:")
                            print(f"        Baseline: {float(baseline_val):.0f}ms")
                            print(f"        Candidate: {float(candidate_val):.0f}ms")
                            print(f"        Delta: {float(delta_val):+.0f}ms")
                        elif "cost" in key:
                            print(f"      {key}:")
                            print(f"        Baseline: ${float(baseline_val):.4f}")
                            print(f"        Candidate: ${float(candidate_val):.4f}")
                            print(f"        Delta: ${float(delta_val):+.4f}")

                print(f"\n    {result.notes}")

            # Apply passing proposals
            print_subsection("Phase 5: Apply Improvements")
            applied = [p for p, r in zip(proposals, results) if r.passed]
            rejected = [p for p, r in zip(proposals, results) if not r.passed]

            print(f"Applied: {len(applied)}")
            for p in applied:
                print(f"  ✓ {p.title}")

            print(f"\nRejected: {len(rejected)}")
            for p in rejected:
                print(f"  ✗ {p.title}")

            if applied:
                print_subsection("Phase 6: Validation with New Data")

                # Apply the first proposal's prompt changes
                best_proposal = applied[0]
                new_prompt = best_proposal.payload.get("value", "")

                print(f"Testing improved prompt: {best_proposal.title}")
                print(f"New prompt: {new_prompt[:100]}...")

                new_config = PromptConfig(
                    name="improved",
                    system_prompt=new_prompt,
                    temperature=0.5,
                )

                new_client = OpenAIQAClient(config=new_config)
                new_runs = []

                print(f"\nRunning validation questions...")
                for i, question in enumerate(TEST_QUESTIONS[5:8], 1):  # Test on different questions
                    print(f"  [{i}] {question[:50]}...", end=" ")
                    answer, metrics = new_client.answer_question(question)

                    if metrics["success"]:
                        quality = evaluate_answer_quality(question, answer)
                        print(f"✓ (quality: {quality['quality_score']:.1%})")

                        new_runs.append(AIRun(
                            run_id=f"improved_{i}",
                            workflow_id="qa_system",
                            model_calls=[
                                ModelCall(
                                    model=new_config.model,
                                    latency_ms=metrics["latency_ms"],
                                    input_tokens=metrics["prompt_tokens"],
                                    output_tokens=metrics["completion_tokens"],
                                )
                            ],
                            outcome=RunOutcome(
                                success=metrics["success"],
                                quality_score=quality["quality_score"],
                                cost_usd=metrics["cost_usd"],
                            ),
                        ))

                if new_runs:
                    new_metrics = compute_metrics(AIDataset(runs=tuple(new_runs)), workflow_id="qa_system")

                    print(f"\nValidation Results:")
                    print(f"  Success rate: {new_metrics.success_rate:.1%} (was {baseline.success_rate:.1%})")
                    print(f"  P95 latency: {new_metrics.p95_model_latency_ms:.0f}ms (was {baseline.p95_model_latency_ms:.0f}ms)")
                    print(f"  Avg cost: ${new_metrics.avg_cost_usd:.4f} (was ${baseline.avg_cost_usd:.4f})")

                    improvement = new_metrics.success_rate - baseline.success_rate
                    print(f"\n  Improvement: {improvement:+.1%}")

                    if improvement > 0:
                        print("  ✓ AutoFlow successfully improved the system!")
                    else:
                        print("  ✗ No significant improvement detected")

        print_section("Demo Complete!")

        print("\nKey Learnings:")
        print("  1. AutoFlow observed real OpenAI API calls and outcomes")
        print("  2. Detected quality issues using custom rules")
        print("  3. Proposed specific prompt improvements")
        print("  4. Validated proposals using replay on historical data")
        print("  5. Applied changes only when safety gates passed")
        print("  6. Validated improvements with new data")


if __name__ == "__main__":
    run_openai_demo()
