# AutoFlow + DBOS Integration

This directory contains examples demonstrating the integration between AutoFlow and DBOS for durable, fault-tolerant workflows.

## What is DBOS?

DBOS (Durable Backend for Observable Services) is a framework for building reliable applications with:
- **Durable Execution**: Operations survive process crashes and restarts
- **Automatic Retry**: Transient failures are automatically retried
- **Exactly-Once Semantics**: Guaranteed execution without duplication
- **Scheduled Workflows**: Cron-based job scheduling with durability
- **Queues**: High-throughput task queues with concurrency control

## Installation

```bash
pip install 'autoflow[dbos]'
```

Or for development:

```bash
pip install -e '.[dbos]'
```

## Examples

### `dbos_demo.py`

A comprehensive demonstration of AutoFlow + DBOS integration:

1. **Durable Patch Apply**: Git patch application that survives failures
2. **Durable PR Workflow**: Complete PR creation workflow (branch, commit, push, PR)
3. **Scheduled Optimization**: Cron-based automatic improvement loops
4. **Parallel Evaluation**: High-throughput concurrent proposal evaluation
5. **Configuration**: Environment variables and Python configuration

## Quick Start

### 1. Run the Demo

```bash
cd examples/integrations/dbos
python dbos_demo.py
```

### 2. Configure via Environment

```bash
# Enable DBOS
export AUTOFLOW_DBOS_ENABLED=true

# Database (PostgreSQL for production, SQLite for dev)
export AUTOFLOW_DBOS_SYSTEM_DATABASE_URL=postgresql://user:pass@localhost/autoflow

# Scheduler
export AUTOFLOW_DBOS_SCHEDULER_ENABLED=true
export AUTOFLOW_DBOS_SCHEDULE="0 */6 * * *"  # Every 6 hours

# Apply mode
export AUTOFLOW_DBOS_APPLY_MODE="patch"  # or "pr" or "custom"

# PR mode settings
export AUTOFLOW_DBOS_PR_REPOSITORY="owner/repo"
export AUTOFLOW_DBOS_PR_BRANCH_PREFIX="autoflow/"

# Evaluation queues
export AUTOFLOW_DBOS_EVAL_CONCURRENCY=5
```

### 3. Use in Code

```python
from autoflow.factory import autoflow_dbos

# Create engine with durable patch apply
engine = autoflow_dbos(
    allowed_paths=("config/", "prompts/"),
    apply_mode="patch",
)

# All operations are now durable!
proposals = engine.propose()
engine.apply(proposals)  # Survives failures
```

## Features

### Durable Apply Backends

When you apply a proposal with DBOS:

```python
from autoflow.factory import autoflow_dbos_pr

engine = autoflow_dbos_pr(
    repository="myorg/myrepo",
    allowed_paths=("config/",),
)

# Apply creates a PR durably:
# 1. Create feature branch (survives failure)
# 2. Apply patch (survives failure)
# 3. Commit changes (survives failure)
# 4. Push to remote (survives failure)
# 5. Create PR (survives failure)
engine.applier.apply(proposal)
```

If any step fails (network error, crash, etc.), DBOS resumes from the last checkpoint.

### Scheduled Optimization

Run automatic improvement on a schedule:

```python
from autoflow.apply.dbos_scheduler import DBOSScheduler

scheduler = DBOSScheduler(
    engine=engine,
    optimization_schedule="0 */6 * * *",  # Every 6 hours
)

# Register the scheduled workflow
scheduler.register_scheduled_workflows()

# Or run manually
result = scheduler.run_improvement_loop()
print(f"Generated: {result['proposals_generated']}")
print(f"Applied: {result['proposals_applied']}")
```

### Parallel Evaluation

Evaluate proposals in parallel with controlled concurrency:

```python
from autoflow.apply.dbos_queues import DBOSQueues

queues = DBOSQueues(
    queue_name="autoflow-eval",
    concurrency=5,  # Max 5 concurrent evaluations
)

# Evaluate a batch
results = queues.evaluate_batch(proposals)

# Or enqueue for async processing
handle_ids = queues.evaluate_batch_async(proposals)
```

## Use Cases

### When to Use DBOS with AutoFlow

1. **Production Deployments**: Ensure changes are applied reliably
2. **Scheduled Maintenance**: Run optimization during low-traffic hours
3. **High-Volume Evaluation**: Process many proposals in parallel
4. **Multi-Step Workflows**: PR creation requires multiple steps
5. **Audit Requirements**: Durable execution logs for compliance

### When NOT to Use DBOS

1. **Local Development**: Overhead for simple testing
2. **Single-Node Deployments**: If durability isn't critical
3. **Low Volume**: If you rarely apply changes

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AUTOFLOW_DBOS_ENABLED` | `false` | Enable DBOS integration |
| `AUTOFLOW_DBOS_APP_NAME` | `autoflow` | Application name |
| `AUTOFLOW_DBOS_SYSTEM_DATABASE_URL` | `sqlite:///dbos.db` | DBOS database URL |
| `AUTOFLOW_DBOS_SCHEDULER_ENABLED` | `true` | Enable scheduled workflows |
| `AUTOFLOW_DBOS_SCHEDULE` | `0 */6 * * *` | Cron schedule |
| `AUTOFLOW_DBOS_APPLY_MODE` | `patch` | Apply mode: `patch`, `pr`, `custom` |
| `AUTOFLOW_DBOS_PR_REPOSITORY` | `null` | GitHub repo for PR mode |
| `AUTOFLOW_DBOS_PR_BRANCH_PREFIX` | `autoflow/` | Prefix for PR branches |
| `AUTOFLOW_DBOS_EVAL_CONCURRENCY` | `5` | Max concurrent evaluations |

## Resources

- **DBOS Documentation**: https://docs.dbos.dev
- **AutoFlow README**: ../../../README.md
- **Examples README**: ../../README.md
