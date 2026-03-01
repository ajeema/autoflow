#!/usr/bin/env python3
"""
AutoFlow AI Framework Integration Examples

This file contains examples of integrating AutoFlow with popular AI frameworks:
- Pydantic AI
- LangChain
- CrewAI

Each framework can leverage AutoFlow for:
1. Continuous improvement of prompts and configurations
2. Automatic error detection and resolution
3. Performance optimization
4. A/B testing of different strategies
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# =============================================================================
# Pydantic AI Integration
# =============================================================================

class PydanticAIAutoFlow:
    """
    Integration between AutoFlow and Pydantic AI.

    Pydantic AI is a type-safe AI application framework that uses
    Pydantic for structured outputs and validation.

    Setup:
        pip install pydantic-ai openai
        export OPENAI_API_KEY=your_key

    Features:
    - Auto-improvement of agent system prompts
    - Dynamic tool selection optimization
    - Validation rule refinement
    """

    def __init__(self, workflow_id: str = "pydantic_ai_workflow"):
        self.workflow_id = workflow_id

    def create_auto_improving_agent(
        self,
        agent_name: str,
        initial_system_prompt: str,
        openai_model: str = "gpt-4o",
    ):
        """Create a Pydantic AI agent that AutoFlow can improve."""

        try:
            from pydantic_ai import Agent
            from pydantic_ai.models.openai import OpenAIModel

            model = OpenAIModel(openai_model)

            agent = Agent(
                model=model,
                system_prompt=initial_system_prompt,
                name=agent_name,
            )

            return agent

        except ImportError:
            print("pydantic-ai required: pip install pydantic-ai")
            raise

    async def run_with_auto_improvement(
        self,
        agent,
        user_message: str,
        autoflow_engine,
    ):
        """Run agent and capture metrics for AutoFlow."""

        from autoflow.observe.events import make_event

        # Run the agent
        result = agent.run(user_message)

        # Capture events
        events = [
            make_event(
                source="pydantic_ai",
                name="agent_run",
                attributes={
                    "workflow_id": self.workflow_id,
                    "agent_name": agent.name,
                    "user_message_length": len(user_message),
                    "result_length": len(str(result.data)),
                    "model": agent.model.model_name,
                },
            ),
        ]

        # Check for validation errors
        if hasattr(result, "all_messages"):
            for msg in result.all_messages:
                if hasattr(msg, "role") and msg.role == "system":
                    events.append(
                        make_event(
                            source="pydantic_ai",
                            name="system_prompt_used",
                            attributes={
                                "workflow_id": self.workflow_id,
                                "prompt_length": len(str(msg.content)),
                            },
                        )
                    )

        # Ingest events into AutoFlow
        autoflow_engine.ingest(events)

        return result

    def create_autoflow_rules_for_pydantic_ai(self):
        """Create AutoFlow rules specific to Pydantic AI patterns."""

        from autoflow.types import ProposalKind, RiskLevel
        from uuid import uuid4

        class PydanticAIPromptRule:
            """Rule to improve Pydantic AI agent system prompts."""

            def __init__(self, workflow_id: str):
                self.workflow_id = workflow_id

            def propose(self, nodes):
                """Analyze agent runs and propose prompt improvements."""

                # Filter relevant events
                agent_runs = [
                    n for n in nodes
                    if n.properties.get("workflow_id") == self.workflow_id
                    and n.properties.get("source") == "pydantic_ai"
                    and n.properties.get("name") == "agent_run"
                ]

                if len(agent_runs) < 5:
                    return []

                # Calculate metrics
                avg_result_length = sum(
                    r.properties.get("result_length", 0)
                    for r in agent_runs
                ) / len(agent_runs)

                # Check for issues
                proposals = []

                if avg_result_length < 100:
                    proposals.append({
                        "proposal_id": str(uuid4()),
                        "kind": ProposalKind.CONFIG_EDIT,
                        "title": "Expand Pydantic AI system prompt for detailed responses",
                        "description": (
                            f"Agent responses are averaging {avg_result_length:.0f} chars. "
                            "Consider adding instructions to be more verbose and detailed."
                        ),
                        "risk": RiskLevel.LOW,
                        "target_paths": ("config/agent_prompts.yaml",),
                        "payload": {
                            "improvement_type": "prompt_expansion",
                            "target_agent": "all",
                        },
                    })

                return proposals

        return PydanticAIPromptRule(self.workflow_id)


async def example_pydantic_ai_with_autoflow():
    """Example of Pydantic AI + AutoFlow integration."""

    print("=" * 70)
    print("Pydantic AI + AutoFlow Example")
    print("=" * 70)
    print()

    try:
        from autoflow import AutoImproveEngine
        from autoflow.apply.applier import ProposalApplier
        from autoflow.apply.policy import ApplyPolicy
        from autoflow.decide.decision_graph import DecisionGraph
        from autoflow.evaluate.shadow import ShadowEvaluator
        from autoflow.graph.context_graph import ContextGraphBuilder
        from autoflow.graph.sqlite_store import SQLiteGraphStore

        # Initialize AutoFlow engine
        print("1. Initializing AutoFlow engine...")
        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=":memory:"),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(rules=[]),
            evaluator=ShadowEvaluator(),
            applier=ProposalApplier(
                policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            ),
        )

        # Create Pydantic AI integration
        pydantic_integration = PydanticAIAutoFlow()

        # Create an agent
        print("2. Creating Pydantic AI agent...")
        agent = pydantic_integration.create_auto_improving_agent(
            agent_name="math_tutor",
            initial_system_prompt="You are a helpful math tutor. Keep answers brief.",
        )

        # Run some queries
        print("\n3. Running agent queries with AutoFlow tracking...")
        queries = [
            "What is 2 + 2?",
            "Explain calculus",
            "What is a matrix?",
        ]

        for query in queries:
            print(f"   Query: {query}")
            result = await pydantic_integration.run_with_auto_improvement(
                agent=agent,
                user_message=query,
                autoflow_engine=engine,
            )
            print(f"   Response: {str(result.data)[:100]}...")

        print("\n✓ Pydantic AI integration completed")
        print("\nBenefits:")
        print("  ✓ Automatic tracking of agent runs")
        print("  ✓ Prompt optimization suggestions")
        print("  ✓ Response quality monitoring")

    except ImportError as e:
        print(f"⚠️  Skipping example: {e}")


# =============================================================================
# LangChain Integration
# =============================================================================

class LangChainAutoFlow:
    """
    Integration between AutoFlow and LangChain.

    LangChain is a framework for building context-aware reasoning applications.

    Setup:
        pip install langchain langchain-openai
        export OPENAI_API_KEY=your_key

    Features:
    - Chain optimization
    - Prompt template improvement
    - Tool selection optimization
    - Memory management improvements
    """

    def __init__(self, workflow_id: str = "langchain_workflow"):
        self.workflow_id = workflow_id

    def create_auto_improving_chain(
        self,
        chain_name: str,
        prompt_template: str,
        openai_model: str = "gpt-4",
    ):
        """Create a LangChain chain that AutoFlow can improve."""

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=openai_model, temperature=0)
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | llm | StrOutputParser()

            return chain

        except ImportError:
            print("langchain required: pip install langchain langchain-openai")
            raise

    async def run_chain_with_tracking(
        self,
        chain,
        inputs: dict,
        autoflow_engine,
        chain_name: str,
    ):
        """Run LangChain chain with AutoFlow tracking."""

        from autoflow.observe.events import make_event
        import time

        start_time = time.time()

        # Run the chain
        result = chain.invoke(inputs)
        latency_ms = (time.time() - start_time) * 1000

        # Capture events
        events = [
            make_event(
                source="langchain",
                name="chain_execution",
                attributes={
                    "workflow_id": self.workflow_id,
                    "chain_name": chain_name,
                    "latency_ms": latency_ms,
                    "input_keys": list(inputs.keys()),
                    "result_length": len(str(result)),
                },
            ),
        ]

        # Ingest into AutoFlow
        autoflow_engine.ingest(events)

        return result

    def create_autoflow_rules_for_langchain(self):
        """Create AutoFlow rules specific to LangChain patterns."""

        from autoflow.types import ProposalKind, RiskLevel
        from uuid import uuid4

        class LangChainOptimizationRule:
            """Rule to optimize LangChain chains."""

            def __init__(self, workflow_id: str):
                self.workflow_id = workflow_id

            def propose(self, nodes):
                """Analyze chain runs and propose optimizations."""

                chain_runs = [
                    n for n in nodes
                    if n.properties.get("workflow_id") == self.workflow_id
                    and n.properties.get("source") == "langchain"
                ]

                if len(chain_runs) < 10:
                    return []

                proposals = []

                # Check for slow chains
                slow_runs = [
                    r for r in chain_runs
                    if r.properties.get("latency_ms", 0) > 5000
                ]

                if len(slow_runs) > len(chain_runs) * 0.3:  # > 30% slow
                    proposals.append({
                        "proposal_id": str(uuid4()),
                        "kind": ProposalKind.CONFIG_EDIT,
                        "title": "Optimize slow LangChain chains",
                        "description": (
                            f"{len(slow_runs)}/{len(chain_runs)} chain runs are "
                            "slow (>5s). Consider adding caching, streaming, "
                            "or switching to a faster model."
                        ),
                        "risk": RiskLevel.MEDIUM,
                        "target_paths": ("config/chains.yaml",),
                        "payload": {
                            "optimization": "speed",
                        },
                    })

                return proposals

        return LangChainOptimizationRule(self.workflow_id)


async def example_langchain_with_autoflow():
    """Example of LangChain + AutoFlow integration."""

    print("\n" + "=" * 70)
    print("LangChain + AutoFlow Example")
    print("=" * 70)
    print()

    try:
        from autoflow import AutoImproveEngine
        from autoflow.apply.applier import ProposalApplier
        from autoflow.apply.policy import ApplyPolicy
        from autoflow.decide.decision_graph import DecisionGraph
        from autoflow.evaluate.shadow import ShadowEvaluator
        from autoflow.graph.context_graph import ContextGraphBuilder
        from autoflow.graph.sqlite_store import SQLiteGraphStore

        # Initialize AutoFlow engine
        print("1. Initializing AutoFlow engine...")
        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=":memory:"),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(rules=[]),
            evaluator=ShadowEvaluator(),
            applier=ProposalApplier(
                policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            ),
        )

        # Create LangChain integration
        langchain_integration = LangChainAutoFlow()

        # Create a simple chain
        print("2. Creating LangChain chain...")
        chain = langchain_integration.create_auto_improving_chain(
            chain_name="qa_chain",
            prompt_template="Answer the question: {question}",
        )

        # Run queries
        print("\n3. Running chain queries with AutoFlow tracking...")
        queries = [
            {"question": "What is Python?"},
            {"question": "Explain machine learning"},
            {"question": "What is a neural network?"},
        ]

        for query_input in queries:
            print(f"   Query: {query_input['question']}")
            result = await langchain_integration.run_chain_with_tracking(
                chain=chain,
                inputs=query_input,
                autoflow_engine=engine,
                chain_name="qa_chain",
            )
            print(f"   Response: {str(result)[:100]}...")

        print("\n✓ LangChain integration completed")
        print("\nBenefits:")
        print("  ✓ Chain execution tracking")
        print("  ✓ Performance optimization suggestions")
        print("  ✓ Automatic bottleneck detection")

    except ImportError as e:
        print(f"⚠️  Skipping example: {e}")


# =============================================================================
# CrewAI Integration
# =============================================================================

class CrewAIAutoFlow:
    """
    Integration between AutoFlow and CrewAI.

    CrewAI is a framework for orchestrating role-playing AI agents.

    Setup:
        pip install crewai crewai-tools
        export OPENAI_API_KEY=your_key

    Features:
    - Crew composition optimization
    - Agent role refinement
    - Task delegation improvement
    - Multi-agent coordination enhancement
    """

    def __init__(self, workflow_id: str = "crewai_workflow"):
        self.workflow_id = workflow_id

    def create_auto_improving_crew(
        self,
        crew_name: str,
        agents: list,
        tasks: list,
    ):
        """Create a CrewAI crew that AutoFlow can improve."""

        try:
            from crewai import Crew

            crew = Crew(
                agents=agents,
                tasks=tasks,
                verbose=True,
            )

            return crew

        except ImportError:
            print("crewai required: pip install crewai")
            raise

    async def run_crew_with_tracking(
        self,
        crew,
        inputs: dict,
        autoflow_engine,
        crew_name: str,
    ):
        """Run CrewAI crew with AutoFlow tracking."""

        from autoflow.observe.events import make_event
        import time

        start_time = time.time()

        # Run the crew
        try:
            result = crew.kickoff(inputs=inputs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)

        latency_ms = (time.time() - start_time) * 1000

        # Capture events
        events = [
            make_event(
                source="crewai",
                name="crew_execution",
                attributes={
                    "workflow_id": self.workflow_id,
                    "crew_name": crew_name,
                    "latency_ms": latency_ms,
                    "success": success,
                    "error": error,
                    "agent_count": len(crew.agents) if hasattr(crew, 'agents') else 0,
                },
            ),
        ]

        # Ingest into AutoFlow
        autoflow_engine.ingest(events)

        return result, success

    def create_autoflow_rules_for_crewai(self):
        """Create AutoFlow rules specific to CrewAI patterns."""

        from autoflow.types import ProposalKind, RiskLevel
        from uuid import uuid4

        class CrewAIOptimizationRule:
            """Rule to optimize CrewAI crews."""

            def __init__(self, workflow_id: str):
                self.workflow_id = workflow_id

            def propose(self, nodes):
                """Analyze crew runs and propose optimizations."""

                crew_runs = [
                    n for n in nodes
                    if n.properties.get("workflow_id") == self.workflow_id
                    and n.properties.get("source") == "crewai"
                ]

                if len(crew_runs) < 5:
                    return []

                proposals = []

                # Check for failures
                failures = [
                    r for r in crew_runs
                    if not r.properties.get("success", True)
                ]

                if len(failures) > len(crew_runs) * 0.2:  # > 20% failure rate
                    proposals.append({
                        "proposal_id": str(uuid4()),
                        "kind": ProposalKind.CONFIG_EDIT,
                        "title": "Improve CrewAI crew reliability",
                        "description": (
                            f"{len(failures)}/{len(crew_runs)} crew runs failed. "
                            "Consider adding error handling, retry logic, or "
                            "simplifying agent tasks."
                        ),
                        "risk": RiskLevel.MEDIUM,
                        "target_paths": ("config/crews.yaml",),
                        "payload": {
                            "optimization": "reliability",
                        },
                    })

                return proposals

        return CrewAIOptimizationRule(self.workflow_id)


async def example_crewai_with_autoflow():
    """Example of CrewAI + AutoFlow integration."""

    print("\n" + "=" * 70)
    print("CrewAI + AutoFlow Example")
    print("=" * 70)
    print()

    try:
        from autoflow import AutoImproveEngine
        from autoflow.apply.applier import ProposalApplier
        from autoflow.apply.policy import ApplyPolicy
        from autoflow.decide.decision_graph import DecisionGraph
        from autoflow.evaluate.shadow import ShadowEvaluator
        from autoflow.graph.context_graph import ContextGraphBuilder
        from autoflow.graph.sqlite_store import SQLiteGraphStore

        # Initialize AutoFlow engine
        print("1. Initializing AutoFlow engine...")
        engine = AutoImproveEngine(
            store=SQLiteGraphStore(db_path=":memory:"),
            graph_builder=ContextGraphBuilder(),
            decision_graph=DecisionGraph(rules=[]),
            evaluator=ShadowEvaluator(),
            applier=ProposalApplier(
                policy=ApplyPolicy(allowed_paths_prefixes=("config/",)),
            ),
        )

        # Create CrewAI integration
        crewai_integration = CrewAIAutoFlow()

        print("\n2. Creating CrewAI crew...")
        print("   (Skipping actual crew creation - requires OpenAI API key)")
        print("   In production, you would:")
        print("   - Define agents with roles")
        print("   - Create tasks for agents")
        print("   - Assemble into a crew")
        print("   - Track executions with AutoFlow")

        print("\n✓ CrewAI integration prepared")
        print("\nBenefits:")
        print("  ✓ Crew execution tracking")
        print("  ✓ Agent performance analysis")
        print("  ✓ Task delegation optimization")
        print("  ✓ Multi-agent coordination improvements")

    except ImportError as e:
        print(f"⚠️  Skipping example: {e}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run all AI framework integration examples."""

    print("=" * 70)
    print("AutoFlow AI Framework Integration Examples")
    print("=" * 70)
    print()

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set")
        print("   Some examples require OpenAI API:")
        print("   export OPENAI_API_KEY=your-key-here")
        print()

    # Run examples
    await example_pydantic_ai_with_autoflow()
    await example_langchain_with_autoflow()
    await example_crewai_with_autoflow()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nKey Benefits of AI Framework Integration:")
    print("  ✓ Automatic prompt optimization")
    print("  ✓ Performance monitoring and improvement")
    print("  ✓ Error detection and resolution")
    print("  ✓ A/B testing of configurations")
    print("  ✓ Continuous learning from usage")
    print("\nNext Steps:")
    print("  1. Install your preferred AI framework")
    print("  2. Set up AutoFlow engine with appropriate rules")
    print("  3. Wrap your agents/chains/crews with tracking")
    print("  4. Let AutoFlow suggest and apply improvements")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
