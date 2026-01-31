"""
Vector DB Plugin Base Interface

Unified interface for all vector database providers.
"""

import os
from abc import abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from caas_framework.plugins.base import Plugin, PluginType


class VectorDocument(BaseModel):
    """Vector document format"""
    id: str
    text: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None


class VectorSearchResult(BaseModel):
    """Vector search result"""
    id: str
    score: float
    text: str
    metadata: Optional[Dict[str, Any]] = None


class VectorDBPlugin(Plugin):
    """
    Base class for Vector DB plugins

    All Vector DB providers must implement:
    - upsert(): Add/update vectors
    - search(): Semantic search
    - delete(): Remove vectors
    - get(): Retrieve by ID
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, plugin_type=PluginType.VECTORDB, config=config)
        # Get index_name from environment variable first, then config, then default
        self.index_name = config.get("index_name") or os.getenv("VECTORDB_INDEX_NAME", "caas-vectors")
        self.dimension = config.get("dimension", 1536)  # OpenAI embedding dimension
        self.metric = config.get("metric", "cosine")  # cosine, euclidean, dot_product

    @abstractmethod
    async def upsert(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors into the database

        Args:
            documents: List of documents with embeddings
            namespace: Optional namespace for multi-tenancy

        Returns:
            Result metadata
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Metadata filter
            namespace: Optional namespace

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete vectors by ID

        Args:
            ids: List of vector IDs
            namespace: Optional namespace

        Returns:
            Delete metadata
        """
        pass

    @abstractmethod
    async def get(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> List[VectorDocument]:
        """
        Retrieve vectors by ID

        Args:
            ids: List of vector IDs
            namespace: Optional namespace

        Returns:
            List of documents
        """
        pass

    @abstractmethod
    async def create_index(self) -> bool:
        """
        Create index if it doesn't exist

        Returns:
            True if created or already exists
        """
        pass

    @abstractmethod
    async def delete_index(self) -> bool:
        """
        Delete the entire index

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics

        Returns:
            Stats dict (count, dimension, etc.)
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if Vector DB is accessible

        Returns:
            True if healthy
        """
        try:
            stats = await self.index_stats()
            return stats is not None
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, index={self.index_name})>"
