"""
Core abstractions for the Context Graph Framework.

This module defines the fundamental building blocks that work across
any domain: entities, relationships, and the graph interface itself.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar, Optional
from enum import Enum
from uuid import uuid4

# Pydantic for validation and serialization
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic.dataclasses import dataclass

# Security is optional - can be disabled for development
from autoflow.context_graph.security import default_config, default_validator, default_sanitizer

# Type aliases for clarity
EntityID = str
RelationshipID = str


class EntityType(str, Enum):
    """Standard entity types. Domains can extend with custom types."""

    # Generic types
    NODE = "node"
    ENTITY = "entity"

    # Business/domain types (examples)
    BRAND = "brand"
    COMPANY = "company"
    CAMPAIGN = "campaign"
    CREATIVE = "creative"
    PUBLISHER = "publisher"
    USER = "user"
    PRODUCT = "product"
    VERTICAL = "vertical"


class RelationshipType(str, Enum):
    """Standard relationship types. Domains can extend with custom types."""

    # Generic
    RELATED_TO = "related_to"
    BELONGS_TO = "belongs_to"
    PART_OF = "part_of"

    # Competitive
    COMPETES_WITH = "competes_with"
    ACQUIRED_BY = "acquired_by"
    PARTNERED_WITH = "partnered_with"

    # Advertising
    ADVERTISED_ON = "advertised_on"
    TARGETS = "targets"
    OPTIMIZED_FOR = "optimized_for"
    USES_CREATIVE = "uses_creative"

    # Performance
    PERFORMED_ON = "performed_on"
    CONVERTED_FROM = "converted_from"

    # Temporal
    CREATED_BEFORE = "created_before"
    CREATED_AFTER = "created_after"


class Entity(BaseModel):
    """
    A node in the context graph.

    Entities represent real-world objects: brands, campaigns, users, etc.

    Security:
        Validation can be enabled globally via SecurityConfig or per-instance
        by setting _validate=True. Default uses global config.

    Attributes:
        type: The entity type (e.g., "brand", "campaign")
        properties: Key-value metadata about the entity
        id: Unique identifier (auto-generated if not provided)
        embedding: Optional vector embedding for semantic search
        created_at: Timestamp when entity was added to graph
        _validate: Whether to validate this entity (default: uses global config)
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",  # Prevent unknown fields
        arbitrary_types_allowed=True,  # Allow datetime, etc.
        use_enum_values=True,
    )

    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: f"entity:{uuid4().hex[:12]}")
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    _validate: Optional[bool] = None  # None = use global config

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that type is not empty."""
        if not v:
            raise ValueError("Entity must have a type")
        return v

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, v: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Validate and normalize properties."""
        if v is None:
            return {}

        # Security validation (can be disabled)
        if default_config.enable_validation:
            # Validate properties (note: we can't access self yet in validator)
            # Properties will be validated in model_post_init
            pass

        return v

    @model_validator(mode="after")
    def validate_and_sanitize(self) -> "Entity":
        """Validate and normalize the entity after construction."""
        # Security validation (can be disabled)
        should_validate = self._validate if self._validate is not None else default_config.enable_validation
        if should_validate:
            # Validate and normalize type
            object.__setattr__(self, "type", default_validator.validate_entity_type(self.type))
            # Validate properties
            validated_props = default_validator.validate_property_dict(self.properties)
            # Sanitize property values
            sanitized_props = {k: default_sanitizer.sanitize_property_value(v) for k, v in validated_props.items()}
            object.__setattr__(self, "properties", sanitized_props)

        return self

    def get(self, key: str, default: Any = None) -> Any:
        """Get a property value."""
        return self.properties.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a property value."""
        self.properties[key] = value

    @property
    def label(self) -> str:
        """Get a human-readable label for the entity."""
        return self.properties.get("name", self.properties.get("title", self.id))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "type": self.type,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create from dictionary representation."""
        return cls.model_validate(data)

    def model_dump_json(self, **kwargs: Any) -> str:
        """
        Dump model to JSON (Pydantic v2 method).

        This is the Pydantic v2 equivalent of to_json().
        """
        return super().model_dump_json(**kwargs)


class Relationship(BaseModel):
    """
    A directed edge between two entities.

    Relationships can have properties (e.g., confidence scores, timestamps)
    and are typed (e.g., "competes_with", "advertised_on").

    Security:
        Validation can be enabled globally via SecurityConfig or per-instance
        by setting _validate=True. Default uses global config.

    Attributes:
        from_entity: Source entity ID
        to_entity: Target entity ID
        type: Relationship type
        properties: Metadata about the relationship
        confidence: Optional confidence score (0-1) for probabilistic edges
        created_at: Timestamp when relationship was created
        _validate: Whether to validate this relationship (default: uses global config)
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )

    from_entity: str
    to_entity: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    _validate: Optional[bool] = None  # None = use global config

    @field_validator("from_entity", "to_entity")
    @classmethod
    def validate_entities(cls, v: str, info) -> str:
        """Validate that entity IDs are not empty."""
        if not v:
            raise ValueError("Entity ID cannot be empty")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that type is not empty."""
        if not v:
            raise ValueError("Relationship must have a type")
        return v

    @model_validator(mode="after")
    def validate_and_sanitize(self) -> "Relationship":
        """Validate and sanitize the relationship after construction."""
        # Security validation (can be disabled)
        should_validate = self._validate if self._validate is not None else default_config.enable_validation
        if should_validate:
            # Validate and normalize type
            object.__setattr__(self, "type", default_validator.validate_relationship_type(self.type))
            # Validate properties
            validated_props = default_validator.validate_property_dict(self.properties)
            # Sanitize property values
            sanitized_props = {k: default_sanitizer.sanitize_property_value(v) for k, v in validated_props.items()}
            object.__setattr__(self, "properties", sanitized_props)

        return self

    @property
    def label(self) -> str:
        """Get a human-readable label for the relationship."""
        return self.properties.get("label", self.type.replace("_", " ").title())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "from": self.from_entity,
            "to": self.to_entity,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


class TraversalPattern(BaseModel):
    """
    A pattern for traversing the graph.

    Patterns use a Cypher-like syntax for multi-hop queries:
    (entity1)-[RELATIONSHIP_TYPE]->(entity2)-[:ANOTHER_TYPE]->(entity3)

    Attributes:
        pattern: The traversal pattern string
        max_hops: Maximum number of hops to traverse
        filter_properties: Optional property filters
    """

    # Pydantic configuration
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    pattern: str
    max_hops: int = Field(default=4, ge=1, le=10)
    filter_properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("max_hops")
    @classmethod
    def validate_max_hops(cls, v: int) -> int:
        """Validate max_hops is reasonable."""
        return min(v, default_config.max_hops) if default_config.enable_validation else v

    def to_cypher(self, start_node: str = "start") -> str:
        """
        Convert pattern to Cypher query fragment.

        Args:
            start_node: The variable name for the starting node

        Returns:
            Cypher MATCH pattern
        """
        return f"MATCH ({start_node}){self.pattern}"


class Subgraph(BaseModel):
    """
    A subset of the graph containing entities and relationships.

    Subgraphs are the result of traversals and are passed to LLMs as context.

    Attributes:
        entities: Entities in the subgraph
        relationships: Relationships in the subgraph
        path: Optional traversal path that generated this subgraph
    """

    # Pydantic configuration
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    entities: dict[str, Entity] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)
    path: Optional[str] = None

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the subgraph."""
        self.entities[entity.id] = entity

    def add_relationship(self, rel: Relationship) -> None:
        """Add a relationship to the subgraph."""
        self.relationships.append(rel)

    def merge(self, other: "Subgraph") -> None:
        """Merge another subgraph into this one."""
        self.entities.update(other.entities)
        self.relationships.extend(other.relationships)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "relationships": [r.to_dict() for r in self.relationships],
            "path": self.path,
            "summary": f"{len(self.entities)} entities, {len(self.relationships)} relationships",
        }


T = TypeVar("T", bound=Entity)


class GraphBackend(ABC):
    """
    Abstract base class for graph storage backends.

    Implementations include Neo4j, in-memory, and potentially others.
    """

    @abstractmethod
    def add_entity(self, entity: Entity) -> str:
        """Add an entity to the graph. Returns entity ID."""
        pass

    @abstractmethod
    def add_entities(self, entities: list[Entity]) -> list[str]:
        """Add multiple entities efficiently. Returns list of entity IDs."""
        pass

    @abstractmethod
    def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship. Returns relationship ID."""
        pass

    @abstractmethod
    def add_relationships(self, relationships: list[Relationship]) -> list[str]:
        """Add multiple relationships efficiently. Returns list of relationship IDs."""
        pass

    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        pass

    @abstractmethod
    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> list[tuple[Entity, Optional[Relationship]]]:
        """
        Get neighboring entities.

        Args:
            entity_id: Starting entity ID
            relationship_type: Filter by relationship type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of (entity, relationship) tuples
        """
        pass

    @abstractmethod
    def traverse(self, start_entity_id: str, pattern: TraversalPattern) -> Subgraph:
        """Execute a multi-hop traversal."""
        pass

    @abstractmethod
    def query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a raw query (backend-specific syntax)."""
        pass

    @abstractmethod
    def search_by_property(
        self, entity_type: str, property_name: str, property_value: Any
    ) -> list[Entity]:
        """Search for entities by property value."""
        pass

    @abstractmethod
    def search_similar(
        self, entity_id: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> list[tuple[Entity, float]]:
        """
        Semantic similarity search using embeddings.

        Returns:
            List of (entity, similarity_score) tuples
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the backend connection."""
        pass


class ContextDomain(ABC):
    """
    Abstract base class for domain modules.

    Domains encapsulate entity types, relationship types, and domain-specific
    logic (validation, extraction, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain name (e.g., "brand", "campaign")."""
        pass

    @property
    @abstractmethod
    def entity_types(self) -> set[str]:
        """Entity types this domain handles."""
        pass

    @property
    @abstractmethod
    def relationship_types(self) -> set[str]:
        """Relationship types this domain handles."""
        pass

    def validate_entity(self, entity: Entity) -> bool:
        """
        Validate an entity belongs to this domain.

        Returns:
            True if valid, False otherwise
        """
        return entity.type in self.entity_types

    def validate_relationship(self, relationship: Relationship) -> bool:
        """
        Validate a relationship belongs to this domain.

        Returns:
            True if valid, False otherwise
        """
        return relationship.type in self.relationship_types

    def extract_from_source(self, source: Any) -> list[Entity]:
        """
        Extract entities from a data source.

        Override this in subclasses to implement domain-specific extraction.
        """
        raise NotImplementedError(f"{self.name} domain does not implement extract_from_source")


class ContextGraph:
    """
    Main interface for the Context Graph Framework.

    The ContextGraph provides a unified API for working with knowledge graphs,
    handling entity/relationship management, multi-hop traversals, and LLM integration.

    Example:
        ```python
        graph = ContextGraph(backend=Neo4jBackend(uri="..."))

        # Add entities and relationships
        brand = Entity(type="brand", properties={"name": "Nike"})
        graph.add_entity(brand)

        # Traverse the graph
        subgraph = graph.traverse("brand:nike", TraversalPattern("(brand)-[:COMPETES_WITH]->(brand)"))

        # Get LLM-ready context
        context = graph.get_context_for_llm(subgraph)
        ```
    """

    def __init__(self, backend: GraphBackend, domains: Optional[list[ContextDomain]] = None):
        """
        Initialize the context graph.

        Args:
            backend: Storage backend (Neo4j, in-memory, etc.)
            domains: Optional domain modules for validation and extraction
        """
        self._backend = backend
        self._domains: dict[str, ContextDomain] = {}

        for domain in domains or []:
            self.register_domain(domain)

    def register_domain(self, domain: ContextDomain) -> None:
        """Register a domain module."""
        self._domains[domain.name] = domain

    def get_domain(self, name: str) -> Optional[ContextDomain]:
        """Get a registered domain by name."""
        return self._domains.get(name)

    def add_entity(self, entity: Entity) -> str:
        """
        Add an entity to the graph.

        Returns:
            The entity ID
        """
        for domain in self._domains.values():
            if domain.validate_entity(entity):
                break

        return self._backend.add_entity(entity)

    def add_entities(self, entities: list[Entity]) -> list[str]:
        """
        Add multiple entities efficiently.

        Args:
            entities: List of entities to add

        Returns:
            List of entity IDs in the same order
        """
        for domain in self._domains.values():
            for entity in entities:
                if domain.validate_entity(entity):
                    break

        return self._backend.add_entities(entities)

    def add_relationship(self, relationship: Relationship) -> str:
        """
        Add a relationship to the graph.

        Returns:
            The relationship ID
        """
        return self._backend.add_relationship(relationship)

    def add_relationships(self, relationships: list[Relationship]) -> list[str]:
        """
        Add multiple relationships efficiently.

        Args:
            relationships: List of relationships to add

        Returns:
            List of relationship IDs in the same order
        """
        return self._backend.add_relationships(relationships)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._backend.get_entity(entity_id)

    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> list[tuple[Entity, Optional[Relationship]]]:
        """Get neighboring entities."""
        return self._backend.get_neighbors(entity_id, relationship_type, direction)

    def traverse(
        self,
        start_entity_id: str,
        pattern: TraversalPattern,
        max_hops: Optional[int] = None,
    ) -> Subgraph:
        """
        Execute a multi-hop traversal.

        Args:
            start_entity_id: ID of the starting entity
            pattern: Traversal pattern
            max_hops: Override max hops from pattern

        Returns:
            Subgraph containing the traversal results
        """
        if max_hops:
            pattern = TraversalPattern(
                pattern.pattern,
                max_hops=max_hops,
                filter_properties=pattern.filter_properties,
            )

        return self._backend.traverse(start_entity_id, pattern)

    def search_by_property(
        self, entity_type: str, property_name: str, property_value: Any
    ) -> list[Entity]:
        """Search for entities by property."""
        return self._backend.search_by_property(entity_type, property_name, property_value)

    def search_similar(
        self, entity_id: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> list[tuple[Entity, float]]:
        """Search for semantically similar entities."""
        return self._backend.search_similar(entity_id, entity_type, limit)

    def query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a raw query."""
        return self._backend.query(query, params)

    def get_context_for_llm(
        self,
        start_entity_id: Optional[str] = None,
        subgraph: Optional[Subgraph] = None,
        max_hops: int = 3,
        include_paths: bool = True,
    ) -> str:
        """
        Get LLM-ready context from the graph.

        This is the key integration point with LLMs - it converts graph structure
        into natural language context.

        Args:
            start_entity_id: If provided, traverse from this entity
            subgraph: If provided, use this subgraph directly
            max_hops: Max hops if traversing from start_entity_id
            include_paths: Whether to include traversal paths in output

        Returns:
            Natural language description of the graph context
        """
        if subgraph is None and start_entity_id:
            pattern = TraversalPattern(pattern="-[*]->", max_hops=max_hops)
            subgraph = self.traverse(start_entity_id, pattern)
        elif subgraph is None:
            return "No context available."

        from autoflow.context_graph.llm import GraphToContextAssembler

        assembler = GraphToContextAssembler(include_paths=include_paths)
        return assembler.subgraph_to_context(subgraph)

    def close(self) -> None:
        """Close the graph backend connection."""
        self._backend.close()


# ============================================================================
# Utility Functions
# ============================================================================


def is_valid_entity_id(entity_id: str) -> bool:
    """
    Check if string looks like a valid entity ID.

    Valid formats:
    - "entity:<uuid>" (auto-generated)
    - "<type>:<identifier>" (user-provided)
    - Any string containing ":" (type:value)

    Args:
        entity_id: The entity ID to validate

    Returns:
        True if looks like a valid entity ID format
    """
    return ":" in entity_id or entity_id.startswith("entity:")


def extract_entity_type(entity_id: str) -> Optional[str]:
    """
    Extract entity type from entity ID.

    Args:
        entity_id: The entity ID (e.g., "brand:nike")

    Returns:
        The entity type (e.g., "brand") or None if not parseable
    """
    if ":" in entity_id:
        return entity_id.split(":")[0]
    return None


def validate_entity_id(entity_id: str) -> None:
    """
    Validate entity ID format and raise exception if invalid.

    Args:
        entity_id: The entity ID to validate

    Raises:
        ValueError: If entity ID format is invalid
    """
    if not is_valid_entity_id(entity_id):
        raise ValueError(
            f"Invalid entity ID format: '{entity_id}'. "
            f"Expected format: '<type>:<identifier>' (e.g., 'brand:nike')"
        )
