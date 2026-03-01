"""
LLM integration for the Context Graph Framework.

This module provides utilities for:
1. Converting graph subgraphs to natural language context for LLMs
2. Generating graph queries from natural language
3. Entity and relationship extraction using LLMs
"""

from typing import TYPE_CHECKING, Any, Optional, Generator
import json

if TYPE_CHECKING:
    from autoflow.context_graph.core import Entity, Relationship, Subgraph

from autoflow.context_graph.security import default_sanitizer


class GraphToContextAssembler:
    """
    Converts graph subgraphs into natural language context for LLMs.

    This is the primary integration point between the graph and LLMs.
    It transforms structured graph data into readable text that provides
    context and reasoning trails.
    """

    def __init__(
        self,
        include_paths: bool = True,
        include_properties: bool = True,
        max_entities: int = 50,
    ) -> None:
        """
        Initialize the assembler.

        Args:
            include_paths: Whether to include traversal paths in output
            include_properties: Whether to include entity properties
            max_entities: Maximum number of entities to include
        """
        self.include_paths = include_paths
        self.include_properties = include_properties
        self.max_entities = max_entities

    def subgraph_to_context(self, subgraph: Any) -> str:
        """
        Convert a subgraph to natural language context.

        Args:
            subgraph: The subgraph to convert

        Returns:
            Natural language description
        """
        if not subgraph.entities:
            return "No context available."

        sections = []

        if subgraph.path:
            sections.append(f"## Context: {subgraph.path}\n")

        sections.append("### Entities\n")

        for i, (entity_id, entity) in enumerate(list(subgraph.entities.items())[: self.max_entities]):
            label = entity.label if hasattr(entity, "label") else entity.get("name", entity_id)
            entity_type = entity.type if hasattr(entity, "type") else entity.get("type", "entity")

            line = f"- {label} ({entity_type})"

            if self.include_properties and hasattr(entity, "properties"):
                props = [f"{k}={v}" for k, v in entity.properties.items() if k != "name"]
                if props:
                    line += f" [{', '.join(props)}]"

            sections.append(line)

        if subgraph.relationships:
            sections.append("\n### Relationships\n")

            for rel in subgraph.relationships[: self.max_entities]:
                from_label = self._get_entity_label(subgraph, rel.from_entity if hasattr(rel, "from_entity") else rel.get("from"))
                to_label = self._get_entity_label(subgraph, rel.to_entity if hasattr(rel, "to_entity") else rel.get("to"))
                rel_type = rel.type if hasattr(rel, "type") else rel.get("type", "related_to")

                sections.append(f"- {from_label} → {rel_type} → {to_label}")

        sections.append(
            f"\n__Context contains {len(subgraph.entities)} entities "
            f"and {len(subgraph.relationships)} relationships.__"
        )

        return "\n".join(sections)

    def _get_entity_label(self, subgraph: Any, entity_id: str) -> str:
        """Get a human-readable label for an entity."""
        entity = subgraph.entities.get(entity_id)
        if entity:
            return entity.label if hasattr(entity, "label") else entity.get("name", entity_id)
        return entity_id

    def entity_to_description(self, entity: Any) -> str:
        """Convert a single entity to a text description."""
        label = entity.label if hasattr(entity, "label") else entity.get("name", entity.id)
        entity_type = entity.type if hasattr(entity, "type") else entity.get("type", "entity")

        desc = f"{label} is a {entity_type}"

        if hasattr(entity, "properties") and entity.properties:
            props = ", ".join([f"{k}={v}" for k, v in entity.properties.items() if k != "name"])
            if props:
                desc += f" with attributes: {props}"

        return desc

    def relationship_to_description(self, relationship: Any, from_entity: Any, to_entity: Any) -> str:
        """Convert a relationship to a text description."""
        from_label = from_entity.label if hasattr(from_entity, "label") else from_entity.get("name", from_entity.id)
        to_label = to_entity.label if hasattr(to_entity, "label") else to_entity.get("name", to_entity.id)
        rel_type = relationship.type if hasattr(relationship, "type") else relationship.get("type", "related_to")

        rel_text = rel_type.replace("_", " ")
        return f"{from_label} {rel_text} {to_label}"

    def format_for_prompt(
        self,
        subgraph: Any,
        query: Optional[str] = None,
    ) -> str:
        """
        Format graph context for an LLM prompt.

        Args:
            subgraph: The graph context
            query: Optional query that generated this context

        Returns:
            Formatted prompt section
        """
        parts = []

        if query:
            parts.append(f"**Query:** {query}\n")

        parts.append("**Relevant Context:**\n")
        parts.append(self.subgraph_to_context(subgraph))

        if self.include_paths and subgraph.path:
            parts.append(f"\n**Reasoning Path:** {subgraph.path}")

        return "\n".join(parts)

    def subgraph_to_context_stream(
        self, subgraph: Any
    ) -> Generator[str, None, None]:
        """
        Stream context generation piece by piece.

        Useful for LLM streaming APIs where you want to send
        context incrementally.

        Args:
            subgraph: The subgraph to convert

        Yields:
            Context fragments as strings
        """
        if not subgraph.entities:
            yield "No context available."
            return

        if subgraph.path:
            yield f"## Context: {subgraph.path}\n\n"

        yield "### Entities\n"
        for i, (entity_id, entity) in enumerate(
            list(subgraph.entities.items())[: self.max_entities]
        ):
            label = (
                entity.label
                if hasattr(entity, "label")
                else entity.get("name", entity_id)
            )
            entity_type = (
                entity.type if hasattr(entity, "type") else entity.get("type", "entity")
            )

            line = f"- {label} ({entity_type})"

            if self.include_properties and hasattr(entity, "properties"):
                props = [
                    f"{k}={v}"
                    for k, v in entity.properties.items()
                    if k != "name"
                ]
                if props:
                    line += f" [{', '.join(props)}]"

            yield line + "\n"

        if subgraph.relationships:
            yield "\n### Relationships\n"

            for rel in subgraph.relationships[: self.max_entities]:
                from_label = self._get_entity_label(
                    subgraph,
                    rel.from_entity if hasattr(rel, "from_entity") else rel.get("from"),
                )
                to_label = self._get_entity_label(
                    subgraph,
                    rel.to_entity if hasattr(rel, "to_entity") else rel.get("to"),
                )
                rel_type = (
                    rel.type if hasattr(rel, "type") else rel.get("type", "related_to")
                )

                yield f"- {from_label} → {rel_type} → {to_label}\n"

        yield (
            f"\n__Context contains {len(subgraph.entities)} entities "
            f"and {len(subgraph.relationships)} relationships.__"
        )


class CypherQueryBuilder:
    """
    Generates Cypher queries from natural language using LLMs.

    This enables text-to-graph querying where users can ask questions
    in natural language and get Cypher queries.
    """

    # Dangerous Cypher keywords that should not be in generated queries
    DANGEROUS_KEYWORDS = {
        "DROP",
        "DELETE",
        "DETACH",
        "REMOVE",
        "LOAD",
        "CSV",
        "CALL",
        "FOREACH",
        "CREATE",
        "SET",
        "MERGE",
    }

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        schema: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the query builder.

        Args:
            llm_client: An LLM client (Anthropic, OpenAI, etc.)
            schema: Optional graph schema description
        """
        self.llm_client = llm_client
        self.schema = schema or {}

    def build_query(
        self,
        question: str,
        schema: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build a Cypher query from a natural language question.

        Args:
            question: The natural language question
            schema: Optional schema override

        Returns:
            Cypher query string
        """
        effective_schema = schema or self.schema

        if not self.llm_client:
            return self._default_query(question)

        # Sanitize input to prevent prompt injection
        safe_question = default_sanitizer.sanitize_llm_input(question)
        prompt = self._build_prompt(safe_question, effective_schema)
        query = self._call_llm(prompt)

        # Validate the generated query
        if not self.validate_query(query):
            # Return safe default if validation fails
            return self._default_query(question)

        return query

    def validate_query(self, query: str) -> bool:
        """
        Validate a generated Cypher query is safe.

        Checks for:
        - No destructive operations (DROP, DELETE, DETACH)
        - No admin operations (LOAD CSV, CALL)
        - Reasonable complexity (LIMIT present or short query)

        Args:
            query: The Cypher query to validate

        Returns:
            True if query appears safe, False otherwise
        """
        if not query:
            return False

        query_upper = query.upper()

        # Check for dangerous keywords
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False

        # Require LIMIT for queries (prevents unbounded queries)
        # Skip this check for very short queries that might be intentional
        if len(query) > 100 and "LIMIT" not in query_upper:
            return False

        # Basic query structure check
        if not any(word in query_upper for word in ["MATCH", "RETURN", "WITH"]):
            return False

        return True

    def _build_prompt(self, question: str, schema: dict[str, Any]) -> str:
        """Build the LLM prompt for query generation."""
        schema_desc = self._format_schema(schema)

        prompt = f"""You are a Cypher query generator. Convert the following question into a Cypher query.

Graph Schema:
{schema_desc}

Question: {question}

Generate a Cypher query that answers the question. Return only the query, no explanation.

Query:"""

        return prompt

    def _format_schema(self, schema: dict[str, Any]) -> str:
        """Format schema for the prompt."""
        if not schema:
            return "No schema provided"

        parts = []

        if "entity_types" in schema:
            parts.append("Entity Types:")
            for et in schema["entity_types"]:
                parts.append(f"  - {et}")

        if "relationship_types" in schema:
            parts.append("\nRelationship Types:")
            for rt in schema["relationship_types"]:
                parts.append(f"  - {rt}")

        return "\n".join(parts)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM (placeholder - implement based on your LLM client)."""
        return "MATCH (n) RETURN n LIMIT 10"

    def _default_query(self, question: str) -> str:
        """Return a default query when no LLM is available."""
        question_lower = question.lower()

        if "brand" in question_lower and "compet" in question_lower:
            return "MATCH (b:Brand)-[:COMPETES_WITH]-(other:Brand) RETURN b, other"
        elif "campaign" in question_lower:
            return "MATCH (c:Campaign) RETURN c LIMIT 10"
        else:
            return "MATCH (n) RETURN n LIMIT 10"


class EntityExtractor:
    """
    Extracts entities and relationships from text using LLMs.

    This enables automated graph construction from unstructured text sources.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        entity_types: Optional[list[str]] = None,
        relationship_types: Optional[list[str]] = None,
    ) -> None:
        """
        Initialize the entity extractor.

        Args:
            llm_client: An LLM client
            entity_types: Known entity types to extract
            relationship_types: Known relationship types to extract
        """
        self.llm_client = llm_client
        self.entity_types = entity_types or []
        self.relationship_types = relationship_types or []

    def extract(
        self,
        text: str,
        domain: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Extract entities and relationships from text.

        Args:
            text: The input text
            domain: Optional domain hint (e.g., "brand", "campaign")

        Returns:
            Tuple of (entities, relationships) as dictionaries
        """
        if not self.llm_client:
            return self._extract_rules(text)

        # Sanitize input to prevent prompt injection
        safe_text = default_sanitizer.sanitize_llm_input(text)
        prompt = self._build_extraction_prompt(safe_text, domain)
        result = self._call_llm(prompt)
        return self._parse_extraction_result(result)

    def _build_extraction_prompt(self, text: str, domain: Optional[str]) -> str:
        """Build prompt for entity/relationship extraction."""
        entity_list = ", ".join(self.entity_types) if self.entity_types else "generic entities"
        rel_list = ", ".join(self.relationship_types) if self.relationship_types else "generic relationships"

        domain_hint = f"in the {domain} domain" if domain else ""

        prompt = f"""Extract entities and relationships from the following text {domain_hint}.

Entity types to look for: {entity_list}
Relationship types to look for: {rel_list}

Text:
{text}

Return the result as JSON with this structure:
{{
  "entities": [
    {{"type": "brand", "name": "Nike", "properties": {{...}}}}
  ],
  "relationships": [
    {{"from": "Nike", "to": "Adidas", "type": "competes_with"}}
  ]
}}"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM (placeholder)."""
        return '{"entities": [], "relationships": []}'

    def _parse_extraction_result(self, result: str) -> tuple[list[dict], list[dict]]:
        """Parse the LLM result."""
        try:
            data = json.loads(result)
            return data.get("entities", []), data.get("relationships", [])
        except json.JSONDecodeError:
            return [], []

    def _extract_rules(self, text: str) -> tuple[list[dict], list[dict]]:
        """Simple rule-based extraction (without LLM)."""
        return [], []

