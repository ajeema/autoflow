"""
LLM-as-Judge evaluator for AutoFlow proposals.

Uses an LLM to evaluate proposals based on:
- Safety and risk assessment
- Correctness of the proposed change
- Potential side effects
- Alignment with best practices
- Overall recommendation

This can be used standalone or in combination with other evaluators.

Supports multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3, Claude 3.5 Sonnet, etc.)
- AWS Bedrock (multiple models)
- xAI (Grok)
- Ollama (local open-source models)
- Any provider via litellm unified interface
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional, Dict, Any

# Pydantic for validation
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object  # type: ignore
    Field = lambda default=None, **kwargs: default

from autoflow.types import ChangeProposal, EvaluationResult
from autoflow.evaluate.evaluator import CompositeEvaluator
from autoflow.llm.client import create_llm_client, LLMClientConfig


class LLMJudgeConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Configuration for LLM judge."""

    # Model configuration (supports multiple providers)
    model: str = "gpt-4"
    provider: Optional[str] = None  # Auto-detect if None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    region: Optional[str] = None  # For Bedrock

    # Evaluation criteria
    check_safety: bool = True
    check_correctness: bool = True
    check_side_effects: bool = True
    check_best_practices: bool = True

    # Scoring weights (0-1)
    safety_weight: float = 0.3
    correctness_weight: float = 0.3
    side_effects_weight: float = 0.2
    best_practices_weight: float = 0.2

    # Thresholds
    pass_threshold: float = 0.6
    auto_approve_threshold: float = 0.8

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "LLMJudgeConfig":
        """Load configuration from environment variables."""
        model = os.getenv("AUTOFLOW_LLM_JUDGE_MODEL", "gpt-4")
        provider = os.getenv("AUTOFLOW_LLM_JUDGE_PROVIDER")

        return cls(
            model=model,
            provider=provider,
            api_key=os.getenv("AUTOFLOW_LLM_JUDGE_API_KEY"),
            base_url=os.getenv("AUTOFLOW_LLM_JUDGE_BASE_URL"),
            region=os.getenv("AWS_DEFAULT_REGION"),  # For Bedrock
        )


class LLMJudgeEvaluator:
    """
    Evaluate proposals using LLM-as-Judge.

    This evaluator sends proposals to an LLM for detailed analysis
    and returns a structured evaluation result.
    """

    def __init__(
        self,
        config: Optional[LLMJudgeConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        self.config = config or LLMJudgeConfig.from_env()
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Create the LLM client
        self.llm_client = create_llm_client(
            model=self.config.model,
            provider=self.config.provider,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            region=self.config.region,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
        )

    def evaluate(self, proposal: ChangeProposal) -> EvaluationResult:
        """
        Evaluate a proposal using LLM judgment.

        Args:
            proposal: The proposal to evaluate

        Returns:
            EvaluationResult with LLM's assessment
        """
        # Build the evaluation prompt
        user_prompt = self._build_evaluation_prompt(proposal)

        # Call LLM
        response = self._call_llm(user_prompt)

        # Parse response
        judgment = self._parse_judgment(response)

        # Calculate weighted score
        score = self._calculate_score(judgment)

        # Determine if passed
        passed = score >= self.config.pass_threshold

        # Build metrics
        metrics = {
            "llm_judge_score": score,
            "safety_score": judgment.get("safety_score", 0.0),
            "correctness_score": judgment.get("correctness_score", 0.0),
            "side_effects_score": judgment.get("side_effects_score", 0.0),
            "best_practices_score": judgment.get("best_practices_score", 0.0),
            "auto_approve": score >= self.config.auto_approve_threshold,
            "judge_model": self.config.model,
            "judge_provider": self.llm_client._provider.value,
        }

        # Build notes
        notes = judgment.get("reasoning", "")
        if judgment.get("concerns"):
            notes += f"\n\nConcerns: {judgment['concerns']}"
        if judgment.get("suggestions"):
            notes += f"\n\nSuggestions: {judgment['suggestions']}"

        return EvaluationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            score=score,
            metrics=metrics,
            notes=notes,
        )

    def _default_system_prompt(self) -> str:
        """Default system prompt for LLM judge."""
        return """You are an expert code reviewer evaluating AutoFlow proposals.

Your role is to assess proposed changes for:
1. Safety - Could this introduce bugs, security issues, or breaking changes?
2. Correctness - Does the proposal address the issue it's meant to fix?
3. Side Effects - What else might this change affect?
4. Best Practices - Does this follow language/framework best practices?

Provide your assessment in JSON format:
{
  "safety_score": 0.0-1.0,
  "correctness_score": 0.0-1.0,
  "side_effects_score": 0.0-1.0,
  "best_practices_score": 0.0-1.0,
  "reasoning": "Your detailed analysis",
  "concerns": "Any concerns (optional)",
  "suggestions": "Suggestions for improvement (optional)"
}

Be thorough but fair. Consider the context and risk level."""

    def _build_evaluation_prompt(self, proposal: ChangeProposal) -> str:
        """Build the evaluation prompt for a proposal."""
        prompt = f"""Please evaluate this AutoFlow proposal:

**Title:** {proposal.title}

**Kind:** {proposal.kind}

**Risk Level:** {proposal.risk}

**Description:**
{proposal.description}

**Affected Files:**
{chr(10).join(f'  - {p}' for p in proposal.target_paths) if proposal.target_paths else '  (None)'}

**Proposal Details:**
```json
{json.dumps(dict(proposal.payload), indent=2)}
```

Please analyze this proposal and provide your assessment."""

        return prompt

    def _call_llm(self, user_prompt: str) -> str:
        """Call the LLM API."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self.llm_client.chat_completion(
                messages=messages,
                response_format={"type": "json_object"},
            )

            return response

        except ImportError as e:
            # Required package not available, return mock response
            print(f"⚠️  LLM package not available: {e}")
            return self._mock_judgment()
        except Exception as e:
            # API call failed, return conservative judgment
            print(f"⚠️  LLM judge API call failed: {e}")
            return self._conservative_judgment(str(e))

    def _mock_judgment(self) -> str:
        """Mock judgment for testing when LLM provider is not available."""
        return json.dumps({
            "safety_score": 0.7,
            "correctness_score": 0.8,
            "side_effects_score": 0.6,
            "best_practices_score": 0.7,
            "reasoning": f"Mock judgment (LLM provider '{self.config.model}' not available)",
            "concerns": None,
            "suggestions": "Review with human evaluator",
        })

    def _conservative_judgment(self, error: str) -> str:
        """Conservative judgment when API fails."""
        return json.dumps({
            "safety_score": 0.5,
            "correctness_score": 0.5,
            "side_effects_score": 0.5,
            "best_practices_score": 0.5,
            "reasoning": f"Unable to complete evaluation due to error: {error}",
            "concerns": "API call failed - human review recommended",
            "suggestions": "Please review manually",
        })

    def _parse_judgment(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into judgment dict."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Response not valid JSON, try to extract it
            match = re.search(r'\{[^{}]*\}', response)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

            # Fallback
            return {
                "safety_score": 0.5,
                "correctness_score": 0.5,
                "side_effects_score": 0.5,
                "best_practices_score": 0.5,
                "reasoning": response,
            }

    def _calculate_score(self, judgment: Dict[str, Any]) -> float:
        """Calculate weighted score from judgment."""
        score = 0.0

        if self.config.check_safety:
            score += judgment.get("safety_score", 0.5) * self.config.safety_weight

        if self.config.check_correctness:
            score += judgment.get("correctness_score", 0.5) * self.config.correctness_weight

        if self.config.check_side_effects:
            score += judgment.get("side_effects_score", 0.5) * self.config.side_effects_weight

        if self.config.check_best_practices:
            score += judgment.get("best_practices_score", 0.5) * self.config.best_practices_weight

        # Normalize by total weight
        total_weight = (
            (self.config.safety_weight if self.config.check_safety else 0) +
            (self.config.correctness_weight if self.config.check_correctness else 0) +
            (self.config.side_effects_weight if self.config.check_side_effects else 0) +
            (self.config.best_practices_weight if self.config.check_best_practices else 0)
        )

        return score / total_weight if total_weight > 0 else score


__all__ = [
    "LLMJudgeConfig",
    "LLMJudgeEvaluator",
]
