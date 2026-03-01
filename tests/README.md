# AutoFlow Tests

This directory contains comprehensive tests for the AutoFlow library.

## Test Coverage

The test suite covers:
- **Observation Events** (`test_observe_events.py`) - Event creation and properties
- **Context Graph** (`test_context_graph.py`) - Graph builders and stores
- **Decision Graph** (`test_decision_graph.py`) - Rules and proposal generation
- **Evaluators** (`test_evaluators.py`) - Shadow, replay, and composite evaluation
- **Apply Module** (`test_apply.py`) - Policies, applier, and backends
- **Workflow Module** (`test_workflow.py`) - Workflow-aware graph building and metrics
- **Engine** (`test_engine.py`) - End-to-end engine integration
- **Types** (`test_types.py`) - Core type definitions
- **Errors** (`test_errors.py`) - Exception hierarchy

## Running Tests with uv

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Dependencies

```bash
# Install all dependencies (including dev)
uv sync --group dev

# Or install specific groups
uv sync --all-extras
uv sync --group dev --group all
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=autoflow --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_engine.py

# Run specific test
uv run pytest tests/test_engine.py::TestAutoImproveEngine::test_init

# Run with verbose output
uv run pytest -v

# Run with coverage HTML report
uv run pytest --cov=autoflow --cov-report=html
open htmlcov/index.html
```

### Run Tests with Traditional pip

If you're not using uv:

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=autoflow --cov-report=term-missing
```

## Test Organization

- `conftest.py` - Pytest fixtures and configuration
- `test_*.py` - Test files organized by module

### Fixtures

Available fixtures:
- `tmp_path` - Temporary directory for file operations
- `sample_events` - Sample observation events
- `sample_workflow_events` - Sample workflow step events
- `sample_nodes` - Sample graph nodes
- `sample_edges` - Sample graph edges

## Coverage Goals

The test suite aims for >90% code coverage across all modules.

Current coverage can be checked with:
```bash
uv run pytest --cov=autoflow --cov-report=term-missing
```

## Continuous Integration

Tests are configured to run with:
- pytest for test execution
- pytest-cov for coverage tracking
- ruff for linting
- mypy for type checking
