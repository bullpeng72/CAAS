"""
Qdrant Vector DB Plugin

Supports:
- Qdrant Cloud and self-hosted
- Collections and payloads
- Advanced filtering
"""

import os
from typing import Any, Dict, List, Optional

from caas_framework.plugins.vectordb.base import VectorDBPlugin, VectorDocument, VectorSearchResult


class QdrantPlugin(VectorDBPlugin):
    """Qdrant Vector DB provider"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # Qdrant specific
        self.url = config.get("url") or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = config.get("api_key") or os.getenv("QDRANT_API_KEY")
        self.collection_name = config.get("collection_name", self.index_name)
        self.on_disk = config.get("on_disk", False)

        self._client = None

    async def initialize(self) -> None:
        """Initialize Qdrant client"""
        try:
            from qdrant_client import AsyncQdrantClient

            self._client = AsyncQdrantClient(url=self.url, api_key=self.api_key)

            # Create collection if it doesn't exist
            await self.create_index()

            self._initialized = True

        except ImportError:
            raise ImportError(
                "Qdrant package not installed. " "Install with: pip install qdrant-client"
            )

    async def create_index(self) -> bool:
        """Create collection if it doesn't exist"""
        from qdrant_client.models import Distance, VectorParams

        # Check if collection exists
        collections = await self._client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            # Map metric to Qdrant Distance
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "dot_product": Distance.DOT,
            }
            distance = distance_map.get(self.metric, Distance.COSINE)

            await self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension, distance=distance, on_disk=self.on_disk
                ),
            )
            return True
        return False

    async def delete_index(self) -> bool:
        """Delete the entire collection"""
        try:
            await self._client.delete_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False

    async def index_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self._initialized:
            await self.initialize()

        info = await self._client.get_collection(collection_name=self.collection_name)

        return {
            "total_vector_count": info.points_count,
            "dimension": info.config.params.vectors.size,
            "status": info.status,
            "optimizer_status": info.optimizer_status,
        }

    async def upsert(
        self, documents: List[VectorDocument], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert vectors into Qdrant"""
        if not self._initialized:
            await self.initialize()

        from qdrant_client.models import PointStruct

        # Convert to Qdrant format
        points = []
        for doc in documents:
            payload = {"text": doc.text, **(doc.metadata or {})}
            if namespace:
                payload["namespace"] = namespace

            points.append(PointStruct(id=doc.id, vector=doc.embedding, payload=payload))

        # Upsert
        result = await self._client.upsert(collection_name=self.collection_name, points=points)

        return {"upserted_count": len(points), "status": result.status}

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Qdrant"""
        if not self._initialized:
            await self.initialize()

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        # Build filter
        qdrant_filter = None
        if filter or namespace:
            conditions = []

            if namespace:
                conditions.append(
                    FieldCondition(key="namespace", match=MatchValue(value=namespace))
                )

            if filter:
                for key, value in filter.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

            qdrant_filter = Filter(must=conditions)

        # Search
        results = await self._client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=qdrant_filter,
        )

        # Convert to VectorSearchResult
        search_results = []
        for hit in results:
            metadata = {k: v for k, v in hit.payload.items() if k not in ["text", "namespace"]}
            search_results.append(
                VectorSearchResult(
                    id=str(hit.id),
                    score=hit.score,
                    text=hit.payload.get("text", ""),
                    metadata=metadata,
                )
            )

        return search_results

    async def delete(self, ids: List[str], namespace: Optional[str] = None) -> Dict[str, Any]:
        """Delete vectors by ID"""
        if not self._initialized:
            await self.initialize()

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        # Build filter
        qdrant_filter = None
        if namespace:
            qdrant_filter = Filter(
                must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]
            )

        # Delete points
        await self._client.delete(
            collection_name=self.collection_name, points_selector=ids, points_filter=qdrant_filter
        )

        return {"deleted_ids": ids}

    async def get(self, ids: List[str], namespace: Optional[str] = None) -> List[VectorDocument]:
        """Retrieve vectors by ID"""
        if not self._initialized:
            await self.initialize()

        # Retrieve points
        results = await self._client.retrieve(
            collection_name=self.collection_name, ids=ids, with_vectors=True, with_payload=True
        )

        # Convert to VectorDocument
        documents = []
        for point in results:
            # Filter by namespace if provided
            if namespace and point.payload.get("namespace") != namespace:
                continue

            metadata = {k: v for k, v in point.payload.items() if k not in ["text", "namespace"]}
            documents.append(
                VectorDocument(
                    id=str(point.id),
                    text=point.payload.get("text", ""),
                    embedding=point.vector,
                    metadata=metadata,
                )
            )

        return documents

    async def close(self) -> None:
        """Close Qdrant client"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("qdrant", QdrantPlugin)
