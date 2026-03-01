"""
Brand domain module for the Context Graph Framework.

This module handles brand and company intelligence, including:
- Company and brand entities
- Competitive relationships
- Vertical/category classification
- Company hierarchy (parent/subsidiary)
"""

from typing import Any, Optional

from autoflow.context_graph.core import ContextDomain, Entity, Relationship


class BrandDomain(ContextDomain):
    """
    Domain module for brand and company intelligence.

    Entity types:
    - brand: Consumer-facing brands (Nike, Coca-Cola)
    - company: Legal entities (Nike Inc, The Coca-Cola Company)
    - vertical: Industry categories (Apparel, Beverages)

    Relationship types:
    - competes_with: Competitive relationships
    - belongs_to: Brand belongs to company
    - acquired_by: M&A relationships
    - in_vertical: Vertical classification
    """

    def __init__(self) -> None:
        """Initialize the Brand domain."""
        self._entity_types = {"brand", "company", "vertical"}
        self._relationship_types = {
            "competes_with",
            "belongs_to",
            "acquired_by",
            "partnered_with",
            "in_vertical",
            "sells_to",
            "targets_demographic",
        }

    @property
    def name(self) -> str:
        """Domain name."""
        return "brand"

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
        Validate a brand domain entity.

        Required properties vary by entity type:
        - brand: name (required), vertical (optional), tier (optional)
        - company: name (required), industry (optional), employees (optional)
        - vertical: name (required), parent (optional)
        """
        if entity.type not in self._entity_types:
            return False

        if entity.type == "brand":
            return "name" in entity.properties
        elif entity.type == "company":
            return "name" in entity.properties
        elif entity.type == "vertical":
            return "name" in entity.properties

        return False

    def validate_relationship(self, relationship: Relationship) -> bool:
        """Validate a brand domain relationship."""
        return relationship.type in self._relationship_types

    def extract_from_source(self, source: Any) -> list[Entity]:
        """
        Extract brand entities from a data source.

        Supported source types:
        - dict: Raw data dictionary
        - str: Company/brand name
        - list: List of companies/brands
        """
        if isinstance(source, dict):
            return self._extract_from_dict(source)
        elif isinstance(source, str):
            return self._extract_from_name(source)
        elif isinstance(source, list):
            return self._extract_from_list(source)
        return []

    def _extract_from_dict(self, data: dict[str, Any]) -> list[Entity]:
        """Extract entities from a dictionary."""
        entities = []

        entity_type = data.get("type", "brand")
        if entity_type not in self._entity_types:
            entity_type = "brand"

        entity = Entity(
            type=entity_type,
            properties={
                "name": data.get("name", ""),
                "vertical": data.get("vertical", data.get("industry", "")),
                "tier": data.get("tier", data.get("segment", "")),
                "description": data.get("description", ""),
                "website": data.get("website", ""),
                "employees": data.get("employees"),
                "revenue": data.get("revenue"),
                "founded": data.get("founded"),
            },
        )
        entities.append(entity)

        vertical = data.get("vertical", data.get("industry"))
        if vertical:
            vertical_entity = Entity(
                type="vertical",
                properties={"name": vertical, "description": f"{vertical} industry vertical"},
            )
            entities.append(vertical_entity)

        return entities

    def _extract_from_name(self, name: str) -> list[Entity]:
        """Extract entities from a company/brand name."""
        entity = Entity(
            type="brand",
            properties={"name": name},
        )
        return [entity]

    def _extract_from_list(self, names: list[str]) -> list[Entity]:
        """Extract entities from a list of names."""
        return [self._extract_from_name(name)[0] for name in names]

    def create_competitive_relationship(
        self,
        brand1: str,
        brand2: str,
        intensity: str = "medium",
        basis: Optional[str] = None,
    ) -> Relationship:
        """
        Create a competitive relationship between two brands.

        Args:
            brand1: First brand ID or name
            brand2: Second brand ID or name
            intensity: Competition intensity (low, medium, high)
            basis: Optional basis for competition

        Returns:
            Relationship object
        """
        properties = {"intensity": intensity}
        if basis:
            properties["basis"] = basis

        return Relationship(
            from_entity=brand1 if ":" in brand1 else f"brand:{brand1.lower()}",
            to_entity=brand2 if ":" in brand2 else f"brand:{brand2.lower()}",
            type="competes_with",
            properties=properties,
        )

    def create_brand_vertical_relationship(
        self,
        brand: str,
        vertical: str,
    ) -> Relationship:
        """
        Create a brand-to-vertical relationship.

        Args:
            brand: Brand ID or name
            vertical: Vertical ID or name

        Returns:
            Relationship object
        """
        return Relationship(
            from_entity=brand if ":" in brand else f"brand:{brand.lower()}",
            to_entity=vertical if ":" in vertical else f"vertical:{vertical.lower()}",
            type="in_vertical",
        )

    def get_performance_context(self, brand_id: str) -> dict[str, Any]:
        """
        Get performance-related context for a brand.

        Returns a dictionary with performance insights.
        """
        return {
            "brand_id": brand_id,
            "total_campaigns": 0,
            "avg_ctr": 0.0,
            "top_publishers": [],
            "top_creatives": [],
        }
