"""
OpenAPI/JSON schema generation utilities for AutoFlow.

This module provides utilities to generate OpenAPI 3.0 schemas
from Pydantic models for API documentation and validation.

Usage:
    from autoflow.schema import generate_openapi_schema, generate_all_schemas

    # Generate schema for a single model
    schema = generate_openapi_schema(ObservationEvent)

    # Generate all AutoFlow schemas
    all_schemas = generate_all_schemas()

    # Export to file
    from autoflow.schema import export_schemas_to_json
    export_schemas_to_json("autoflow_schemas.json")
"""

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue

from autoflow.types_pyantic import (
    ObservationEvent,
    GraphNode,
    GraphEdge,
    ContextGraphDelta,
    ChangeProposal,
    EvaluationResult,
    WorkflowStep,
    WorkflowExecution,
    ContextSource,
)


def generate_openapi_schema(
    model: type[BaseModel],
    title: str = "AutoFlow API",
    version: str = "1.0.0",
    description: str = "AutoFlow engine API schema",
) -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 schema for a Pydantic model.

    Args:
        model: The Pydantic model class
        title: API title
        version: API version
        description: API description

    Returns:
        OpenAPI 3.0 schema as a dictionary

    Example:
        schema = generate_openapi_schema(ObservationEvent)
        print(json.dumps(schema, indent=2))
    """
    # Generate JSON schema for the model
    json_schema = model.model_json_schema()

    # Wrap in OpenAPI 3.0 format
    openapi_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "components": {
            "schemas": {
                model.__name__: json_schema,
            },
        },
    }

    return openapi_schema


def generate_all_schemas(
    title: str = "AutoFlow API",
    version: str = "1.0.0",
    description: str = "AutoFlow engine API - Complete schema for all data models",
) -> Dict[str, Any]:
    """
    Generate OpenAPI 3.0 schemas for all AutoFlow models.

    Args:
        title: API title
        version: API version
        description: API description

    Returns:
        OpenAPI 3.0 schema with all AutoFlow models

    Example:
        all_schemas = generate_all_schemas()
        with open("autoflow_openapi.json", "w") as f:
            json.dump(all_schemas, f, indent=2)
    """
    models = [
        ObservationEvent,
        GraphNode,
        GraphEdge,
        ContextGraphDelta,
        ChangeProposal,
        EvaluationResult,
        WorkflowStep,
        WorkflowExecution,
        ContextSource,
    ]

    schemas = {}

    for model in models:
        try:
            json_schema = model.model_json_schema()
            schemas[model.__name__] = json_schema
        except Exception as e:
            # Skip models that fail to generate schema
            print(f"Warning: Failed to generate schema for {model.__name__}: {e}")

    openapi_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "components": {
            "schemas": schemas,
        },
    }

    return openapi_schema


def export_schemas_to_json(
    output_path: str = "autoflow_schemas.json",
    pretty: bool = True,
) -> None:
    """
    Export all AutoFlow schemas to a JSON file.

    Args:
        output_path: Path to the output JSON file
        pretty: Whether to format JSON with indentation

    Example:
        export_schemas_to_json("docs/api_schemas.json")
    """
    schemas = generate_all_schemas()

    with open(output_path, "w") as f:
        if pretty:
            json.dump(schemas, f, indent=2)
        else:
            json.dump(schemas, f)

    print(f"✓ Schemas exported to {output_path}")


def export_schemas_to_yaml(
    output_path: str = "autoflow_schemas.yaml",
) -> None:
    """
    Export all AutoFlow schemas to a YAML file.

    Requires PyYAML to be installed.

    Args:
        output_path: Path to the output YAML file

    Example:
        export_schemas_to_yaml("docs/api_schemas.yaml")
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML required: pip install pyyaml")

    schemas = generate_all_schemas()

    with open(output_path, "w") as f:
        yaml.dump(schemas, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Schemas exported to {output_path}")


def generate_schema_markdown(
    output_path: str = "docs/api_schemas.md",
) -> None:
    """
    Generate Markdown documentation for all schemas.

    Args:
        output_path: Path to the output Markdown file

    Example:
        generate_schema_markdown("docs/api_reference.md")
    """
    models = [
        (ObservationEvent, "Observation Event", "An event captured during AutoFlow operation"),
        (GraphNode, "Graph Node", "A node in the context graph"),
        (GraphEdge, "Graph Edge", "An edge in the context graph"),
        (ContextGraphDelta, "Context Graph Delta", "Changes to apply to the context graph"),
        (ChangeProposal, "Change Proposal", "A proposed change to the codebase"),
        (EvaluationResult, "Evaluation Result", "Result of evaluating a change proposal"),
        (WorkflowStep, "Workflow Step", "A single step in a workflow"),
        (WorkflowExecution, "Workflow Execution", "A complete workflow execution"),
        (ContextSource, "Context Source", "A source of context information"),
    ]

    lines = [
        "# AutoFlow API Schemas",
        "",
        "This document provides the schema definitions for all AutoFlow data models.",
        "",
        "---",
        "",
    ]

    for model, name, description in models:
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"{description}")
        lines.append("")
        lines.append("### Fields")
        lines.append("")

        schema = model.model_json_schema()
        if "properties" in schema:
            for field_name, field_info in schema["properties"].items():
                required = field_name in schema.get("required", [])
                req_marker = "**(required)**" if required else ""

                lines.append(f"- `{field_name}` {req_marker}")
                if "description" in field_info:
                    lines.append(f"  - {field_info['description']}")
                if "title" in field_info:
                    lines.append(f"  - **Type:** {field_info['title']}")
                elif "type" in field_info:
                    lines.append(f"  - **Type:** {field_info['type']}")
                lines.append("")

        lines.append("---")
        lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✓ Schema documentation exported to {output_path}")


def get_model_examples(model: type[BaseModel]) -> Dict[str, Any]:
    """
    Get example data for a model.

    Returns a dictionary of example instances for the model.

    Args:
        model: The Pydantic model class

    Returns:
        Dictionary with example data

    Example:
        examples = get_model_examples(ObservationEvent)
        print(examples["basic"])
    """
    examples = {}

    if model == ObservationEvent:
        examples["basic"] = {
            "source": "autoflow_engine",
            "name": "proposal_generated",
            "attributes": {"proposal_count": 3},
        }
        examples["with_custom_id"] = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "source": "evaluator",
            "name": "evaluation_complete",
            "attributes": {"score": 0.85, "passed": True},
        }

    elif model == ChangeProposal:
        examples["basic"] = {
            "kind": "text_patch",
            "title": "Fix typo in README",
            "description": "Fix spelling error in README.md",
            "risk": "low",
            "target_paths": ["README.md"],
            "payload": {
                "file": "README.md",
                "line": 42,
                "old": "recieve",
                "new": "receive",
            },
        }

    elif model == GraphNode:
        examples["function_node"] = {
            "node_id": "func_process_data",
            "node_type": "function",
            "properties": {
                "name": "process_data",
                "file": "src/process.py",
                "line": 10,
            },
        }

    elif model == EvaluationResult:
        examples["passing"] = {
            "proposal_id": "prop_123",
            "passed": True,
            "score": 85.0,
            "metrics": {
                "test_coverage": 0.9,
                "performance_improvement": 0.15,
            },
            "notes": "All checks passed",
        }

    elif model == WorkflowExecution:
        examples["basic"] = {
            "name": "test_workflow",
            "status": "running",
            "steps": [],
        }

    return examples


# Convenience exports
__all__ = [
    "generate_openapi_schema",
    "generate_all_schemas",
    "export_schemas_to_json",
    "export_schemas_to_yaml",
    "generate_schema_markdown",
    "get_model_examples",
]
