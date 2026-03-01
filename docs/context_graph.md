# Context Graph Framework

A generic, extensible framework for building knowledge graphs that provide structured context to LLMs.

## Overview

The Context Graph Framework enables you to:
- Build domain-specific knowledge graphs with pluggable modules
- Perform multi-hop traversals for complex reasoning
- Generate LLM-ready context from graph structure
- Integrate with Neo4j or use in-memory storage

## Installation

```bash
# Basic installation
pip install autoflow

# With Neo4j backend
pip install autoflow[neo4j]

# With all optional dependencies
pip install autoflow[all]
```

## Quick Start

```python
from autoflow.context_graph.core import ContextGraph, Entity, Relationship, TraversalPattern
from autoflow.context_graph.backends import InMemoryBackend

# Initialize graph
graph = ContextGraph(backend=InMemoryBackend())

# Create entities
nike = Entity(
    type="brand",
    properties={"name": "Nike", "vertical": "Apparel", "tier": "premium"},
)

adidas = Entity(
    type="brand",
    properties={"name": "Adidas", "vertical": "Apparel", "tier": "premium"},
)

# Add entities
nike_id = graph.add_entity(nike)
adidas_id = graph.add_entity(adidas)

# Create relationships
competitor_rel = Relationship(
    from_entity=nike_id,
    to_entity=adidas_id,
    type="competes_with",
    properties={"intensity": "high"},
)
graph.add_relationship(competitor_rel)

# Traverse the graph
subgraph = graph.traverse(
    start_entity_id=nike_id,
    pattern=TraversalPattern(pattern="-[*]->", max_hops=2),
)

# Get LLM-ready context
context = graph.get_context_for_llm(start_entity_id=nike_id, max_hops=2)
print(context)
```

## Core Concepts

### Entities

Entities represent nodes in your graph - brands, campaigns, users, publishers, etc.

```python
entity = Entity(
    type="brand",  # Entity type
    properties={
        "name": "Nike",
        "vertical": "Apparel",
        "tier": "premium",
    },
)
```

### Relationships

Relationships are directed edges between entities.

```python
relationship = Relationship(
    from_entity="brand:nike",
    to_entity="brand:adidas",
    type="competes_with",
    properties={"intensity": "high"},
    confidence=0.95,  # Optional confidence score
)
```

### Traversals

Multi-hop traversals enable complex reasoning across your graph.

```python
pattern = TraversalPattern(
    pattern="-[:COMPETES_WITH]->(brand)-[:ADVERTISED_ON]->(publisher)",
    max_hops=3,
)

subgraph = graph.traverse(start_entity_id="brand:nike", pattern=pattern)
```

## Domain Modules

Domain modules encapsulate entity types, relationship types, and domain-specific logic.

### Built-in Domains

```python
from autoflow.context_graph.domains.brand import BrandDomain
from autoflow.context_graph.domains.campaign import CampaignDomain
from autoflow.context_graph.domains.publisher import PublisherDomain

# Register domain modules
graph = ContextGraph(
    backend=InMemoryBackend(),
    domains=[BrandDomain(), CampaignDomain(), PublisherDomain()],
)
```

### Creating Custom Domains

```python
from autoflow.context_graph.core import ContextDomain, Entity, Relationship

class TravelDomain(ContextDomain):
    @property
    def name(self) -> str:
        return "travel"

    @property
    def entity_types(self) -> set[str]:
        return {"flight", "airport", "airline"}

    @property
    def relationship_types(self) -> set[str]:
        return {"departed_from", "arrived_at", "serviced_by"}

    def validate_entity(self, entity: Entity) -> bool:
        return entity.type in self.entity_types
```

## Backends

### In-Memory Backend

For testing and development:

```python
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.core import ContextGraph

backend = InMemoryBackend()
graph = ContextGraph(backend=backend)
```

### Neo4j Backend

For production use:

```python
from autoflow.context_graph.backends import Neo4jBackend
from autoflow.context_graph.core import ContextGraph

backend = Neo4jBackend(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your-password",
    database="neo4j",
)
graph = ContextGraph(backend=backend)
```

## LLM Integration

### Graph to Context

Convert graph subgraphs to natural language for LLMs:

```python
from autoflow.context_graph.llm import GraphToContextAssembler

assembler = GraphToContextAssembler(include_paths=True)
context = assembler.subgraph_to_context(subgraph)

# Use in LLM prompt
prompt = f"""
Based on the following context, answer the question:

{context}

Question: Why might Nike's campaign be underperforming?
"""
```

### Natural Language to Cypher

Generate graph queries from natural language:

```python
from autoflow.context_graph.llm import CypherQueryBuilder

builder = CypherQueryBuilder(llm_client=your_llm_client)
query = builder.build_query(
    question="Find all brands that compete with Nike",
    schema={"entity_types": ["Brand"], "relationship_types": ["COMPETES_WITH"]},
)
```

### Entity Extraction

Extract entities and relationships from text:

```python
from autoflow.context_graph.llm import EntityExtractor

extractor = EntityExtractor(
    llm_client=your_llm_client,
    entity_types=["brand", "company"],
    relationship_types=["competes_with", "acquired_by"],
)

text = "Nike acquired RTFKT, a digital fashion company..."
entities, relationships = extractor.extract(text, domain="brand")
```

## Example Use Cases

### Brand Competitive Intelligence

```python
# Find all competitors of a brand
nike = graph.search_by_property("brand", "name", "Nike")[0]
competitors = graph.get_neighbors(nike.id, relationship_type="competes_with")

# Analyze competitor strategies
for competitor, rel in competitors:
    campaigns = graph.get_neighbors(competitor.id, relationship_type="created_by")
    print(f"{competitor.label} has {len(campaigns)} active campaigns")
```

### Campaign Performance Analysis

```python
# Find campaigns that ran on specific publishers
espn = graph.search_by_property("publisher", "name", "ESPN")[0]
campaigns = graph.get_neighbors(espn.id, direction="incoming", relationship_type="ran_on")

# Compare performance
for campaign, rel in campaigns:
    budget = rel.properties.get("spent", 0)
    impressions = rel.properties.get("impressions", 0)
    print(f"{campaign.label}: ${budget:,} spent, {impressions:,} impressions")
```

### Multi-hop Reasoning

```python
# Brand → Campaign → Publisher → Performance
subgraph = graph.traverse(
    start_entity_id="brand:nike",
    pattern=TraversalPattern(
        pattern="-[:CREATED_BY]->(campaign)-[:RAN_ON]->(publisher)",
        max_hops=2,
    ),
)

# Get insights
context = graph.get_context_for_llm(subgraph=subgraph)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Context Graph Framework                │
│  - Entity/Relationship abstractions                     │
│  - Traversal engine                                     │
│  - LLM integration                                      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Brand Module │  │Campaign M.  │  │Publisher M. │
└─────────────┘  └─────────────┘  └─────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                    ┌─────▼─────┐
                    │ Graph DB   │
                    │ (Neo4j/Mem)│
                    └───────────┘
```

## Design Principles

1. **Generic but Extensible**: Core framework works for any domain
2. **Plugin Architecture**: Domain modules add specialized logic
3. **Backend Agnostic**: Switch between storage backends
4. **LLM-First**: Designed for AI agent integration
5. **Explainable**: All traversals leave a reasoning trail

## Running the Demo

```bash
# From the autoflow directory
uv run python examples/context_graph_demo.py
```

This will demonstrate:
- Creating entities and relationships
- Multi-hop traversals
- LLM context assembly
- Property search
- Neighbor queries
