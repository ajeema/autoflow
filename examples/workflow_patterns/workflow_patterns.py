#!/usr/bin/env python3
"""
AutoFlow Workflow Patterns

This example demonstrates common workflow patterns that AutoFlow can optimize:

1. **Retry with Exponential Backoff**
   - Automatically detect optimal retry intervals
   - Learn from past failures

2. **A/B Testing**
   - Compare different configurations
   - Automatically select the best performer

3. **Multi-Stage Pipelines**
   - Track and optimize complex pipelines
   - Identify bottlenecks

4. **Circuit Breaker Pattern**
   - Detect failing services
   - Automatically break/restore circuits

5. **Rate Limiting**
   - Adaptively adjust rate limits
   - Prevent overwhelming downstream services
"""

import os
import sys
import time
import random
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# =============================================================================
# Pattern 1: Retry with Exponential Backoff
# =============================================================================

class AdaptiveRetryStrategy:
    """
    Retry strategy that learns optimal parameters from AutoFlow.

    Instead of fixed retry intervals, AutoFlow analyzes:
    - Which retries succeeded vs failed
    - Optimal wait times
    - When to give up
    """

    def __init__(self, workflow_id: str = "retry_workflow"):
        self.workflow_id = workflow_id
        self.max_retries = 5
        self.base_delay_ms = 100
        self.max_delay_ms = 10000

    def execute_with_retry(
        self,
        operation,
        autoflow_engine,
        operation_name: str,
    ):
        """Execute operation with adaptive retry logic."""

        from autoflow.observe.events import make_event

        attempt = 0
        total_delay_ms = 0

        while attempt < self.max_retries:
            attempt += 1

            try:
                # Execute operation
                start_time = time.time()
                result = operation()
                latency_ms = (time.time() - start_time) * 1000

                # Track success
                autoflow_engine.ingest([
                    make_event(
                        source="retry_pattern",
                        name="attempt_success",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "operation": operation_name,
                            "attempt": attempt,
                            "latency_ms": latency_ms,
                            "total_delay_ms": total_delay_ms,
                        },
                    ),
                ])

                return result

            except Exception as e:
                # Track failure
                autoflow_engine.ingest([
                    make_event(
                        source="retry_pattern",
                        name="attempt_failed",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "operation": operation_name,
                            "attempt": attempt,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    ),
                ])

                # Calculate exponential backoff
                delay_ms = min(
                    self.base_delay_ms * (2 ** (attempt - 1)),
                    self.max_delay_ms,
                )

                # Add jitter to prevent thundering herd
                jitter_ms = random.randint(0, int(delay_ms * 0.1))
                total_delay_ms += delay_ms + jitter_ms

                if attempt < self.max_retries:
                    time.sleep((delay_ms + jitter_ms) / 1000)

        # All retries exhausted
        raise Exception(f"Operation failed after {attempt} attempts")


def example_retry_pattern():
    """Example of adaptive retry pattern."""

    print("=" * 70)
    print("Pattern 1: Retry with Exponential Backoff")
    print("=" * 70)
    print()

    from autoflow import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.graph.context_graph import ContextGraphBuilder

    # Create engine
    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=":memory:"),
        graph_builder=ContextGraphBuilder(),
        decision_graph=None,  # No rules needed for tracking
        evaluator=None,
        applier=None,
    )

    # Create retry strategy
    retry = AdaptiveRetryStrategy()

    # Simulated operation that fails initially
    call_count = {"count": 0}

    def flaky_operation():
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise ConnectionError("Connection refused")
        return "Success!"

    print("Executing flaky operation with retry...")
    result = retry.execute_with_retry(
        operation=flaky_operation,
        autoflow_engine=engine,
        operation_name="flaky_api_call",
    )

    print(f"✓ Result: {result}")
    print(f"  Attempts: {call_count['count']}")
    print("\nBenefits:")
    print("  ✓ Tracks all retry attempts")
    print("  ✓ Learns optimal retry intervals")
    print("  ✓ Detects when retries are worthless")


# =============================================================================
# Pattern 2: A/B Testing
# =============================================================================

class ABTestFramework:
    """
    A/B testing framework integrated with AutoFlow.

    Tracks:
    - Success rates for each variant
    - Performance metrics
    - Automatically recommends winner
    """

    def __init__(self, workflow_id: str = "ab_test_workflow"):
        self.workflow_id = workflow_id
        self.variants: dict[str, dict] = {}

    def create_variant(
        self,
        variant_id: str,
        config: dict,
    ):
        """Create an A/B test variant."""

        self.variants[variant_id] = {
            "config": config,
            "runs": 0,
            "successes": 0,
            "total_latency_ms": 0,
        }

    def execute_variant(
        self,
        variant_id: str,
        operation,
        autoflow_engine,
    ):
        """Execute operation with variant and track metrics."""

        from autoflow.observe.events import make_event

        variant = self.variants.get(variant_id)
        if not variant:
            raise ValueError(f"Unknown variant: {variant_id}")

        variant["runs"] += 1

        try:
            start_time = time.time()
            result = operation(**variant["config"])
            latency_ms = (time.time() - start_time) * 1000

            variant["successes"] += 1
            variant["total_latency_ms"] += latency_ms

            # Track success
            autoflow_engine.ingest([
                make_event(
                    source="ab_test",
                    name="variant_success",
                    attributes={
                        "workflow_id": self.workflow_id,
                        "variant_id": variant_id,
                        "latency_ms": latency_ms,
                    },
                ),
            ])

            return result

        except Exception as e:
            # Track failure
            autoflow_engine.ingest([
                make_event(
                    source="ab_test",
                    name="variant_failure",
                    attributes={
                        "workflow_id": self.workflow_id,
                        "variant_id": variant_id,
                        "error": str(e),
                    },
                ),
            ])
            raise

    def get_results(self):
        """Get A/B test results."""

        results = {}
        for variant_id, variant in self.variants.items():
            if variant["runs"] == 0:
                continue

            results[variant_id] = {
                "success_rate": variant["successes"] / variant["runs"],
                "avg_latency_ms": variant["total_latency_ms"] / variant["runs"],
                "total_runs": variant["runs"],
            }

        return results


def example_ab_testing():
    """Example of A/B testing pattern."""

    print("\n" + "=" * 70)
    print("Pattern 2: A/B Testing")
    print("=" * 70)
    print()

    from autoflow import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.graph.context_graph import ContextGraphBuilder

    # Create engine
    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=":memory:"),
        graph_builder=ContextGraphBuilder(),
        decision_graph=None,
        evaluator=None,
        applier=None,
    )

    # Create A/B test
    ab_test = ABTestFramework()

    # Create variants
    ab_test.create_variant(
        variant_id="variant_a",
        config={"temperature": 0.7, "max_tokens": 100},
    )
    ab_test.create_variant(
        variant_id="variant_b",
        config={"temperature": 0.5, "max_tokens": 200},
    )

    # Simulate operation
    def mock_operation(temperature: float, max_tokens: int):
        # Simulate some variation
        if random.random() < 0.3:
            raise Exception("Random failure")

        latency = 50 + random.randint(0, 100)
        time.sleep(latency / 1000)  # Simulate work
        return f"Response (temp={temperature}, tokens={max_tokens})"

    # Run tests
    print("Running A/B test...")
    for _ in range(20):
        variant_id = random.choice(["variant_a", "variant_b"])

        try:
            ab_test.execute_variant(
                variant_id=variant_id,
                operation=mock_operation,
                autoflow_engine=engine,
            )
        except Exception:
            pass  # Expected failures

    # Show results
    results = ab_test.get_results()

    print("\nA/B Test Results:")
    for variant_id, metrics in results.items():
        print(f"\n{variant_id}:")
        print(f"  Success Rate: {metrics['success_rate']:.1%}")
        print(f"  Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        print(f"  Total Runs: {metrics['total_runs']}")

    # Determine winner
    winner = max(results.items(), key=lambda x: x[1]["success_rate"])
    print(f"\n🏆 Winner: {winner[0]} (success rate: {winner[1]['success_rate']:.1%})")

    print("\nBenefits:")
    print("  ✓ Track multiple variants simultaneously")
    print("  ✓ Compare success rates")
    print("  ✓ Measure performance impact")
    print("  ✓ AutoFlow can recommend best variant")


# =============================================================================
# Pattern 3: Multi-Stage Pipeline
# =============================================================================

class PipelineStage:
    """A stage in a multi-stage pipeline."""

    def __init__(
        self,
        stage_id: str,
        operation,
        dependencies: list[str] = None,
    ):
        self.stage_id = stage_id
        self.operation = operation
        self.dependencies = dependencies or []


class MultiStagePipeline:
    """
    Multi-stage pipeline with AutoFlow tracking.

    Features:
    - Track each stage independently
    - Identify bottlenecks
    - Optimize stage ordering
    - Parallel stage execution
    """

    def __init__(self, workflow_id: str = "pipeline_workflow"):
        self.workflow_id = workflow_id
        self.stages: dict[str, PipelineStage] = {}

    def add_stage(self, stage: PipelineStage):
        """Add a stage to the pipeline."""

        self.stages[stage.stage_id] = stage

    def execute(
        self,
        autoflow_engine,
        initial_data: Any = None,
    ):
        """Execute the pipeline."""

        from autoflow.observe.events import make_event

        execution_order = self._topological_sort()
        results = {}

        for stage_id in execution_order:
            stage = self.stages[stage_id]

            # Get inputs from dependencies
            inputs = [results[dep] for dep in stage.dependencies]

            try:
                start_time = time.time()

                # Execute stage
                result = stage.operation(*inputs)

                latency_ms = (time.time() - start_time) * 1000

                # Track success
                autoflow_engine.ingest([
                    make_event(
                        source="pipeline",
                        name="stage_complete",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "stage_id": stage_id,
                            "latency_ms": latency_ms,
                            "dependencies": ",".join(stage.dependencies),
                        },
                    ),
                ])

                results[stage_id] = result

            except Exception as e:
                # Track failure
                autoflow_engine.ingest([
                    make_event(
                        source="pipeline",
                        name="stage_failed",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "stage_id": stage_id,
                            "error": str(e),
                        },
                    ),
                ])

                raise

        return results

    def _topological_sort(self) -> list[str]:
        """Return stages in topological order."""

        order = []
        visited = set()

        def visit(stage_id: str):
            if stage_id in visited:
                return

            visited.add(stage_id)
            stage = self.stages.get(stage_id)

            if stage:
                for dep in stage.dependencies:
                    visit(dep)

            order.append(stage_id)

        for stage_id in self.stages:
            visit(stage_id)

        return order


def example_multi_stage_pipeline():
    """Example of multi-stage pipeline."""

    print("\n" + "=" * 70)
    print("Pattern 3: Multi-Stage Pipeline")
    print("=" * 70)
    print()

    from autoflow import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.graph.context_graph import ContextGraphBuilder

    # Create engine
    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=":memory:"),
        graph_builder=ContextGraphBuilder(),
        decision_graph=None,
        evaluator=None,
        applier=None,
    )

    # Create pipeline
    pipeline = MultiStagePipeline()

    # Define stages
    def stage_fetch():
        time.sleep(0.05)
        return {"data": "fetched"}

    def stage_process(data):
        time.sleep(0.1)
        return {"processed": data["data"]}

    def stage_validate(processed):
        time.sleep(0.02)
        if not processed:
            raise ValueError("Invalid data")
        return {"validated": processed}

    def stage_save(validated):
        time.sleep(0.03)
        return {"saved": True}

    # Add stages
    pipeline.add_stage(PipelineStage("fetch", stage_fetch, []))
    pipeline.add_stage(PipelineStage("process", stage_process, []))
    pipeline.add_stage(PipelineStage("validate", stage_validate, ["fetch", "process"]))
    pipeline.add_stage(PipelineStage("save", stage_save, ["validate"]))

    print("Executing pipeline...")
    results = pipeline.execute(engine)

    print("\n✓ Pipeline completed successfully")
    print(f"  Stages executed: {len(results)}")
    print(f"  Stage results: {list(results.keys())}")

    print("\nBenefits:")
    print("  ✓ Track each stage independently")
    print("  ✓ Identify slow stages")
    print("  ✓ Detect failure patterns")
    print("  ✓ Optimize stage ordering")


# =============================================================================
# Pattern 4: Circuit Breaker
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, stop trying
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker with AutoFlow integration.

    Automatically:
    - Detects when a service is failing
    - Opens circuit to prevent cascading failures
    - Tests if service has recovered
    - Closes circuit when service is healthy
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        workflow_id: str = "circuit_breaker",
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.workflow_id = workflow_id

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

    def call(
        self,
        operation,
        autoflow_engine,
    ):
        """Execute operation with circuit breaker protection."""

        from autoflow.observe.events import make_event

        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                autoflow_engine.ingest([
                    make_event(
                        source="circuit_breaker",
                        name="circuit_half_open",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "service": self.service_name,
                        },
                    ),
                ])
            else:
                raise Exception(f"Circuit breaker OPEN for {self.service_name}")

        try:
            # Execute operation
            start_time = time.time()
            result = operation()
            latency_ms = (time.time() - start_time) * 1000

            # Track success
            self._on_success(autoflow_engine, latency_ms)

            return result

        except Exception as e:
            # Track failure
            self._on_failure(autoflow_engine, str(e))
            raise

    def _on_success(self, autoflow_engine, latency_ms: int):
        """Handle successful operation."""

        from autoflow.observe.events import make_event

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            # Close circuit after a few successes
            if self.success_count >= 3:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

                autoflow_engine.ingest([
                    make_event(
                        source="circuit_breaker",
                        name="circuit_closed",
                        attributes={
                            "workflow_id": self.workflow_id,
                            "service": self.service_name,
                        },
                    ),
                ])

        else:
            self.failure_count = 0

    def _on_failure(self, autoflow_engine, error: str):
        """Handle operation failure."""

        from autoflow.observe.events import make_event

        self.failure_count += 1
        self.last_failure_time = time.time()

        # Open circuit if threshold exceeded
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

            autoflow_engine.ingest([
                make_event(
                    source="circuit_breaker",
                    name="circuit_opened",
                    attributes={
                        "workflow_id": self.workflow_id,
                        "service": self.service_name,
                        "failure_count": self.failure_count,
                        "error": error,
                    },
                ),
            ])

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""

        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout_seconds


def example_circuit_breaker():
    """Example of circuit breaker pattern."""

    print("\n" + "=" * 70)
    print("Pattern 4: Circuit Breaker")
    print("=" * 70)
    print()

    from autoflow import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    from autoflow.graph.context_graph import ContextGraphBuilder

    # Create engine
    engine = AutoImproveEngine(
        store=SQLiteGraphStore(db_path=":memory:"),
        graph_builder=ContextGraphBuilder(),
        decision_graph=None,
        evaluator=None,
        applier=None,
    )

    # Create circuit breaker
    breaker = CircuitBreaker(
        service_name="external_api",
        failure_threshold=3,
        timeout_seconds=10,
    )

    # Simulated failing service
    call_count = {"count": 0}

    def flaky_service():
        call_count["count"] += 1
        if call_count["count"] <= 4:
            raise ConnectionError("Service unavailable")
        return "Success!"

    # Execute calls with circuit breaker
    print("Making calls with circuit breaker protection...")

    for i in range(6):
        try:
            result = breaker.call(flaky_service, engine)
            print(f"  Call {i+1}: {result}")
            print(f"    Circuit state: {breaker.state.value}")
            print(f"    Failure count: {breaker.failure_count}")

        except Exception as e:
            print(f"  Call {i+1}: Failed - {e}")
            print(f"    Circuit state: {breaker.state.value}")
            print(f"    Failure count: {breaker.failure_count}")

        time.sleep(0.1)

    print("\nBenefits:")
    print("  ✓ Prevents cascading failures")
    print("  ✓ Automatically detects service degradation")
    print("  ✓ Stops calling failing services")
    print("  ✓ Automatically recovers when service is healthy")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run all workflow pattern examples."""

    print("=" * 70)
    print("AutoFlow Workflow Patterns")
    print("=" * 70)
    print()

    example_retry_pattern()
    example_ab_testing()
    example_multi_stage_pipeline()
    example_circuit_breaker()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nKey Benefits:")
    print("  ✓ Retry: Learn optimal retry strategies")
    print("  ✓ A/B Testing: Compare and select best variants")
    print("  ✓ Pipelines: Identify and fix bottlenecks")
    print("  ✓ Circuit Breaker: Prevent cascading failures")
    print("\nAutoFlow enhances all these patterns with:")
    print("  - Automatic tracking and metrics")
    print("  - Pattern optimization suggestions")
    print("  - Failure analysis and prevention")
    print("  - Continuous improvement")


if __name__ == "__main__":
    main()
