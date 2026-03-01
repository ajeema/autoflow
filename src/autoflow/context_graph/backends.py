"""
Graph storage backends.

Implementations include:
- Neo4jBackend: Production Neo4j database
- InMemoryBackend: In-memory storage for testing and development
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from autoflow.context_graph.core import Entity, Relationship, TraversalPattern, Subgraph

from autoflow.context_graph.security import default_config, default_sanitizer


class InMemoryBackend:
    """
    In-memory graph backend for testing and development.

    This is a simple implementation that stores everything in Python dictionaries.
    Useful for unit tests and quick prototyping without a database.
    """

    def __init__(self) -> None:
        """Initialize the in-memory backend."""
        self._entities: dict[str, Any] = {}
        self._relationships: dict[str, Any] = {}
        self._adjacency_out: dict[str, list[tuple[str, str]]] = {}
        self._adjacency_in: dict[str, list[tuple[str, str]]] = {}

    def add_entity(self, entity: Any) -> str:
        """Add an entity to the graph."""
        self._entities[entity.id] = entity
        self._adjacency_out.setdefault(entity.id, [])
        self._adjacency_in.setdefault(entity.id, [])
        return entity.id

    def add_entities(self, entities: list[Any]) -> list[str]:
        """
        Add multiple entities efficiently.

        Args:
            entities: List of entities to add

        Returns:
            List of entity IDs in the same order
        """
        ids = []
        for entity in entities:
            ids.append(self.add_entity(entity))
        return ids

    def add_relationship(self, relationship: Any) -> str:
        """Add a relationship to the graph."""
        rel_id = f"{relationship.from_entity}->{relationship.to_entity}"
        self._relationships[rel_id] = relationship

        # Outgoing adjacency
        self._adjacency_out.setdefault(relationship.from_entity, [])
        self._adjacency_out[relationship.from_entity].append((rel_id, relationship.to_entity))

        # Incoming adjacency
        self._adjacency_in.setdefault(relationship.to_entity, [])
        self._adjacency_in[relationship.to_entity].append((rel_id, relationship.from_entity))

        return rel_id

    def add_relationships(self, relationships: list[Any]) -> list[str]:
        """
        Add multiple relationships efficiently.

        Args:
            relationships: List of relationships to add

        Returns:
            List of relationship IDs in the same order
        """
        ids = []
        for relationship in relationships:
            ids.append(self.add_relationship(relationship))
        return ids

    def get_entity(self, entity_id: str) -> Optional[Any]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> list[tuple[Any, Optional[Any]]]:
        """Get neighboring entities."""
        neighbors = []

        if direction in ("outgoing", "both"):
            for rel_id, target_id in self._adjacency_out.get(entity_id, []):
                rel = self._relationships.get(rel_id)
                if rel is None:
                    continue
                if relationship_type is None or rel.type == relationship_type:
                    target = self._entities.get(target_id)
                    if target:
                        neighbors.append((target, rel))

        if direction in ("incoming", "both"):
            for rel_id, source_id in self._adjacency_in.get(entity_id, []):
                rel = self._relationships.get(rel_id)
                if rel is None:
                    continue
                if relationship_type is None or rel.type == relationship_type:
                    source = self._entities.get(source_id)
                    if source:
                        neighbors.append((source, rel))

        return neighbors

    def traverse(self, start_entity_id: str, pattern: Any) -> Any:
        """Execute a simple traversal."""
        from autoflow.context_graph.core import Subgraph

        result = Subgraph()

        start_entity = self.get_entity(start_entity_id)
        if not start_entity:
            return result

        result.add_entity(start_entity)

        max_hops = pattern.max_hops
        visited = {start_entity_id}
        current_level = {start_entity_id}

        for _ in range(max_hops):
            next_level = set()
            for entity_id in current_level:
                neighbors = self.get_neighbors(entity_id)
                for neighbor, rel in neighbors:
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        next_level.add(neighbor.id)
                        result.add_entity(neighbor)
                        if rel:
                            result.add_relationship(rel)

            current_level = next_level
            if not current_level:
                break

        result.path = f"Traversal from {start_entity_id} ({len(result.entities)} entities)"
        return result

    def query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a query (limited support)."""
        return []

    def search_by_property(self, entity_type: str, property_name: str, property_value: Any) -> list[Any]:
        """Search for entities by property."""
        results = []
        for entity in self._entities.values():
            if entity.type == entity_type and entity.get(property_name) == property_value:
                results.append(entity)
        return results

    def search_similar(
        self, entity_id: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> list[tuple[Any, float]]:
        """Semantic similarity search (not supported in-memory)."""
        return []

    def close(self) -> None:
        """Close the backend (no-op for in-memory)."""
        pass


class Neo4jBackend:
    """
    Neo4j graph database backend.

    This is the recommended backend for production use. Neo4j provides:
    - Native graph storage and querying
    - Cypher query language
    - Built-in vector search (v5.11+)
    - Excellent visualization tools

    Requires the neo4j Python driver:
        pip install neo4j

    Example:
        ```python
        backend = Neo4jBackend(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password"
        )
        ```
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "neo4j",
        database: str = "neo4j",
    ) -> None:
        """
        Initialize the Neo4j backend.

        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
            database: Database name (default: "neo4j")
        """
        try:
            from neo4j import GraphDatabase
        except ImportError as e:
            raise ImportError(
                "Neo4j backend requires 'neo4j' package. "
                "Install it with: pip install neo4j"
            ) from e

        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        self._database = database
        self._uri = uri

        with self._driver.session(database=database) as session:
            session.run("RETURN 1")

    def add_entity(self, entity: Any) -> str:
        """Add an entity to Neo4j."""
        # Entity type is already validated by Entity.__post_init__
        # Use backtick quoting for safety if needed
        entity_type = default_sanitizer.sanitize_cypher_identifier(entity.type.title())
        labels = f"{entity_type}:Entity"

        # Property keys are already validated, just parameterize
        props = ", ".join([f"e.{k}: $k_{k}" for k in entity.properties.keys()])

        query = f"""
        MERGE (e:{labels} {{id: $id}})
        SET {{{props}}}
        RETURN e.id as id
        """

        params = {"id": entity.id}
        params.update({f"k_{k}": v for k, v in entity.properties.items()})

        with self._driver.session(database=self._database) as session:
            result = session.run(query, params)
            record = result.single()
            return record["id"]

    def add_entities(self, entities: list[Any]) -> list[str]:
        """
        Add multiple entities efficiently using UNWIND.

        Args:
            entities: List of entities to add

        Returns:
            List of entity IDs
        """
        ids = []
        with self._driver.session(database=self._database) as session:
            for entity in entities:
                ids.append(self.add_entity(entity))
        return ids

    def add_relationship(self, relationship: Any) -> str:
        """Add a relationship to Neo4j."""
        # Relationship type is already validated by Relationship.__post_init__
        rel_type = default_sanitizer.sanitize_cypher_identifier(relationship.type.upper())

        props_str = ""
        params = {"from": relationship.from_entity, "to": relationship.to_entity}

        if relationship.properties:
            # Property keys already validated
            props = ", ".join([f"r.{k} = $p_{k}" for k in relationship.properties.keys()])
            props_str = f"SET {props}"
            params.update({f"p_{k}": v for k, v in relationship.properties.items()})

        if relationship.confidence is not None:
            if props_str:
                props_str += ", r.confidence = $confidence"
            else:
                props_str = f"SET r.confidence = $confidence"
            params["confidence"] = relationship.confidence

        query = f"""
        MATCH (from {{id: $from}})
        MATCH (to {{id: $to}})
        MERGE (from)-[r:{rel_type}]->(to)
        {props_str}
        RETURN from.id + '->' + to.id as id
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, params)
            record = result.single()
            return record["id"]

    def add_relationships(self, relationships: list[Any]) -> list[str]:
        """
        Add multiple relationships efficiently.

        Args:
            relationships: List of relationships to add

        Returns:
            List of relationship IDs
        """
        ids = []
        with self._driver.session(database=self._database) as session:
            for relationship in relationships:
                ids.append(self.add_relationship(relationship))
        return ids

    def get_entity(self, entity_id: str) -> Optional[Any]:
        """Get an entity by ID."""
        from autoflow.context_graph.core import Entity

        query = """
        MATCH (e {id: $id})
        RETURN e
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, {"id": entity_id})
            record = result.single()

            if record:
                node = record["e"]
                labels = list(node.labels)
                labels.discard("Entity")
                entity_type = labels[0].lower() if labels else "entity"

                return Entity(
                    id=node["id"],
                    type=entity_type,
                    properties=dict(node),
                )

        return None

    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> list[tuple[Any, Optional[Any]]]:
        """Get neighboring entities."""
        if direction == "outgoing":
            dir_pattern = "-[r]->(other)"
            other_var = "other"
        elif direction == "incoming":
            dir_pattern = "<-[r]-(other)"
            other_var = "other"
        else:
            dir_pattern = "-[r]-(other)"
            other_var = "other"

        rel_filter = f":{relationship_type.upper()}" if relationship_type else ""

        query = f"""
        MATCH (start {{id: $id}}){dir_pattern}{rel_filter}
        RETURN {other_var}, r
        LIMIT 100
        """

        with self._driver.session(database=self._database) as session:
            from autoflow.context_graph.core import Entity, Relationship

            result = session.run(query, {"id": entity_id})

            neighbors = []
            for record in result:
                node = record[other_var]
                rel = record["r"]

                labels = list(node.labels)
                labels.discard("Entity")
                entity_type = labels[0].lower() if labels else "entity"

                entity = Entity(
                    id=node.get("id", ""),
                    type=entity_type,
                    properties=dict(node),
                )

                relationship = Relationship(
                    from_entity=rel.start_node.get("id", ""),
                    to_entity=rel.end_node.get("id", ""),
                    type=rel.type.lower(),
                    properties=dict(rel),
                )

                neighbors.append((entity, relationship))

            return neighbors

    def traverse(self, start_entity_id: str, pattern: Any) -> Any:
        """Execute a multi-hop traversal."""
        from autoflow.context_graph.core import Subgraph, Entity, Relationship

        max_hops = pattern.max_hops

        query = f"""
        MATCH path = (start {{id: $id}})-[*..{max_hops}]-(other)
        RETURN path, other
        LIMIT 100
        """

        result = Subgraph()

        with self._driver.session(database=self._database) as session:
            records = session.run(query, {"id": start_entity_id})

            for record in records:
                path = record["path"]

                for node in path.nodes:
                    labels = list(node.labels)
                    labels.discard("Entity")
                    entity_type = labels[0].lower() if labels else "entity"

                    entity = Entity(
                        id=node.get("id", ""),
                        type=entity_type,
                        properties=dict(node),
                    )
                    result.add_entity(entity)

                for rel in path.relationships:
                    relationship = Relationship(
                        from_entity=rel.start_node.get("id", ""),
                        to_entity=rel.end_node.get("id", ""),
                        type=rel.type.lower(),
                        properties=dict(rel),
                    )
                    result.add_relationship(relationship)

        result.path = f"Traversal from {start_entity_id}"
        return result

    def query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a raw Cypher query."""
        with self._driver.session(database=self._database) as session:
            result = session.run(query, params)
            return [dict(record) for record in result]

    def search_by_property(self, entity_type: str, property_name: str, property_value: Any) -> list[Any]:
        """Search for entities by property."""
        from autoflow.context_graph.core import Entity

        query = f"""
        MATCH (e:{entity_type.title()}:Entity)
        WHERE e.{property_name} = $value
        RETURN e
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, {"value": property_value})

            entities = []
            for record in result:
                node = record["e"]
                entity = Entity(
                    id=node.get("id", ""),
                    type=entity_type,
                    properties=dict(node),
                )
                entities.append(entity)

            return entities

    def search_similar(
        self, entity_id: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> list[tuple[Any, float]]:
        """Semantic similarity search (requires vector index configuration)."""
        return []

    def close(self) -> None:
        """Close the Neo4j driver."""
        self._driver.close()
