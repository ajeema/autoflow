"""
Campaign domain module for the Context Graph Framework.

This module handles campaign and creative context, including:
- Campaign entities and their configuration
- Creative assets and their attributes
- Performance metrics and outcomes
- Campaign-to-brand and campaign-to-publisher relationships
"""

from typing import Any, Optional

from autoflow.context_graph.core import ContextDomain, Entity, Relationship


class CampaignDomain(ContextDomain):
    """
    Domain module for campaign and creative intelligence.

    Entity types:
    - campaign: Advertising campaigns
    - creative: Creative assets
    - goal: Campaign goals and KPIs

    Relationship types:
    - optimized_for: Campaign → goal
    - uses_creative: Campaign → creative
    - targets: Campaign → audience segment
    - created_by: Campaign → advertiser/brand
    - ran_on: Campaign → publisher
    """

    def __init__(self) -> None:
        """Initialize the Campaign domain."""
        self._entity_types = {"campaign", "creative", "goal"}
        self._relationship_types = {
            "optimized_for",
            "uses_creative",
            "targets",
            "created_by",
            "ran_on",
            "performed_best_on",
            "performed_worst_on",
        }

    @property
    def name(self) -> str:
        """Domain name."""
        return "campaign"

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
        Validate a campaign domain entity.

        Required properties:
        - campaign: name (required)
        - creative: format (required), name (optional)
        - goal: type (required)
        """
        if entity.type not in self._entity_types:
            return False

        if entity.type == "campaign":
            return "name" in entity.properties
        elif entity.type == "creative":
            return "format" in entity.properties
        elif entity.type == "goal":
            return "type" in entity.properties

        return False

    def validate_relationship(self, relationship: Relationship) -> bool:
        """Validate a campaign domain relationship."""
        return relationship.type in self._relationship_types

    def extract_from_source(self, source: Any) -> list[Entity]:
        """Extract campaign entities from a data source."""
        if isinstance(source, dict):
            return self._extract_from_dict(source)
        return []

    def _extract_from_dict(self, data: dict[str, Any]) -> list[Entity]:
        """Extract entities from a dictionary."""
        entities = []

        entity_type = data.get("type", "campaign")
        if entity_type not in self._entity_types:
            entity_type = "campaign"

        entity = Entity(
            type=entity_type,
            properties={
                "name": data.get("name", ""),
                "format": data.get("format", ""),
                "budget": data.get("budget"),
                "goal": data.get("goal", ""),
                "status": data.get("status", ""),
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
            },
        )
        entities.append(entity)
        return entities

    def classify_creative_attributes(self, creative: Entity) -> dict[str, Any]:
        """
        Classify creative attributes for analysis.

        Analyzes a creative to determine:
        - Format (display, video, native, etc.)
        - Messaging type (emotional, informational, promotional)
        - Visual style
        - Contains price/discount
        - Contains logo/branding

        Args:
            creative: The creative entity to classify

        Returns:
            Dictionary of classified attributes
        """
        properties = creative.properties

        return {
            "format": properties.get("format", "unknown"),
            "messaging_type": self._classify_messaging(properties),
            "visual_style": self._classify_visual_style(properties),
            "has_price": properties.get("has_price", False),
            "has_logo": properties.get("has_logo", True),
            "has_cta": properties.get("has_cta", False),
        }

    def _classify_messaging(self, properties: dict[str, Any]) -> str:
        """Classify messaging type."""
        description = properties.get("description", "").lower()

        if any(word in description for word in ["sale", "discount", "offer", "deal", "save"]):
            return "promotional"
        elif any(word in description for word in ["feel", "experience", "emotional", "story"]):
            return "emotional"
        elif any(word in description for word in ["features", "specs", "details", "information"]):
            return "informational"
        return "general"

    def _classify_visual_style(self, properties: dict[str, Any]) -> str:
        """Classify visual style."""
        return properties.get("visual_style", "unknown")

    def compare_campaign_performance(
        self,
        campaign1_id: str,
        campaign2_id: str,
    ) -> dict[str, Any]:
        """
        Compare performance between two campaigns.

        Returns:
            Dictionary with performance comparison metrics
        """
        return {
            "campaign1": campaign1_id,
            "campaign2": campaign2_id,
            "ctr_diff": 0.0,
            "conversion_diff": 0.0,
            "roi_diff": 0.0,
        }
