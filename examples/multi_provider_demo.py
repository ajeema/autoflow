"""
Demo: Provider-Agnostic LLM Judge

This demonstrates how to use the LLM-as-Judge evaluator
with different LLM providers.
"""

import asyncio
from autoflow.evaluate.llm_judge import LLMJudgeEvaluator, LLMJudgeConfig
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel


def demo_openai():
    """Demo using OpenAI (GPT-4) as the judge."""
    print("\n" + "=" * 70)
    print("DEMO 1: OpenAI GPT-4 as Judge")
    print("=" * 70)

    evaluator = LLMJudgeEvaluator(
        config=LLMJudgeConfig(
            model="gpt-4",
            api_key="sk-test-key",  # Replace with actual key
        )
    )

    print(f"✅ Created evaluator with model: {evaluator.config.model}")
    print(f"   Provider: {evaluator.llm_client._provider.value}")


def demo_anthropic():
    """Demo using Anthropic (Claude) as the judge."""
    print("\n" + "=" * 70)
    print("DEMO 2: Anthropic Claude as Judge")
    print("=" * 70)

    evaluator = LLMJudgeEvaluator(
        config=LLMJudgeConfig(
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test-key",  # Replace with actual key
        )
    )

    print(f"✅ Created evaluator with model: {evaluator.config.model}")
    print(f"   Provider: {evaluator.llm_client._provider.value}")


def demo_ollama():
    """Demo using Ollama (local models) as the judge."""
    print("\n" + "=" * 70)
    print("DEMO 3: Ollama Local Model as Judge")
    print("=" * 70)

    evaluator = LLMJudgeEvaluator(
        config=LLMJudgeConfig(
            model="llama3:8b",
            base_url="http://localhost:11434",
        )
    )

    print(f"✅ Created evaluator with model: {evaluator.config.model}")
    print(f"   Provider: {evaluator.llm_client._provider.value}")
    print(f"   Base URL: {evaluator.config.base_url}")


def demo_bedrock():
    """Demo using AWS Bedrock as the judge."""
    print("\n" + "=" * 70)
    print("DEMO 4: AWS Bedrock as Judge")
    print("=" * 70)

    evaluator = LLMJudgeEvaluator(
        config=LLMJudgeConfig(
            model="amazon.titan-text-express-v1",
            region="us-east-1",
            api_key="aws-test-key",  # Replace with actual AWS credentials
        )
    )

    print(f"✅ Created evaluator with model: {evaluator.config.model}")
    print(f"   Provider: {evaluator.llm_client._provider.value}")
    print(f"   Region: {evaluator.config.region}")


def demo_auto_detection():
    """Demo automatic provider detection from model names."""
    print("\n" + "=" * 70)
    print("DEMO 5: Automatic Provider Detection")
    print("=" * 70)

    from autoflow.llm.client import LLMClientConfig

    models = [
        ("gpt-4", "OpenAI"),
        ("claude-3-5-sonnet-20241022", "Anthropic"),
        ("llama3:8b", "Ollama"),
        ("amazon.titan-text-express-v1", "AWS Bedrock"),
        ("grok-beta", "xAI"),
        ("azure/gpt-4", "Azure OpenAI"),
    ]

    print("Provider detection from model names:")
    for model, expected in models:
        provider = LLMClientConfig._detect_provider(model)
        status = "✅" if provider.value.lower() in expected.lower() or expected.lower() in provider.value.lower() else "❌"
        print(f"{status} {model:40} -> {provider.value:15} (expected: {expected})")


def demo_custom_evaluation():
    """Demo custom evaluation configuration."""
    print("\n" + "=" * 70)
    print("DEMO 6: Custom Evaluation Configuration")
    print("=" * 70)

    # Create evaluator with custom thresholds
    evaluator = LLMJudgeEvaluator(
        config=LLMJudgeConfig(
            model="gpt-4",
            pass_threshold=0.7,  # Require higher score to pass
            auto_approve_threshold=0.9,  # Require very high score to auto-approve
            safety_weight=0.4,  # Prioritize safety
            correctness_weight=0.3,
            side_effects_weight=0.2,
            best_practices_weight=0.1,
            check_best_practices=False,  # Disable best practices check
        )
    )

    print("Custom evaluation configuration:")
    print(f"  Pass threshold: {evaluator.config.pass_threshold}")
    print(f"  Auto-approve threshold: {evaluator.config.auto_approve_threshold}")
    print(f"  Safety weight: {evaluator.config.safety_weight}")
    print(f"  Correctness weight: {evaluator.config.correctness_weight}")
    print(f"  Side effects weight: {evaluator.config.side_effects_weight}")
    print(f"  Best practices weight: {evaluator.config.best_practices_weight}")
    print(f"  Check best practices: {evaluator.config.check_best_practices}")


def demo_from_env():
    """Demo loading configuration from environment variables."""
    print("\n" + "=" * 70)
    print("DEMO 7: Load Configuration from Environment")
    print("=" * 70)

    import os

    # Set environment variables (in production, these would be set beforehand)
    print("Setting environment variables:")
    os.environ["AUTOFLOW_LLM_JUDGE_MODEL"] = "claude-3-5-sonnet-20241022"
    print("  AUTOFLOW_LLM_JUDGE_MODEL=claude-3-5-sonnet-20241022")

    os.environ["AUTOFLOW_LLM_JUDGE_API_KEY"] = "sk-ant-test-key"
    print("  AUTOFLOW_LLM_JUDGE_API_KEY=sk-ant-test-key")

    # Load config from environment
    config = LLMJudgeConfig.from_env()

    evaluator = LLMJudgeEvaluator(config=config)

    print(f"\n✅ Created evaluator from environment:")
    print(f"   Model: {evaluator.config.model}")
    print(f"   Provider: {evaluator.llm_client._provider.value}")

    # Clean up
    del os.environ["AUTOFLOW_LLM_JUDGE_MODEL"]
    del os.environ["AUTOFLOW_LLM_JUDGE_API_KEY"]


def main():
    """Run all demos."""
    demo_openai()
    demo_anthropic()
    demo_ollama()
    demo_bedrock()
    demo_auto_detection()
    demo_custom_evaluation()
    demo_from_env()

    print("\n" + "=" * 70)
    print("All demos complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. ✅ Supports multiple LLM providers (OpenAI, Anthropic, Bedrock, etc.)")
    print("  2. ✅ Auto-detects provider from model name")
    print("  3. ✅ Can explicitly specify provider if needed")
    print("  4. ✅ Customizable evaluation thresholds and weights")
    print("  5. ✅ Load configuration from environment variables")
    print("\nTo use with actual API calls:")
    print("  - Set your API key in environment or pass to constructor")
    print("  - Install required packages (openai, anthropic, boto3)")
    print("  - Call evaluator.evaluate(proposal) to evaluate proposals")


if __name__ == "__main__":
    main()
