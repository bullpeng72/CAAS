"""
Pinecone Vector DB Plugin

Supports:
- Pinecone serverless and pod-based indexes
- Namespaces for multi-tenancy
- Metadata filtering
"""

import os
from typing import Any, Dict, List, Optional

from caas_framework.plugins.vectordb.base import (
    VectorDBPlugin,
    VectorDocument,
    VectorSearchResult,
)


class PineconePlugin(VectorDBPlugin):
    """Pinecone Vector DB provider"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # Pinecone specific
        self.api_key = config.get("api_key") or os.getenv("PINECONE_API_KEY")
        self.environment = config.get("environment") or os.getenv(
            "PINECONE_ENVIRONMENT"
        )
        self.cloud = config.get("cloud", "aws")
        self.region = config.get("region", "us-east-1")

        self._pinecone = None
        self._index = None

    async def initialize(self) -> None:
        """Initialize Pinecone client"""
        try:
            from pinecone import Pinecone

            self._pinecone = Pinecone(api_key=self.api_key)

            # Check if index exists, create if not
            await self.create_index()

            # Connect to index
            self._index = self._pinecone.Index(self.index_name)
            self._initialized = True

        except ImportError:
            raise ImportError(
                "Pinecone package not installed. "
                "Install with: pip install pinecone-client"
            )

    async def create_index(self) -> bool:
        """Create index if it doesn't exist"""
        existing_indexes = self._pinecone.list_indexes().names()

        if self.index_name not in existing_indexes:
            self._pinecone.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.metric,
                spec={"serverless": {"cloud": self.cloud, "region": self.region}},
            )
            return True
        return False

    async def delete_index(self) -> bool:
        """Delete the entire index"""
        try:
            self._pinecone.delete_index(self.index_name)
            return True
        except Exception:
            return False

    async def index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if not self._initialized:
            await self.initialize()

        stats = self._index.describe_index_stats()
        return {
            "total_vector_count": stats.total_vector_count,
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness,
            "namespaces": stats.namespaces,
        }

    async def upsert(
        self, documents: List[VectorDocument], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert vectors into Pinecone"""
        if not self._initialized:
            await self.initialize()

        # Convert to Pinecone format
        vectors = []
        for doc in documents:
            vectors.append(
                {
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {"text": doc.text, **(doc.metadata or {})},
                }
            )

        # Upsert
        result = self._index.upsert(vectors=vectors, namespace=namespace or "")

        return {"upserted_count": result.upserted_count}

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Pinecone"""
        if not self._initialized:
            await self.initialize()

        # Query
        results = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            namespace=namespace or "",
            include_metadata=True,
        )

        # Convert to VectorSearchResult
        search_results = []
        for match in results.matches:
            search_results.append(
                VectorSearchResult(
                    id=match.id,
                    score=match.score,
                    text=match.metadata.get("text", ""),
                    metadata={k: v for k, v in match.metadata.items() if k != "text"},
                )
            )

        return search_results

    async def delete(
        self, ids: List[str], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete vectors by ID"""
        if not self._initialized:
            await self.initialize()

        self._index.delete(ids=ids, namespace=namespace or "")

        return {"deleted_ids": ids}

    async def get(
        self, ids: List[str], namespace: Optional[str] = None
    ) -> List[VectorDocument]:
        """Retrieve vectors by ID"""
        if not self._initialized:
            await self.initialize()

        result = self._index.fetch(ids=ids, namespace=namespace or "")

        documents = []
        for vector_id, vector_data in result.vectors.items():
            documents.append(
                VectorDocument(
                    id=vector_id,
                    text=vector_data.metadata.get("text", ""),
                    embedding=vector_data.values,
                    metadata={
                        k: v for k, v in vector_data.metadata.items() if k != "text"
                    },
                )
            )

        return documents

    async def close(self) -> None:
        """Close Pinecone client"""
        self._index = None
        self._pinecone = None
        self._initialized = False


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("pinecone", PineconePlugin)
