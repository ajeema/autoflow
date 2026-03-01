"""
Test fixtures and factory functions for Context Graph testing.

Provides utilities for creating test entities, relationships, and sample graphs
to reduce boilerplate in tests and examples.
"""

from typing import Any, Optional

from autoflow.context_graph.core import (
    ContextGraph,
    Entity,
    Relationship,
    Subgraph,
)
from autoflow.context_graph.backends import InMemoryBackend


class GraphFixtures:
    """Factory for creating test entities and relationships."""

    @staticmethod
    def brand(name: str = "Nike", **props: Any) -> Entity:
        """
        Create a test brand entity.

        Args:
            name: Brand name
            **props: Additional properties

        Returns:
            Brand entity
        """
        default_props = {"vertical": "Apparel", "tier": "premium"}
        default_props.update(props)
        return Entity(type="brand", properties={"name": name, **default_props})

    @staticmethod
    def company(name: str = "Nike Inc", **props: Any) -> Entity:
        """
        Create a test company entity.

        Args:
            name: Company name
            **props: Additional properties

        Returns:
            Company entity
        """
        default_props = {"industry": "Apparel", "employees": 10000}
        default_props.update(props)
        return Entity(type="company", properties={"name": name, **default_props})

    @staticmethod
    def campaign(name: str = "Summer 2024", **props: Any) -> Entity:
        """
        Create a test campaign entity.

        Args:
            name: Campaign name
            **props: Additional properties

        Returns:
            Campaign entity
        """
        default_props = {"status": "active", "budget": 10000}
        default_props.update(props)
        return Entity(type="campaign", properties={"name": name, **default_props})

    @staticmethod
    def creative(name: str = "Banner Ad", **props: Any) -> Entity:
        """
        Create a test creative entity.

        Args:
            name: Creative name
            **props: Additional properties

        Returns:
            Creative entity
        """
        default_props = {"format": "display", "has_cta": True}
        default_props.update(props)
        return Entity(type="creative", properties={"name": name, **default_props})

    @staticmethod
    def publisher(name: str = "ESPN", **props: Any) -> Entity:
        """
        Create a test publisher entity.

        Args:
            name: Publisher name
            **props: Additional properties

        Returns:
            Publisher entity
        """
        default_props = {"category": "Sports", "tier": "premium"}
        default_props.update(props)
        return Entity(type="publisher", properties={"name": name, **default_props})

    @staticmethod
    def vertical(name: str = "Apparel", **props: Any) -> Entity:
        """
        Create a test vertical entity.

        Args:
            name: Vertical name
            **props: Additional properties

        Returns:
            Vertical entity
        """
        default_props = {"description": f"{name} industry vertical"}
        default_props.update(props)
        return Entity(type="vertical", properties={"name": name, **default_props})

    @staticmethod
    def competes_with(
        brand1: str, brand2: str, intensity: str = "medium", **props: Any
    ) -> Relationship:
        """
        Create a test competitive relationship.

        Args:
            brand1: First brand ID or name
            brand2: Second brand ID or name
            intensity: Competition intensity (low, medium, high)
            **props: Additional properties

        Returns:
            Competitor relationship
        """
        properties = {"intensity": intensity}
        properties.update(props)

        return Relationship(
            from_entity=brand1 if ":" in brand1 else f"brand:{brand1.lower()}",
            to_entity=brand2 if ":" in brand2 else f"brand:{brand2.lower()}",
            type="competes_with",
            properties=properties,
        )

    @staticmethod
    def created_by(campaign: str, brand: str, **props: Any) -> Relationship:
        """
        Create a campaign-to-brand relationship.

        Args:
            campaign: Campaign ID or name
            brand: Brand ID or name
            **props: Additional properties

        Returns:
            Created by relationship
        """
        return Relationship(
            from_entity=campaign if ":" in campaign else f"campaign:{campaign.lower()}",
            to_entity=brand if ":" in brand else f"brand:{brand.lower()}",
            type="created_by",
            properties=props,
        )

    @staticmethod
    def ran_on(campaign: str, publisher: str, **props: Any) -> Relationship:
        """
        Create a campaign-to-publisher relationship.

        Args:
            campaign: Campaign ID or name
            publisher: Publisher ID or name
            **props: Additional properties

        Returns:
            Ran on relationship
        """
        return Relationship(
            from_entity=campaign if ":" in campaign else f"campaign:{campaign.lower()}",
            to_entity=publisher if ":" in publisher else f"publisher:{publisher.lower()}",
            type="ran_on",
            properties=props,
        )

    @staticmethod
    def sample_graph(size: str = "small") -> ContextGraph:
        """
        Create a sample graph for testing.

        Args:
            size: Graph size - "small", "medium", or "large"

        Returns:
            ContextGraph with sample data
        """
        graph = ContextGraph(backend=InMemoryBackend())

        if size == "small":
            GraphFixtures._populate_small_graph(graph)
        elif size == "medium":
            GraphFixtures._populate_small_graph(graph)
            GraphFixtures._populate_medium_graph(graph)
        elif size == "large":
            GraphFixtures._populate_small_graph(graph)
            GraphFixtures._populate_medium_graph(graph)
            GraphFixtures._populate_large_graph(graph)

        return graph

    @staticmethod
    def _populate_small_graph(graph: ContextGraph) -> None:
        """Populate a small graph with 3 brands and a few relationships."""
        entities = [
            GraphFixtures.brand("Nike"),
            GraphFixtures.brand("Adidas"),
            GraphFixtures.brand("Under Armour"),
        ]

        for e in entities:
            graph.add_entity(e)

        relationships = [
            GraphFixtures.competes_with("brand:nike", "brand:adidas", "high"),
            GraphFixtures.competes_with("brand:nike", "brand:under_armour", "medium"),
        ]

        for r in relationships:
            graph.add_relationship(r)

    @staticmethod
    def _populate_medium_graph(graph: ContextGraph) -> None:
        """Add medium-sized expansion (campaigns, publishers)."""
        entities = [
            GraphFixtures.campaign("Summer 2024", budget=50000),
            GraphFixtures.creative("Banner Ad 1", format="display"),
            GraphFixtures.publisher("ESPN"),
            GraphFixtures.publisher("CNN"),
        ]

        for e in entities:
            graph.add_entity(e)

        relationships = [
            GraphFixtures.created_by("campaign:summer 2024", "brand:nike"),
            GraphFixtures.ran_on("campaign:summer 2024", "publisher:espn"),
        ]

        for r in relationships:
            graph.add_relationship(r)

    @staticmethod
    def _populate_large_graph(graph: ContextGraph) -> None:
        """Add large expansion (many brands, verticals)."""
        verticals = ["Apparel", "Electronics", "Automotive", "Food & Beverage"]

        for vertical in verticals:
            graph.add_entity(GraphFixtures.vertical(vertical))

        brands = [
            ("Sony", "Electronics"),
            ("Samsung", "Electronics"),
            ("Toyota", "Automotive"),
            ("Ford", "Automotive"),
            ("Coke", "Food & Beverage"),
        ]

        for brand_name, vertical in brands:
            brand = GraphFixtures.brand(brand_name, vertical=vertical)
            graph.add_entity(brand)
            graph.add_entity(
                Relationship(
                    from_entity=f"brand:{brand_name.lower()}",
                    to_entity=f"vertical:{vertical.lower()}",
                    type="in_vertical",
                )
            )


def create_test_graph(**entities: dict[str, dict[str, Any]]) -> ContextGraph:
    """
    Create a test graph from a simple dict specification.

    Args:
        **entities: Entity specifications
            Key is entity name, value is dict with "type" and "properties"

    Example:
        graph = create_test_graph(
            nike={"type": "brand", "properties": {"name": "Nike", "vertical": "Apparel"}},
            adidas={"type": "brand", "properties": {"name": "Adidas"}},
        )

    Returns:
        ContextGraph with the entities
    """
    graph = ContextGraph(backend=InMemoryBackend())

    for name, spec in entities.items():
        entity = Entity(
            id=spec.get("id", f"{spec['type']}:{name.lower()}"),
            type=spec["type"],
            properties={"name": name, **spec.get("properties", {})},
        )
        graph.add_entity(entity)

    return graph


def make_entity(entity_type: str, name: str, **props: Any) -> Entity:
    """
    Quick helper to create an entity with a name.

    Args:
        entity_type: Type of entity
        name: Entity name
        **props: Additional properties

    Returns:
        Entity instance
    """
    return Entity(
        type=entity_type,
        properties={"name": name, **props},
    )


def make_relationship(
    from_name: str,
    to_name: str,
    rel_type: str,
    from_type: str = "entity",
    to_type: str = "entity",
    **props: Any,
) -> Relationship:
    """
    Quick helper to create a relationship.

    Args:
        from_name: Source entity name
        to_name: Target entity name
        rel_type: Relationship type
        from_type: Source entity type
        to_type: Target entity type
        **props: Additional properties

    Returns:
        Relationship instance
    """
    return Relationship(
        from_entity=f"{from_type}:{from_name.lower()}",
        to_entity=f"{to_type}:{to_name.lower()}",
        type=rel_type,
        properties=props,
    )
