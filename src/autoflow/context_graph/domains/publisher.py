"""
Publisher domain module for the Context Graph Framework.

This module handles publisher and inventory context, including:
- Publisher and domain entities
- Content categorization
- Audience demographics
- Brand safety and quality metrics
"""

from typing import Any, Optional

from autoflow.context_graph.core import ContextDomain, Entity, Relationship


class PublisherDomain(ContextDomain):
    """
    Domain module for publisher and inventory intelligence.

    Entity types:
    - publisher: Publisher entities (ESPN, NYT, etc.)
    - domain: Web domains
    - inventory_category: Inventory classifications

    Relationship types:
    - categorized_as: Domain → category
    - has_audience: Publisher → demographic
    - safe_for: Brand safety classification
    - owned_by: Publisher ownership
    """

    def __init__(self) -> None:
        """Initialize the Publisher domain."""
        self._entity_types = {"publisher", "domain", "inventory_category"}
        self._relationship_types = {
            "categorized_as",
            "has_audience",
            "safe_for",
            "owned_by",
            "mentions_brand",
            "contextual_topic",
        }

    @property
    def name(self) -> str:
        """Domain name."""
        return "publisher"

    @property
    def entity_types(self) -> set[str]:
        """Entity types this domain handles."""
        return self._entity_types

    @property
    def relationship_types(self) -> set[str]:
        """Relationship types this domain handles."""
        return self._relationship_types

    def validate_entity(self, entity: Entity) -> bool:
        """
        Validate a publisher domain entity.

        Required properties:
        - publisher: name (required), domain (optional)
        - domain: name (required)
        - inventory_category: name (required)
        """
        if entity.type not in self._entity_types:
            return False

        if entity.type == "publisher":
            return "name" in entity.properties
        elif entity.type == "domain":
            return "name" in entity.properties
        elif entity.type == "inventory_category":
            return "name" in entity.properties

        return False

    def validate_relationship(self, relationship: Relationship) -> bool:
        """Validate a publisher domain relationship."""
        return relationship.type in self._relationship_types

    def extract_from_source(self, source: Any) -> list[Entity]:
        """Extract publisher entities from a data source."""
        if isinstance(source, dict):
            return self._extract_from_dict(source)
        elif isinstance(source, str):
            return self._extract_from_domain(source)
        return []

    def _extract_from_dict(self, data: dict[str, Any]) -> list[Entity]:
        """Extract entities from a dictionary."""
        entities = []

        entity_type = data.get("type", "publisher")
        if entity_type not in self._entity_types:
            entity_type = "publisher"

        entity = Entity(
            type=entity_type,
            properties={
                "name": data.get("name", ""),
                "domain": data.get("domain", ""),
                "category": data.get("category", data.get("iab_category", "")),
                "monthly_visitors": data.get("monthly_visitors"),
                "page_views": data.get("page_views"),
                "brand_safety_score": data.get("brand_safety_score"),
                "quality_score": data.get("quality_score"),
            },
        )
        entities.append(entity)
        return entities

    def _extract_from_domain(self, domain: str) -> list[Entity]:
        """Extract entities from a domain name."""
        entity = Entity(
            type="domain",
            properties={"name": domain, "domain": domain},
        )
        return [entity]

    def classify_contextual_topics(
        self,
        publisher: Entity,
        topics: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Classify contextual topics for a publisher.

        Args:
            publisher: The publisher entity
            topics: Optional pre-extracted topics

        Returns:
            List of contextual topics
        """
        if topics:
            return topics

        category = publisher.get("category", "")

        topic_map = {
            "Sports": ["sports", "athletics", "competition", "games"],
            "News": ["news", "current events", "politics", "world events"],
            "Business": ["business", "finance", "economy", "markets"],
            "Technology": ["tech", "software", "hardware", "innovation"],
            "Lifestyle": ["lifestyle", "health", "wellness", "living"],
        }

        return topic_map.get(category, [category.lower()])

    def assess_brand_safety(
        self,
        publisher: Entity,
        vertical: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Assess brand safety for a publisher.

        Args:
            publisher: The publisher entity
            vertical: Optional brand vertical to check against

        Returns:
            Dictionary with brand safety assessment
        """
        quality_score = publisher.get("quality_score", 0.5)
        brand_safety_score = publisher.get("brand_safety_score", 0.5)

        if quality_score >= 0.8 and brand_safety_score >= 0.8:
            risk_level = "low"
        elif quality_score >= 0.5 and brand_safety_score >= 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "publisher_id": publisher.id,
            "risk_level": risk_level,
            "quality_score": quality_score,
            "brand_safety_score": brand_safety_score,
            "recommendation": "safe" if risk_level == "low" else "caution" if risk_level == "medium" else "avoid",
        }

    def get_inventory_overlap(
        self,
        publisher1_id: str,
        publisher2_id: str,
    ) -> dict[str, Any]:
        """
        Calculate inventory overlap between two publishers.

        Returns:
            Dictionary with overlap metrics
        """
        return {
            "publisher1": publisher1_id,
            "publisher2": publisher2_id,
            "audience_overlap": 0.0,
            "contextual_overlap": 0.0,
            "shared_topics": [],
        }
