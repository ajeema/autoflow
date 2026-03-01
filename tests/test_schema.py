"""Tests for schema generation utilities."""

import json
from pathlib import Path

import pytest

from autoflow.schema import (
    generate_openapi_schema,
    generate_all_schemas,
    get_model_examples,
    export_schemas_to_json,
)
from autoflow.types_pyantic import (
    ObservationEvent,
    ChangeProposal,
    GraphNode,
    EvaluationResult,
)


class TestSchemaGeneration:
    """Test schema generation."""

    def test_generate_openapi_schema_for_event(self):
        """Test generating OpenAPI schema for ObservationEvent."""
        schema = generate_openapi_schema(ObservationEvent)
        assert schema["openapi"] == "3.0.0"
        assert "info" in schema
        assert "components" in schema
        assert "ObservationEvent" in schema["components"]["schemas"]

    def test_generate_all_schemas(self):
        """Test generating schemas for all models."""
        schemas = generate_all_schemas()
        assert "ObservationEvent" in schemas["components"]["schemas"]
        assert "ChangeProposal" in schemas["components"]["schemas"]
        assert "GraphNode" in schemas["components"]["schemas"]

    def test_schema_has_required_fields(self):
        """Test that required fields are marked in schema."""
        schema = generate_openapi_schema(ObservationEvent)
        event_schema = schema["components"]["schemas"]["ObservationEvent"]
        assert "required" in event_schema
        # source and name should be required
        assert "source" in event_schema["required"]
        assert "name" in event_schema["required"]


class TestModelExamples:
    """Test model example generation."""

    def test_get_examples_for_event(self):
        """Test getting examples for ObservationEvent."""
        examples = get_model_examples(ObservationEvent)
        assert "basic" in examples
        assert "source" in examples["basic"]
        assert "name" in examples["basic"]

    def test_get_examples_for_proposal(self):
        """Test getting examples for ChangeProposal."""
        examples = get_model_examples(ChangeProposal)
        assert "basic" in examples
        assert "title" in examples["basic"]
        assert "risk" in examples["basic"]

    def test_get_examples_for_unknown_model(self):
        """Test getting examples for model without predefined examples."""
        examples = get_model_examples(GraphNode)
        # Should return empty dict if no examples defined
        assert isinstance(examples, dict)


class TestSchemaExport:
    """Test schema export functionality."""

    def test_export_to_json(self, tmp_path):
        """Test exporting schemas to JSON."""
        output_file = tmp_path / "test_schemas.json"
        export_schemas_to_json(str(output_file))
        assert output_file.exists()

        # Verify valid JSON
        with open(output_file) as f:
            data = json.load(f)
        assert "openapi" in data

    def test_export_to_json_compact(self, tmp_path):
        """Test exporting schemas to JSON without pretty printing."""
        output_file = tmp_path / "test_schemas_compact.json"
        export_schemas_to_json(str(output_file), pretty=False)
        assert output_file.exists()

    def test_export_to_yaml(self, tmp_path):
        """Test exporting schemas to YAML."""
        pytest.importorskip("yaml")
        from autoflow.schema import export_schemas_to_yaml

        output_file = tmp_path / "test_schemas.yaml"
        export_schemas_to_yaml(str(output_file))
        assert output_file.exists()
