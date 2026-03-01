"""
Builder classes for creating Context Graph entities and relationships.

Provides fluent interfaces for constructing entities and relationships
with less boilerplate and better type safety.
"""

from typing import Any, Optional

from autoflow.context_graph.core import Entity, Relationship


class EntityBuilder:
    """
    Fluent builder for Entity creation.

    Provides a more readable way to create entities with method chaining.

    Example:
        ```python
        nike = (EntityBuilder("brand")
            .with_name("Nike")
            .with_property("vertical", "Apparel")
            .with_property("tier", "premium")
            .with_id("brand:nike")
            .build())
        ```
    """

    def __init__(self, entity_type: str) -> None:
        """
        Initialize builder for an entity type.

        Args:
            entity_type: The entity type (e.g., "brand", "campaign")
        """
        self._type = entity_type
        self._properties: dict[str, Any] = {}
        self._id: Optional[str] = None
        self._embedding: Optional[list[float]] = None

    def with_id(self, entity_id: str) -> "EntityBuilder":
        """
        Set the entity ID.

        Args:
            entity_id: Unique entity ID

        Returns:
            self for chaining
        """
        self._id = entity_id
        return self

    def with_name(self, name: str) -> "EntityBuilder":
        """
        Set the entity name (convenience for properties["name"]).

        Args:
            name: Entity name

        Returns:
            self for chaining
        """
        self._properties["name"] = name
        return self

    def with_property(self, key: str, value: Any) -> "EntityBuilder":
        """
        Set a single property.

        Args:
            key: Property key
            value: Property value

        Returns:
            self for chaining
        """
        self._properties[key] = value
        return self

    def with_properties(self, **properties: Any) -> "EntityBuilder":
        """
        Set multiple properties at once.

        Args:
            **properties: Keyword arguments of properties

        Returns:
            self for chaining
        """
        self._properties.update(properties)
        return self

    def with_embedding(self, embedding: list[float]) -> "EntityBuilder":
        """
        Set the vector embedding.

        Args:
            embedding: Vector embedding for semantic search

        Returns:
            self for chaining
        """
        self._embedding = embedding
        return self

    def build(self) -> Entity:
        """
        Build and return the Entity.

        Returns:
            Constructed Entity instance

        Raises:
            ValueError: If entity type is empty
        """
        kwargs: dict[str, Any] = {
            "type": self._type,
            "properties": self._properties,
        }

        if self._id is not None:
            kwargs["id"] = self._id

        if self._embedding is not None:
            kwargs["embedding"] = self._embedding

        return Entity(**kwargs)


class RelationshipBuilder:
    """
    Fluent builder for Relationship creation.

    Example:
        ```python
        rel = (RelationshipBuilder()
            .from_entity("brand:nike")
            .to_entity("brand:adidas")
            .with_type("competes_with")
            .with_property("intensity", "high")
            .with_confidence(0.9)
            .build())
        ```
    """

    def __init__(self) -> None:
        """Initialize relationship builder."""
        self._from: Optional[str] = None
        self._to: Optional[str] = None
        self._rel_type: Optional[str] = None
        self._properties: dict[str, Any] = {}
        self._confidence: Optional[float] = None

    def from_entity(self, entity_id: str) -> "RelationshipBuilder":
        """
        Set the source entity.

        Args:
            entity_id: Source entity ID

        Returns:
            self for chaining
        """
        self._from = entity_id
        return self

    def to_entity(self, entity_id: str) -> "RelationshipBuilder":
        """
        Set the target entity.

        Args:
            entity_id: Target entity ID

        Returns:
            self for chaining
        """
        self._to = entity_id
        return self

    def with_type(self, rel_type: str) -> "RelationshipBuilder":
        """
        Set the relationship type.

        Args:
            rel_type: Relationship type (e.g., "competes_with")

        Returns:
            self for chaining
        """
        self._rel_type = rel_type
        return self

    def with_property(self, key: str, value: Any) -> "RelationshipBuilder":
        """
        Set a relationship property.

        Args:
            key: Property key
            value: Property value

        Returns:
            self for chaining
        """
        self._properties[key] = value
        return self

    def with_properties(self, **properties: Any) -> "RelationshipBuilder":
        """
        Set multiple properties at once.

        Args:
            **properties: Keyword arguments of properties

        Returns:
            self for chaining
        """
        self._properties.update(properties)
        return self

    def with_confidence(self, confidence: float) -> "RelationshipBuilder":
        """
        Set the confidence score.

        Args:
            confidence: Confidence value between 0.0 and 1.0

        Returns:
            self for chaining
        """
        self._confidence = confidence
        return self

    def build(self) -> Relationship:
        """
        Build and return the Relationship.

        Returns:
            Constructed Relationship instance

        Raises:
            ValueError: If required fields are missing
        """
        if not self._from:
            raise ValueError("Relationship must have a 'from' entity")
        if not self._to:
            raise ValueError("Relationship must have a 'to' entity")
        if not self._rel_type:
            raise ValueError("Relationship must have a type")

        kwargs: dict[str, Any] = {
            "from_entity": self._from,
            "to_entity": self._to,
            "type": self._rel_type,
            "properties": self._properties,
        }

        if self._confidence is not None:
            kwargs["confidence"] = self._confidence

        return Relationship(**kwargs)


def brand(name: str, **properties: Any) -> Entity:
    """
    Quick builder for brand entities.

    Args:
        name: Brand name
        **properties: Additional properties

    Returns:
        Brand entity
    """
    return (
        EntityBuilder("brand")
        .with_name(name)
        .with_properties(**properties)
        .build()
    )


def campaign(name: str, **properties: Any) -> Entity:
    """
    Quick builder for campaign entities.

    Args:
        name: Campaign name
        **properties: Additional properties

    Returns:
        Campaign entity
    """
    return (
        EntityBuilder("campaign")
        .with_name(name)
        .with_properties(**properties)
        .build()
    )


def publisher(name: str, **properties: Any) -> Entity:
    """
    Quick builder for publisher entities.

    Args:
        name: Publisher name
        **properties: Additional properties

    Returns:
        Publisher entity
    """
    return (
        EntityBuilder("publisher")
        .with_name(name)
        .with_properties(**properties)
        .build()
    )


def competes_with(
    brand1: str, brand2: str, intensity: str = "medium", **properties: Any
) -> Relationship:
    """
    Quick builder for competitive relationships.

    Args:
        brand1: First brand ID or name
        brand2: Second brand ID or name
        intensity: Competition intensity (default: "medium")
        **properties: Additional properties

    Returns:
        Competitor relationship
    """
    return (
        RelationshipBuilder()
        .from_entity(brand1 if ":" in brand1 else f"brand:{brand1.lower()}")
        .to_entity(brand2 if ":" in brand2 else f"brand:{brand2.lower()}")
        .with_type("competes_with")
        .with_property("intensity", intensity)
        .with_properties(**properties)
        .build()
    )
