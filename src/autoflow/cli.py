"""
AutoFlow CLI - Command-line interface using Pydantic Settings.

This module provides a comprehensive CLI for AutoFlow with automatic
argument parsing, environment variable support, and help generation.

Usage:
    # As a module
    python -m autoflow.cli propose --context file.py --max-proposals 5

    # Using the installed command
    autoflow propose --context file.py --max-proposals 5

    # With environment variables
    AUTOFLOW_MAX_PROPOSALS=10 autoflow propose --context file.py
"""

import os
import sys
from typing import Optional

import typer
from pydantic import BaseModel, Field

from autoflow.api_models import (
    ProposeRequest,
    EvaluateRequest,
    ApplyRequest,
    QueryGraphRequest,
    IngestEventsRequest,
)
from autoflow.config import AutoFlowConfig, ConfigProfiles, get_config, setup_autoflow
from autoflow.types import make_event


# =============================================================================
# CLI Settings with Pydantic
# =============================================================================


class CLISettings(BaseModel):
    """
    CLI-specific settings loaded from environment variables.

    These settings control CLI behavior separate from engine configuration.
    """

    # Output formatting
    output_format: str = Field(
        default="json",
        description="Output format: json, yaml, table, text",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")
    quiet: bool = Field(default=False, description="Suppress non-error output")
    color: bool = Field(default=True, description="Enable colored output")

    # Engine configuration
    config_file: Optional[str] = Field(
        default=None,
        description="Path to configuration file (YAML or JSON)",
    )
    profile: Optional[str] = Field(
        default=None,
        description="Configuration profile: development, testing, production, serverless",
    )

    # Connection settings
    db_path: Optional[str] = Field(
        default=None,
        description="Database path (overrides config)",
    )
    otel_endpoint: Optional[str] = Field(
        default=None,
        description="OpenTelemetry endpoint (overrides config)",
    )

    class Config:
        env_prefix = "AUTOFLOW_CLI"
        extra = "ignore"

    @classmethod
    def from_env(cls) -> "CLISettings":
        """Load settings from environment variables."""
        return cls(
            output_format=os.getenv("AUTOFLOW_CLI_OUTPUT_FORMAT", "json"),
            verbose=os.getenv("AUTOFLOW_CLI_VERBOSE", "false").lower() == "true",
            quiet=os.getenv("AUTOFLOW_CLI_QUIET", "false").lower() == "true",
            color=os.getenv("AUTOFLOW_CLI_COLOR", "true").lower() == "true",
            config_file=os.getenv("AUTOFLOW_CLI_CONFIG"),
            profile=os.getenv("AUTOFLOW_CLI_PROFILE"),
            db_path=os.getenv("AUTOFLOW_DB_PATH"),
            otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        )


# =============================================================================
# CLI Application
# =============================================================================

app = typer.Typer(
    name="autoflow",
    help="AutoFlow - Policy-gated auto-improvement engine",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def propose(
    context: str = typer.Option(..., "--context", "-c", help="Context data as JSON string or @file.json"),
    max_proposals: int = typer.Option(10, "--max-proposals", "-n", help="Maximum proposals to generate"),
    max_risk: str = typer.Option("medium", "--max-risk", "-r", help="Maximum risk level"),
    include_reasoning: bool = typer.Option(False, "--reasoning", help="Include proposal explanations"),
    output: str = typer.Option("json", "--output", "-o", help="Output format"),
):
    """
    Generate change proposals.

    Analyzes the given context and generates improvement proposals
    subject to policy constraints and risk limits.

    Example:
        autoflow propose --context @context.json --max-proposals 5
    """
    from autoflow import AutoImproveEngine
    from autoflow.graph.sqlite_store import SQLiteGraphStore
    import json

    # Load configuration
    cli_settings = CLISettings.from_env()
    config = _load_config(cli_settings)

    # Load context
    if context.startswith("@"):
        with open(context[1:], "r") as f:
            context_data = json.load(f)
    else:
        context_data = json.loads(context)

    # Create request
    request = ProposeRequest(
        context=context_data,
        max_proposals=max_proposals,
        max_risk=max_risk,
        include_reasoning=include_reasoning,
    )

    # TODO: Actually invoke the engine
    # For now, just show the request
    _print_output({"request": request.model_dump(), "note": "Engine integration pending"})


@app.command()
def evaluate(
    proposal: str = typer.Option(..., "--proposal", "-p", help="Proposal data as JSON string or @file.json"),
    evaluator: str = typer.Option("shadow", "--evaluator", "-e", help="Evaluator type"),
    dataset: str = typer.Option(None, "--dataset", "-d", help="Dataset for replay evaluation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format"),
):
    """
    Evaluate a change proposal.

    Evaluates a proposal against various criteria including
    test performance, code quality, and policy compliance.

    Example:
        autoflow evaluate --proposal @proposal.json --evaluator replay --dataset @dataset.json
    """
    import json

    # Load configuration
    cli_settings = CLISettings.from_env()
    config = _load_config(cli_settings)

    # Load proposal
    if proposal.startswith("@"):
        with open(proposal[1:], "r") as f:
            proposal_data = json.load(f)
    else:
        proposal_data = json.loads(proposal)

    # Load dataset if provided
    dataset_data = None
    if dataset:
        if dataset.startswith("@"):
            with open(dataset[1:], "r") as f:
                dataset_data = json.load(f)
        else:
            dataset_data = json.loads(dataset)

    # Create request
    request = EvaluateRequest(
        proposal=proposal_data,
        evaluator_type=evaluator,
        dataset=dataset_data,
    )

    # TODO: Actually invoke the evaluator
    _print_output({"request": request.model_dump(), "note": "Evaluator integration pending"})


@app.command()
def apply(
    proposal_id: str = typer.Option(..., "--proposal-id", "-p", help="ID of proposal to apply"),
    dry_run: bool = typer.Option(True, "--dry-run", "-n", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", "-f", help="Apply even if policy checks fail"),
):
    """
    Apply a change proposal.

    Applies the proposal to the codebase, optionally performing
    a dry-run to preview changes first.

    Example:
        autoflow apply --proposal-id prop-123 --dry-run
    """
    # Load configuration
    cli_settings = CLISettings.from_env()
    config = _load_config(cli_settings)

    # Create request
    request = ApplyRequest(
        proposal_id=proposal_id,
        dry_run=dry_run,
        force=force,
    )

    # TODO: Actually apply the proposal
    _print_output({"request": request.model_dump(), "note": "Apply integration pending"})


@app.command()
def query(
    query_type: str = typer.Option(..., "--type", "-t", help="Query type: nodes, edges, paths"),
    filters: list[str] = typer.Option([], "--filter", "-f", help="Filter conditions (key=value)"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum results"),
    offset: int = typer.Option(0, "--offset", "-o", help="Result offset"),
):
    """
    Query the context graph.

    Queries the AutoFlow context graph for nodes, edges, or paths
    matching the given criteria.

    Example:
        autoflow query --type nodes --filter node_type=function --limit 50
    """
    # Load configuration
    cli_settings = CLISettings.from_env()
    config = _load_config(cli_settings)

    # Parse filters
    filter_dict = {}
    for f in filters:
        if "=" in f:
            k, v = f.split("=", 1)
            filter_dict[k] = v

    # Create request
    request = QueryGraphRequest(
        query_type=query_type,
        filters=filter_dict,
        limit=limit,
        offset=offset,
    )

    # TODO: Actually query the graph
    _print_output({"request": request.model_dump(), "note": "Graph query integration pending"})


@app.command()
def ingest(
    events: str = typer.Option(..., "--events", "-e", help="Events data as JSON string or @file.json"),
):
    """
    Ingest observation events.

    Ingests observation events into AutoFlow for tracking
    and analysis.

    Example:
        autoflow ingest --events @events.json
    """
    import json

    # Load configuration
    cli_settings = CLISettings.from_env()
    config = _load_config(cli_settings)

    # Load events
    if events.startswith("@"):
        with open(events[1:], "r") as f:
            events_data = json.load(f)
    else:
        events_data = json.loads(events)

    # Create request
    request = IngestEventsRequest(events=events_data)

    # TODO: Actually ingest events
    _print_output({"request": request.model_dump(), "note": "Event ingestion integration pending"})


@app.command()
def status(
    include_metrics: bool = typer.Option(False, "--metrics", "-m", help="Include performance metrics"),
    include_config: bool = typer.Option(False, "--config", "-c", help="Include configuration details"),
):
    """
    Get AutoFlow engine status.

    Shows the current status of the AutoFlow engine including
    version, uptime, and optional metrics and configuration.

    Example:
        autoflow status --metrics --config
    """
    # TODO: Actually get status
    _print_output({
        "status": "running",
        "version": "1.0.0",
        "note": "Status integration pending",
        "include_metrics": include_metrics,
        "include_config": include_config,
    })


@app.command()
def config(
    profile: str = typer.Option(None, "--profile", "-p", help="Configuration profile to view"),
    show_secrets: bool = typer.Option(False, "--show-secrets", "-s", help="Show sensitive values"),
):
    """
    Show or manage configuration.

    Displays current configuration or a specific profile's
    configuration. Use --show-secrets to reveal sensitive values.

    Example:
        autoflow config --profile production
        autoflow config --show-secrets
    """
    if profile:
        if profile == "development":
            config_obj = ConfigProfiles.development()
        elif profile == "testing":
            config_obj = ConfigProfiles.testing()
        elif profile == "production":
            config_obj = ConfigProfiles.production()
        elif profile == "serverless":
            config_obj = ConfigProfiles.serverless()
        else:
            typer.echo(f"Unknown profile: {profile}", err=True)
            raise typer.Exit(1)
    else:
        config_obj = get_config()

    # Convert config to dict, optionally hiding secrets
    config_dict = config_obj.model_dump()
    if not show_secrets:
        # Hide sensitive fields
        config_dict = _hide_secrets(config_dict)

    _print_output(config_dict)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
):
    """
    Initialize AutoFlow configuration.

    Creates a default configuration file and sets up the AutoFlow
    workspace directory.

    Example:
        autoflow init
        autoflow init --force
    """
    import yaml

    config_file = "autoflow.yaml"

    if os.path.exists(config_file) and not force:
        typer.echo(f"Configuration file already exists: {config_file}")
        typer.echo("Use --force to overwrite")
        raise typer.Exit(1)

    # Create default configuration
    default_config = {
        "environment": "development",
        "database": {
            "type": "sqlite",
            "path": "./autoflow.db",
        },
        "policy": {
            "max_risk": "medium",
            "dry_run": True,
        },
        "observability": {
            "enabled": True,
        },
        "logging": {
            "level": "INFO",
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False)

    typer.echo(f"✓ Configuration created: {config_file}")
    typer.echo("✓ Run 'autoflow config' to view configuration")


# =============================================================================
# Helper Functions
# =============================================================================


def _load_config(cli_settings: CLISettings) -> AutoFlowConfig:
    """Load AutoFlow configuration based on CLI settings."""
    if cli_settings.config_file:
        # Load from specified file
        config = AutoFlowConfig.from_yaml(cli_settings.config_file)
    elif cli_settings.profile:
        # Load profile
        profile_map = {
            "development": ConfigProfiles.development,
            "testing": ConfigProfiles.testing,
            "production": ConfigProfiles.production,
            "serverless": ConfigProfiles.serverless,
        }
        profile_func = profile_map.get(cli_settings.profile)
        if profile_func:
            config = profile_func()
        else:
            typer.echo(f"Unknown profile: {cli_settings.profile}", err=True)
            raise typer.Exit(1)
    else:
        # Load from environment
        config = get_config()

    # Override with CLI settings
    if cli_settings.db_path:
        config.database.path = cli_settings.db_path
    if cli_settings.otel_endpoint:
        config.observability.otel_exporter_otlp_endpoint = cli_settings.otel_endpoint

    return config


def _print_output(data: dict) -> None:
    """Print output in the requested format."""
    import json

    cli_settings = CLISettings.from_env()
    output_format = cli_settings.output_format

    if output_format == "json":
        typer.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        try:
            import yaml
            typer.echo(yaml.dump(data, default_flow_style=False))
        except ImportError:
            typer.echo("YAML output requires PyYAML: pip install pyyaml", err=True)
            raise typer.Exit(1)
    elif output_format == "text":
        typer.echo(str(data))
    else:
        typer.echo(f"Unknown output format: {output_format}", err=True)
        raise typer.Exit(1)


def _hide_secrets(config_dict: dict) -> dict:
    """Hide sensitive configuration values."""
    secrets = [
        "password",
        "api_key",
        "secret",
        "token",
        "credentials",
        "private_key",
    ]

    def hide_recursive(obj):
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if any(secret in key.lower() for secret in secrets):
                    result[key] = "***HIDDEN***"
                else:
                    result[key] = hide_recursive(value)
            return result
        elif isinstance(obj, list):
            return [hide_recursive(item) for item in obj]
        return obj

    return hide_recursive(config_dict)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
