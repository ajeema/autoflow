#!/usr/bin/env python3
"""
AutoFlow + DBOS Integration Demo

This script demonstrates how to use AutoFlow with DBOS for:
1. Durable apply backends (survives failures during git patch application)
2. Scheduled optimization workflows (cron-based improvement loop)
3. Parallel proposal evaluation with queues

Prerequisites:
    pip install 'autoflow[dbos]'

Or for development:
    pip install -e '.[dbos]'

Environment Variables (optional):
    export AUTOFLOW_DBOS_ENABLED=true
    export AUTOFLOW_DBOS_SYSTEM_DATABASE_URL=postgresql://user:pass@localhost/db
    export AUTOFLOW_DBOS_APP_NAME=autoflow-demo

Usage:
    python dbos_demo.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from autoflow.factory import autoflow_dbos, autoflow_dbos_pr, DBOS_AVAILABLE


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---\n")


def check_dbos_available() -> bool:
    """Check if DBOS is installed and available."""
    if not DBOS_AVAILABLE:
        print("DBOS is not installed!")
        print("\nInstall with:")
        print("  pip install 'autoflow[dbos]'")
        print("\nOr for development:")
        print("  pip install -e '.[dbos]'")
        return False
    return True


def demo_durable_patch_apply():
    """Demonstrate durable patch application with DBOS."""
    print_section("DEMO 1: Durable Patch Apply")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a sample config file
        config_dir = tmpdir / "config"
        config_dir.mkdir()
        config_file = config_dir / "retry_config.yaml"
        config_file.write_text("""
retry_policy:
  max_retries: 1
  backoff_ms: [100, 200]
  jitter: false
""")

        print_subsection("Setup")
        print(f"Working directory: {tmpdir}")
        print(f"Config file: {config_file}")
        print("\nInitial config: max_retries=1, backoff_ms=[100, 200]")

        # Create AutoFlow engine with DBOS backend
        engine = autoflow_dbos(
            allowed_paths=("config/",),
            apply_mode="patch",
        )

        print_subsection("Engine Created with DBOS Backend")
        print(f"DBOS Available: {DBOS_AVAILABLE}")
        print(f"Apply Mode: patch (durable git apply)")
        print(f"Allowed Paths: config/")

        # Simulate proposal application
        print_subsection("Simulating Proposal Application")

        from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

        proposal = ChangeProposal(
            proposal_id="prop_001",
            kind=ProposalKind.CONFIG_EDIT,
            title="Increase retry limit for resilience",
            description="Bump max_retries from 1 to 3 to handle transient failures",
            risk=RiskLevel.LOW,
            target_paths=("config/retry_config.yaml",),
            payload={
                "patch": """--- a/config/retry_config.yaml
+++ b/config/retry_config.yaml
@@ -1,5 +1,5 @@
 retry_policy:
-  max_retries: 1
+  max_retries: 3
   backoff_ms: [100, 200]
   jitter: false
"""
            }
        )

        print(f"Proposal: {proposal.title}")
        print(f"Target: {proposal.target_paths[0]}")
        print(f"Risk: {proposal.risk}")

        # Apply the proposal
        print_subsection("Applying Proposal")
        print("With DBOS backend, the apply operation is durable:")
        print("  - Survives process crashes")
        print("  - Automatic retry on transient failures")
        print("  - Exactly-once execution guarantee")

        # Note: Actual apply would require git repo initialization
        # engine.applier.apply(proposal)


def demo_durable_pr_workflow():
    """Demonstrate durable PR workflow with DBOS."""
    print_section("DEMO 2: Durable PR Workflow")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        print_subsection("Setup")
        print(f"Working directory: {tmpdir}")

        # Create AutoFlow engine with PR mode
        print_subsection("Creating Engine with PR Mode")

        print("With PR mode, AutoFlow + DBOS will:")
        print("  1. Create a feature branch")
        print("  2. Apply the proposed changes")
        print("  3. Commit with proposal metadata")
        print("  4. Push to remote")
        print("  5. Create a pull request")
        print("\nAll steps are durable - if any step fails, it resumes from checkpoint!")

        # Example configuration
        config = {
            "repository": "myorg/myrepo",
            "branch_prefix": "autoflow/",
        }

        print(f"\nConfiguration:")
        print(f"  Repository: {config['repository']}")
        print(f"  Branch Prefix: {config['branch_prefix']}")

        # Engine would be created like:
        # engine = autoflow_dbos_pr(
        #     repository="myorg/myrepo",
        #     allowed_paths=("config/", "prompts/"),
        # )

        print("\nTo enable PR mode:")
        print("  engine = autoflow_dbos_pr(")
        print("      repository='myorg/myrepo',")
        print("      allowed_paths=('config/', 'prompts/'),")
        print("  )")


def demo_scheduled_optimization():
    """Demonstrate scheduled optimization with DBOS."""
    print_section("DEMO 3: Scheduled Optimization Workflows")

    print_subsection("DBOS Scheduler Features")
    print("DBOS enables cron-based scheduled optimization:")

    print("\nFeatures:")
    print("  1. Cron Scheduling")
    print("     - Run improvement loop on schedule (e.g., every 6 hours)")
    print("     - Survives process restarts")
    print("     - Automatic recovery from failures")

    print("\n  2. Durable Workflows")
    print("     - Each optimization run is recorded")
    print("     - Track proposals generated, evaluated, applied")
    print("     - Audit trail of all changes")

    print("\n  3. Manual Triggers")
    print("     - Trigger optimization on-demand")
    print("     - Evaluate and apply specific proposals by ID")

    print("\nExample schedule (cron format):")
    schedules = {
        "Every 6 hours": "0 */6 * * *",
        "Every midnight": "0 0 * * *",
        "Every Monday 9am": "0 9 * * 1",
        "Every hour": "0 * * * *",
    }
    for name, cron in schedules.items():
        print(f"  {name:20s} -> {cron}")

    print("\nConfiguration via environment:")
    print("  export AUTOFLOW_DBOS_SCHEDULER_ENABLED=true")
    print("  export AUTOFLOW_DBOS_SCHEDULE='0 */6 * * *'  # Every 6 hours")

    print("\nOr programmatically:")
    print("""
from autoflow.apply.dbos_scheduler import DBOSScheduler

scheduler = DBOSScheduler(
    engine=engine,
    optimization_schedule="0 */6 * * *",
)

# Register the scheduled workflow
scheduler.register_scheduled_workflows()

# Or run manually
result = scheduler.run_improvement_loop()
print(f"Generated: {result['proposals_generated']}")
print(f"Applied: {result['proposals_applied']}")
""")


def demo_parallel_evaluation():
    """Demonstrate parallel proposal evaluation with DBOS queues."""
    print_section("DEMO 4: Parallel Evaluation with Queues")

    print_subsection("DBOS Queue Features")
    print("DBOS queues enable high-throughput parallel evaluation:")

    print("\nFeatures:")
    print("  1. Configurable Concurrency")
    print("     - Control max concurrent evaluations")
    print("     - Prevent resource exhaustion")

    print("\n  2. Durable Task Queue")
    print("     - Evaluations survive worker failures")
    print("     - Automatic retry on transient errors")

    print("\n  3. Async Workflow")
    print("     - Enqueue proposals for background processing")
    print("     - Get workflow IDs for tracking")

    print("\nExample configuration:")
    print("  export AUTOFLOW_DBOS_EVAL_CONCURRENCY=5")

    print("\nOr programmatically:")
    print("""
from autoflow.apply.dbos_queues import DBOSQueues

queues = DBOSQueues(
    queue_name="autoflow-eval",
    concurrency=5,
)

# Evaluate a batch of proposals
proposals = [proposal1, proposal2, proposal3, ...]
results = queues.evaluate_batch(proposals)

# Or enqueue for async processing
handle_ids = queues.evaluate_batch_async(proposals)

# Check queue status
status = queues.get_queue_status()
print(f"Queue: {status['queue_name']}")
print(f"Concurrency: {status['concurrency']}")
""")

    print_subsection("Example: Batch Evaluation")

    from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

    # Create sample proposals
    proposals = [
        ChangeProposal(
            proposal_id=f"prop_{i:03d}",
            kind=ProposalKind.CONFIG_EDIT,
            title=f"Optimization {i}",
            description=f"Proposal number {i}",
            risk=RiskLevel.LOW,
            target_paths=("config/settings.yaml",),
            payload={"key": f"value_{i}"}
        )
        for i in range(1, 6)
    ]

    print(f"Created {len(proposals)} sample proposals:")
    for p in proposals[:3]:
        print(f"  - {p.proposal_id}: {p.title}")
    print(f"  ... and {len(proposals) - 3} more")

    print("\nWith DBOS queues, these would be evaluated in parallel")
    print(f"(up to the configured concurrency limit)")


def demo_configuration():
    """Demonstrate DBOS configuration options."""
    print_section("DEMO 5: DBOS Configuration")

    print_subsection("Environment Variables")
    print("Configure DBOS via environment variables:\n")

    config_vars = [
        ("AUTOFLOW_DBOS_ENABLED", "true", "Enable DBOS integration"),
        ("AUTOFLOW_DBOS_APP_NAME", "autoflow", "Application name for DBOS"),
        ("AUTOFLOW_DBOS_SYSTEM_DATABASE_URL", "postgresql://...", "DBOS database (Postgres)"),
        ("AUTOFLOW_DBOS_SCHEDULER_ENABLED", "true", "Enable scheduled workflows"),
        ("AUTOFLOW_DBOS_SCHEDULE", "0 */6 * * *", "Cron schedule for optimization"),
        ("AUTOFLOW_DBOS_APPLY_MODE", "patch", "Apply mode: patch, pr, custom"),
        ("AUTOFLOW_DBOS_PR_REPOSITORY", "owner/repo", "GitHub repo for PR mode"),
        ("AUTOFLOW_DBOS_PR_BRANCH_PREFIX", "autoflow/", "Prefix for PR branches"),
        ("AUTOFLOW_DBOS_EVAL_CONCURRENCY", "5", "Max concurrent evaluations"),
    ]

    for var, default, description in config_vars:
        print(f"  {var}")
        print(f"    Default: {default}")
        print(f"    Description: {description}")
        print()

    print_subsection("Python Configuration")
    print("Or configure via Python code:\n")
    print("""
from autoflow.config import AutoFlowConfig, DBOSConfig

config = AutoFlowConfig(
    dbos=DBOSConfig(
        enabled=True,
        application_name="autoflow-demo",
        system_database_url="postgresql://localhost/autoflow",
        scheduler_enabled=True,
        optimization_schedule="0 */6 * * *",
        apply_mode="patch",
        evaluation_queue_concurrency=5,
    )
)
""")


def main():
    """Run all DBOS demo scenarios."""
    print("\n" + "=" * 70)
    print("  AutoFlow + DBOS Integration Demo")
    print("  Durable Workflows for Auto-Improvement")
    print("=" * 70)

    if not check_dbos_available():
        print("\nContinuing with demo (without actual DBOS execution)...\n")

    try:
        demo_durable_patch_apply()
        demo_durable_pr_workflow()
        demo_scheduled_optimization()
        demo_parallel_evaluation()
        demo_configuration()

        print_section("Demo Complete!")
        print("\nKey Takeaways:")
        print("  1. DBOS provides durable execution for AutoFlow operations")
        print("  2. Patch/PR workflows survive failures and restarts")
        print("  3. Scheduled optimization runs automatically on cron")
        print("  4. Parallel evaluation queues handle high throughput")
        print("\nNext Steps:")
        print("  - Install DBOS: pip install 'autoflow[dbos]'")
        print("  - Configure database: export AUTOFLOW_DBOS_SYSTEM_DATABASE_URL=...")
        print("  - Run scheduled optimizations")
        print("\nFor more information, see:")
        print("  - DBOS Docs: https://docs.dbos.dev")
        print("  - AutoFlow README: ../README.md\n")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
