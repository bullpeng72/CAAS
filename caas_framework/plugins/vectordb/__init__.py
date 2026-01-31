"""
Vector DB Plugins

Supported providers:
- Pinecone (pinecone.py)
- Qdrant (qdrant.py)
"""

from caas_framework.plugins.vectordb.base import (
    VectorDBPlugin,
    VectorDocument,
    VectorSearchResult
)

# Import plugins to register them
try:
    from caas_framework.plugins.vectordb.pinecone import PineconePlugin
except ImportError:
    PineconePlugin = None

try:
    from caas_framework.plugins.vectordb.qdrant import QdrantPlugin
except ImportError:
    QdrantPlugin = None

__all__ = [
    "VectorDBPlugin",
    "VectorDocument",
    "VectorSearchResult",
    "PineconePlugin",
    "QdrantPlugin",
]
