"""
Context Graph Framework Demo

This example demonstrates how to use the Context Graph Framework
to build a knowledge graph for brand intelligence and campaign optimization.
"""

from autoflow.context_graph.core import ContextGraph, Entity, Relationship, TraversalPattern
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.domains.brand import BrandDomain
from autoflow.context_graph.llm import GraphToContextAssembler


def main():
    """Run a simple demo of the Context Graph Framework."""
    print("=== Context Graph Framework Demo ===\n")

    # Initialize graph with in-memory backend (for demo)
    # In production, use Neo4jBackend(uri="bolt://localhost:7687", ...)
    graph = ContextGraph(backend=InMemoryBackend(), domains=[BrandDomain()])

    # Create brand entities
    nike = Entity(
        type="brand",
        properties={
            "name": "Nike",
            "vertical": "Apparel",
            "tier": "premium",
            "description": "Athletic footwear and apparel",
        },
    )

    adidas = Entity(
        type="brand",
        properties={
            "name": "Adidas",
            "vertical": "Apparel",
            "tier": "premium",
            "description": "German sportswear company",
        },
    )

    under_armour = Entity(
        type="brand",
        properties={
            "name": "Under Armour",
            "vertical": "Apparel",
            "tier": "mid_market",
            "description": "American sports clothing brand",
        },
    )

    # Create publisher entities
    espn = Entity(
        type="publisher",
        properties={
            "name": "ESPN",
            "domain": "espn.com",
            "category": "Sports",
            "monthly_visitors": 50000000,
            "quality_score": 0.9,
        },
    )

    # Create campaign entity
    summer_campaign = Entity(
        type="campaign",
        properties={
            "name": "Summer 2024",
            "budget": 50000,
            "goal": "conversions",
            "status": "active",
        },
    )

    # Add entities to graph
    print("Adding entities to graph...")
    nike_id = graph.add_entity(nike)
    adidas_id = graph.add_entity(adidas)
    ua_id = graph.add_entity(under_armour)
    espn_id = graph.add_entity(espn)
    campaign_id = graph.add_entity(summer_campaign)

    print(f"  Added: {nike.label}")
    print(f"  Added: {adidas.label}")
    print(f"  Added: {under_armour.label}")
    print(f"  Added: {espn.label}")
    print(f"  Added: {summer_campaign.label}\n")

    # Create relationships
    print("Adding relationships to graph...")

    # Competitive relationships
    nike_adidas = Relationship(
        from_entity=nike_id,
        to_entity=adidas_id,
        type="competes_with",
        properties={"intensity": "high", "basis": "same vertical"},
    )
    nike_ua = Relationship(
        from_entity=nike_id,
        to_entity=ua_id,
        type="competes_with",
        properties={"intensity": "medium"},
    )

    # Campaign-brand relationship
    campaign_brand = Relationship(
        from_entity=campaign_id,
        to_entity=nike_id,
        type="created_by",
    )

    # Campaign-publisher relationship
    campaign_publisher = Relationship(
        from_entity=campaign_id,
        to_entity=espn_id,
        type="ran_on",
        properties={"spent": 25000, "impressions": 1500000},
    )

    graph.add_relationship(nike_adidas)
    graph.add_relationship(nike_ua)
    graph.add_relationship(campaign_brand)
    graph.add_relationship(campaign_publisher)

    print("  Added: Nike competes_with Adidas (high intensity)")
    print("  Added: Nike competes_with Under Armour (medium intensity)")
    print("  Added: Summer 2024 created_by Nike")
    print("  Added: Summer 2024 ran_on ESPN\n")

    # Demonstrate traversal
    print("=== Multi-hop Traversal ===\n")

    subgraph = graph.traverse(
        start_entity_id=nike_id,
        pattern=TraversalPattern(pattern="-[*]->", max_hops=2),
    )

    print(f"Traversal found {len(subgraph.entities)} entities and {len(subgraph.relationships)} relationships:\n")

    for entity_id, entity in subgraph.entities.items():
        print(f"  Entity: {entity.label} ({entity.type})")

    print()

    for rel in subgraph.relationships:
        from_entity = subgraph.entities.get(rel.from_entity)
        to_entity = subgraph.entities.get(rel.to_entity)
        if from_entity and to_entity:
            print(f"  Relationship: {from_entity.label} → {rel.type} → {to_entity.label}")

    # Demonstrate LLM context assembly
    print("\n=== LLM Context Assembly ===\n")
    assembler = GraphToContextAssembler(include_paths=True, include_properties=True)
    context = assembler.subgraph_to_context(subgraph)
    print(context)

    # Demonstrate search
    print("\n=== Property Search ===\n")

    results = graph.search_by_property(entity_type="brand", property_name="tier", property_value="premium")
    print(f"Found {len(results)} premium brands:")
    for brand in results:
        print(f"  - {brand.label}")

    # Demonstrate getting neighbors
    print("\n=== Neighbor Query ===\n")

    neighbors = graph.get_neighbors(nike_id, relationship_type="competes_with")
    print(f"Nike has {len(neighbors)} competitors:")
    for neighbor, rel in neighbors:
        intensity = rel.properties.get("intensity", "unknown") if rel else "unknown"
        print(f"  - {neighbor.label} (intensity: {intensity})")

    # Get context for LLM
    print("\n=== Get LLM Context ===\n")

    llm_context = graph.get_context_for_llm(
        start_entity_id=nike_id,
        max_hops=2,
        include_paths=True,
    )
    print(llm_context)

    # Close connection
    graph.close()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
