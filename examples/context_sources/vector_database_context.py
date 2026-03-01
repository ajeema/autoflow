#!/usr/bin/env python3
"""
AutoFlow Context Source: Vector Database Integration

This example demonstrates how to extend AutoFlow to pull context from
vector databases like Pinecone, Weaviate, ChromaDB, or Qdrant.

Use cases:
- Semantic search for similar past issues/errors
- Retrieval-Augmented Generation (RAG) for context gathering
- Historical workflow pattern matching
- Similar proposal retrieval

Setup for different vector databases:

Pinecone:
    pip install pinecone-client
    export PINECONE_API_KEY=your_key

Weaviate:
    pip install weaviate-client
    export WEAVIATE_URL=http://localhost:8080

ChromaDB:
    pip install chromadb
    # ChromaDB runs locally by default

Qdrant:
    pip install qdrant-client
    export QDRANT_URL=http://localhost:6333
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from autoflow.graph.context_graph import ContextGraphBuilder
from autoflow.graph.store import GraphStore
from autoflow.observe.events import make_event
from autoflow.types import GraphNode


# =============================================================================
# Base Classes for Vector Context Sources
# =============================================================================

@dataclass
class ContextMatch:
    """A matching context item from vector search."""
    content: str
    similarity: float
    metadata: dict[str, Any]
    source: str
    timestamp: Optional[datetime] = None


class VectorContextSource:
    """Base class for vector database context sources."""

    def __init__(self, index_name: str = "autoflow_context"):
        self.index_name = index_name

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ContextMatch]:
        """Search for similar contexts."""
        raise NotImplementedError

    async def add_context(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Add context to vector store."""
        raise NotImplementedError

    async def batch_add(
        self,
        items: list[tuple[str, dict[str, Any]]],
    ) -> list[str]:
        """Add multiple contexts in batch."""
        raise NotImplementedError


# =============================================================================
# Pinecone Integration
# =============================================================================

class PineconeContextSource(VectorContextSource):
    """Vector context source using Pinecone."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: str = "us-west1-gcp",
        index_name: str = "autoflow-context",
    ):
        super().__init__(index_name)
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")

        if not self.api_key:
            raise ValueError("PINECONE_API_KEY must be set")

        try:
            import pinecone
            pinecone.init(api_key=self.api_key, environment=environment)

            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                )

            self.index = pinecone.Index(index_name)

        except ImportError:
            raise ImportError("pinecone-client required: pip install pinecone-client")

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ContextMatch]:
        """Search Pinecone for similar contexts."""
        try:
            # Use OpenAI embeddings for the query
            import openai
            response = openai.Embedding.create(
                input=query,
                model="text-embedding-ada-002"
            )
            query_vector = response["data"][0]["embedding"]

            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=limit,
                filter=filters,
                include_metadata=True,
            )

            matches = []
            for match in results["matches"]:
                matches.append(ContextMatch(
                    content=match["metadata"].get("content", ""),
                    similarity=match["score"],
                    metadata=match["metadata"],
                    source="pinecone",
                ))

            return matches

        except Exception as e:
            print(f"Error searching Pinecone: {e}")
            return []

    async def add_context(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Add context to Pinecone."""
        try:
            import openai
            import uuid

            # Generate embedding
            response = openai.Embedding.create(
                input=content,
                model="text-embedding-ada-002"
            )
            vector = response["data"][0]["embedding"]

            # Add content to metadata
            metadata["content"] = content
            metadata["timestamp"] = datetime.utcnow().isoformat()

            # Upsert to Pinecone
            vector_id = str(uuid.uuid4())
            self.index.upsert([(vector_id, vector, metadata)])

            return vector_id

        except Exception as e:
            print(f"Error adding context to Pinecone: {e}")
            raise


# =============================================================================
# ChromaDB Integration
# =============================================================================

class ChromaDBContextSource(VectorContextSource):
    """Vector context source using ChromaDB (local, free)."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "autoflow_context",
    ):
        super().__init__(collection_name)

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

        except ImportError:
            raise ImportError("chromadb required: pip install chromadb")

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ContextMatch]:
        """Search ChromaDB for similar contexts."""
        try:
            # For simplicity, using query_text (ChromaDB will embed automatically)
            # In production, use OpenAI embeddings for consistency
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=filters,
            )

            matches = []
            for i, content in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Convert distance to similarity

                matches.append(ContextMatch(
                    content=content,
                    similarity=similarity,
                    metadata=metadata,
                    source="chromadb",
                ))

            return matches

        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []

    async def add_context(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Add context to ChromaDB."""
        try:
            import uuid

            metadata["timestamp"] = datetime.utcnow().isoformat()

            doc_id = str(uuid.uuid4())
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id],
            )

            return doc_id

        except Exception as e:
            print(f"Error adding context to ChromaDB: {e}")
            raise

    async def batch_add(
        self,
        items: list[tuple[str, dict[str, Any]]],
    ) -> list[str]:
        """Add multiple contexts to ChromaDB in batch."""
        try:
            import uuid

            documents = [item[0] for item in items]
            metadatas = [item[1] for item in items]
            ids = [str(uuid.uuid4()) for _ in items]

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

            return ids

        except Exception as e:
            print(f"Error batch adding to ChromaDB: {e}")
            raise


# =============================================================================
# Weaviate Integration
# =============================================================================

class WeaviateContextSource(VectorContextSource):
    """Vector context source using Weaviate."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: str = "AutoFlowContext",
    ):
        super().__init__(index_name)
        self.url = url or os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")

        try:
            import weaviate
            if self.api_key:
                self.client = weaviate.Client(
                    url=self.url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=self.api_key),
                )
            else:
                self.client = weaviate.Client(url=self.url)

            # Check if class exists, create if not
            schema = self.client.schema.get()
            class_names = [c["class"] for c in schema["classes"]]

            if index_name not in class_names:
                self.client.schema.create_class({
                    "class": index_name,
                    "description": "AutoFlow context storage",
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The context content",
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "Source of the context",
                        },
                        {
                            "name": "metadata",
                            "dataType": ["object"],
                            "description": "Additional metadata",
                        },
                    ],
                    "vectorizer": "text2vec-openai",  # Use OpenAI embeddings
                })

        except ImportError:
            raise ImportError("weaviate-client required: pip install weaviate-client")

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[ContextMatch]:
        """Search Weaviate for similar contexts."""
        try:
            # Build query
            near_text = {"concepts": [query]}

            where_clause = None
            if filters:
                # Convert filters to where clause
                where_clause = {"path": ["metadata"], "operator": "Equal", "valueString": str(filters)}

            results = self.client.query.get(
                class_name=self.index_name,
                properties=["content", "source", "metadata"],
            ).with_near_text(near_text).with_limit(limit).do()

            matches = []
            for result in results["data"]["Get"][self.index_name]:
                # Weaviate doesn't directly return similarity, use _additional if available
                matches.append(ContextMatch(
                    content=result["content"],
                    similarity=1.0,  # Weaviate orders by relevance
                    metadata=result.get("metadata", {}),
                    source="weaviate",
                ))

            return matches

        except Exception as e:
            print(f"Error searching Weaviate: {e}")
            return []

    async def add_context(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Add context to Weaviate."""
        try:
            import uuid

            data_object = {
                "content": content,
                "source": "autoflow",
                "metadata": metadata,
            }

            result = self.client.data_object.create(
                data_object=data_object,
                class_name=self.index_name,
                uuid=str(uuid.uuid4()),
            )

            return result

        except Exception as e:
            print(f"Error adding context to Weaviate: {e}")
            raise


# =============================================================================
# Vector-Enhanced Context Graph Builder
# =============================================================================

class VectorEnhancedContextBuilder:
    """
    ContextGraphBuilder that enriches events with vector search results.

    This builder:
    1. Stores events in the graph
    2. Automatically adds them to vector store
    3. When ingesting, searches for similar historical context
    4. Adds the context as nodes/edges in the graph
    """

    def __init__(
        self,
        base_builder: ContextGraphBuilder,
        vector_source: VectorContextSource,
        search_threshold: float = 0.75,
    ):
        self.base_builder = base_builder
        self.vector_source = vector_source
        self.search_threshold = search_threshold

    async def build_from_events(
        self,
        events: list,
        store: GraphStore,
    ) -> list[GraphNode]:
        """Build graph from events with vector context enrichment."""

        # Build base graph
        nodes = self.base_builder.build_from_events(events, store)

        # For each event, search for similar historical context
        for event in events:
            event_type = event.name
            event_source = event.source

            # Create search query from event
            query = self._event_to_query(event)

            # Search vector store for similar contexts
            similar = await self.vector_source.search_similar(
                query=query,
                limit=3,
                filters={
                    "event_type": event_type,
                    "source": event_source,
                },
            )

            # Add similar context as nodes
            for match in similar:
                if match.similarity >= self.search_threshold:
                    context_node = GraphNode(
                        node_id=f"context:{match.metadata.get('id', 'unknown')}",
                        node_type="context",
                        properties={
                            "content": match.content,
                            "similarity": match.similarity,
                            "source": match.source,
                            "metadata": match.metadata,
                        },
                    )
                    nodes.append(context_node)

                    # Create edge from event to context
                    # (In a real implementation, you'd also add this to the store)

        return nodes

    def _event_to_query(self, event) -> str:
        """Convert event to search query for vector store."""
        parts = [
            f"{event.source}:{event.name}",
        ]

        # Add key attributes
        if event.attributes:
            for key, value in event.attributes.items():
                if isinstance(value, str) and len(value) < 100:
                    parts.append(f"{key}:{value}")

        return " ".join(parts)

    async def store_events(
        self,
        events: list,
    ) -> None:
        """Store events in vector database for future retrieval."""
        items = []
        for event in events:
            metadata = {
                "event_type": event.name,
                "source": event.source,
                "timestamp": event.timestamp.isoformat(),
                "attributes": event.attributes,
            }
            content = self._event_to_query(event)
            items.append((content, metadata))

        # Batch add to vector store
        await self.vector_source.batch_add(items)


# =============================================================================
# Example Usage
# =============================================================================

async def example_vector_context_enhancement():
    """Example of using vector database to enhance context."""

    from autoflow import AutoImproveEngine

    print("=" * 70)
    print("AutoFlow Vector Database Context Enhancement Example")
    print("=" * 70)
    print()

    # Initialize vector source (using ChromaDB for local demo)
    print("1. Initializing vector database (ChromaDB)...")
    vector_source = ChromaDBContextSource(
        persist_directory="./chroma_db",
        collection_name="autoflow_context",
    )
    print("   ✓ ChromaDB initialized")

    # Create base context builder
    base_builder = ContextGraphBuilder()

    # Create vector-enhanced builder
    enhanced_builder = VectorEnhancedContextBuilder(
        base_builder=base_builder,
        vector_source=vector_source,
        search_threshold=0.75,
    )
    print("   ✓ Vector-enhanced context builder created")

    # Populate vector store with historical data
    print("\n2. Populating vector store with historical context...")
    historical_events = [
        {
            "content": "Database connection timeout occurred",
            "metadata": {
                "event_type": "error",
                "source": "database",
                "resolution": "Increased connection pool size",
                "success_rate": 0.95,
            },
        },
        {
            "content": "API rate limit exceeded during peak hours",
            "metadata": {
                "event_type": "error",
                "source": "api",
                "resolution": "Implemented exponential backoff",
                "success_rate": 0.98,
            },
        },
        {
            "content": "Memory spike during large file processing",
            "metadata": {
                "event_type": "warning",
                "source": "worker",
                "resolution": "Implemented streaming processing",
                "success_rate": 0.99,
            },
        },
    ]

    for item in historical_events:
        await vector_source.add_context(
            content=item["content"],
            metadata=item["metadata"],
        )
    print(f"   ✓ Added {len(historical_events)} historical contexts")

    # Create new event
    print("\n3. Processing new event with context enhancement...")
    new_event = make_event(
        source="database",
        name="connection_timeout",
        attributes={
            "database": "postgres",
            "error": "timeout after 30s",
            "query": "SELECT * FROM large_table",
        },
    )

    # Search for similar historical context
    print("\n4. Searching for similar historical context...")
    similar_contexts = await vector_source.search_similar(
        query="database connection timeout error",
        limit=3,
    )

    print(f"   Found {len(similar_contexts)} similar contexts:")
    for i, ctx in enumerate(similar_contexts, 1):
        print(f"   [{i}] Similarity: {ctx.similarity:.1%}")
        print(f"       Content: {ctx.content}")
        print(f"       Resolution: {ctx.metadata.get('resolution', 'N/A')}")
        print()

    # Use the context to inform decisions
    if similar_contexts and similar_contexts[0].similarity > 0.75:
        best_match = similar_contexts[0]
        print("5. High-confidence match found!")
        print(f"   Suggested resolution: {best_match.metadata.get('resolution')}")
        print(f"   Historical success rate: {best_match.metadata.get('success_rate', 0):.0%}")
        print()
        print("   → AutoFlow can use this context to:")
        print("      - Auto-apply the known resolution")
        print("      - Skip proposals that failed historically")
        print("      - Prioritize high-success-rate solutions")


# =============================================================================
# Different Vector Database Examples
# =============================================================================

async def example_pinecone_context():
    """Example using Pinecone as vector backend."""

    if not os.getenv("PINECONE_API_KEY"):
        print("Skipping Pinecone example (PINECONE_API_KEY not set)")
        return

    print("\n" + "=" * 70)
    print("Pinecone Vector Context Example")
    print("=" * 70)

    pinecone_source = PineconeContextSource(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment="us-west1-gcp",
        index_name="autoflow-context",
    )

    # Add some context
    await pinecone_source.add_context(
        content="High error rate in payment processing",
        metadata={
            "event_type": "error",
            "source": "payment_service",
            "impact": "high",
        },
    )

    # Search for similar
    results = await pinecone_source.search_similar(
        query="payment processing failures",
        limit=5,
    )

    print(f"Found {len(results)} similar contexts")


async def example_weaviate_context():
    """Example using Weaviate as vector backend."""

    if not os.getenv("WEAVIATE_URL"):
        print("Skipping Weaviate example (WEAVIATE_URL not set)")
        return

    print("\n" + "=" * 70)
    print("Weaviate Vector Context Example")
    print("=" * 70)

    weaviate_source = WeaviateContextSource(
        url=os.getenv("WEAVIATE_URL"),
        index_name="AutoFlowContext",
    )

    # Add some context
    await weaviate_source.add_context(
        content="Memory leak in long-running workers",
        metadata={
            "event_type": "warning",
            "source": "worker",
            "severity": "medium",
        },
    )

    # Search for similar
    results = await weaviate_source.search_similar(
        query="worker memory issues",
        limit=5,
    )

    print(f"Found {len(results)} similar contexts")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run the vector database context examples."""

    # Example with ChromaDB (local, no API key needed)
    await example_vector_context_enhancement()

    # Examples with other vector databases (require API keys/running instances)
    await example_pinecone_context()
    await example_weaviate_context()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nKey Benefits of Vector Context:")
    print("  ✓ Semantic search for similar issues")
    print("  ✓ Automatic context enrichment")
    print("  ✓ Historical resolution retrieval")
    print("  ✓ Smart proposal prioritization based on past success")
    print("\nTo use in production:")
    print("  1. Set up a vector database (ChromaDB, Pinecone, Weaviate, etc.)")
    print("  2. Configure VectorContextSource with your backend")
    print("  3. Use VectorEnhancedContextBuilder in AutoFlow engine")
    print("  4. Events will be automatically enriched with relevant context")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
