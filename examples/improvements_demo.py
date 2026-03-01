"""
Demo of the new Context Graph Framework improvements.

This example demonstrates:
- Entity and relationship builders
- Batch operations
- Configuration profiles
- Test fixtures
- Metrics tracking
- Query validation
"""

from autoflow.context_graph.core import ContextGraph, Entity, Relationship
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.security import SecurityConfig, Validator
from autoflow.context_graph.builders import (
    EntityBuilder,
    RelationshipBuilder,
    brand,
    campaign,
    publisher,
    competes_with,
)
from autoflow.context_graph.testing import GraphFixtures
from autoflow.context_graph.metrics import track_operation
from autoflow.context_graph.llm import CypherQueryBuilder

print("=" * 60)
print("Context Graph Framework - Improvements Demo")
print("=" * 60)

# ============================================================================
# 1. Entity Builder Pattern
# ============================================================================
print("\n=== 1. Entity Builder Pattern ===")

nike = (
    EntityBuilder("brand")
    .with_name("Nike")
    .with_property("vertical", "Apparel")
    .with_property("tier", "premium")
    .with_id("brand:nike")
    .build()
)
print(f"Created entity: {nike.id} - {nike.label}")

# Quick helper functions
adidas = brand("Adidas", vertical="Apparel", tier="premium")
espn = publisher("ESPN", category="Sports")
print(f"Quick brand: {adidas.label}")
print(f"Quick publisher: {espn.label}")

# ============================================================================
# 2. Relationship Builder Pattern
# ============================================================================
print("\n=== 2. Relationship Builder Pattern ===")

rel = (
    RelationshipBuilder()
    .from_entity("brand:nike")
    .to_entity("brand:adidas")
    .with_type("competes_with")
    .with_property("intensity", "high")
    .with_confidence(0.9)
    .build()
)
print(f"Relationship: {rel.from_entity} -> {rel.to_entity} (confidence: {rel.confidence})")

# Quick helper
comp_rel = competes_with("Nike", "Adidas", intensity="high")
print(f"Quick relationship: {comp_rel.from_entity} -> {comp_rel.to_entity}")

# ============================================================================
# 3. Batch Operations
# ============================================================================
print("\n=== 3. Batch Operations ===")

graph = ContextGraph(backend=InMemoryBackend())

# Batch add entities
entities = [
    brand("Nike", vertical="Apparel"),
    brand("Adidas", vertical="Apparel"),
    brand("Under Armour", vertical="Apparel"),
    publisher("ESPN"),
    publisher("CNN"),
]
ids = graph.add_entities(entities)
print(f"Added {len(ids)} entities in batch: {ids}")

# Batch add relationships
relationships = [
    competes_with("Nike", "Adidas", "high"),
    competes_with("Nike", "Under Armour", "medium"),
]
rel_ids = graph.add_relationships(relationships)
print(f"Added {len(rel_ids)} relationships in batch")

# ============================================================================
# 4. Configuration Profiles
# ============================================================================
print("\n=== 4. Configuration Profiles ===")

dev_config = SecurityConfig.development()
print(f"Development config: validation={dev_config.enable_validation}")

test_config = SecurityConfig.testing()
print(f"Testing config: max_hops={test_config.max_hops}")

prod_config = SecurityConfig.production()
print(f"Production config: max_hops={prod_config.max_hops}")

# ============================================================================
# 5. Test Fixtures
# ============================================================================
print("\n=== 5. Test Fixtures ===")

sample_graph = GraphFixtures.sample_graph(size="small")
print(f"Sample graph has {len(sample_graph._backend._entities)} entities")

# Get an entity
nike_entity = sample_graph.get_entity("brand:nike")
if nike_entity:
    print(f"Found entity: {nike_entity.label}")

# ============================================================================
# 6. Metrics Tracking
# ============================================================================
print("\n=== 6. Metrics Tracking ===")

# Manual timing
with track_operation("batch_insert") as metrics:
    # Do some work
    entities = [brand(f"Brand{i}", vertical="Test") for i in range(5)]
    graph.add_entities(entities)

print(f"Operation took: {metrics['duration_ms']:.2f}ms")
print(f"Success: {metrics['success']}")

# ============================================================================
# 7. Schema Validation
# ============================================================================
print("\n=== 7. Schema Validation ===")

validator = Validator()

# Define a schema for brands
schemas = {
    "brand": {
        "name": (str, True),  # Required string
        "tier": (str, False, ["premium", "basic", "mid_market"]),  # Optional with choices
        "vertical": (str, False),  # Optional string
    }
}

# Valid properties
valid_props = validator.validate_property_schema(
    "brand",
    {"name": "Nike", "tier": "premium", "vertical": "Apparel"},
    schemas,
)
print(f"Valid properties: {valid_props}")

# Try with invalid tier (will raise ValueError in production)
try:
    invalid_props = validator.validate_property_schema(
        "brand",
        {"name": "Nike", "tier": "invalid_tier"},
        schemas,
    )
except ValueError as e:
    print(f"Schema validation caught: {e}")

# ============================================================================
# 8. Query Validation
# ============================================================================
print("\n=== 8. Query Validation ===")

builder = CypherQueryBuilder()

# Safe query
safe_query = "MATCH (b:Brand) RETURN b LIMIT 10"
print(f"Safe query valid: {builder.validate_query(safe_query)}")

# Dangerous query
dangerous_query = "DROP DATABASE graph"
print(f"Dangerous query valid: {builder.validate_query(dangerous_query)}")

# Missing LIMIT
long_query = "MATCH (a)-[r*10..20]-(b) RETURN a, b"
print(f"Long query without LIMIT valid: {builder.validate_query(long_query)}")

print("\n" + "=" * 60)
print("All improvements demonstrated successfully!")
print("=" * 60)
