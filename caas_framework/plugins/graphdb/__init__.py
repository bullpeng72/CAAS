"""
Graph DB Plugins

Supported providers:
- Neo4j (neo4j.py)
"""

from caas_framework.plugins.graphdb.base import (
    GraphDBPlugin,
    GraphNode,
    GraphQueryResult,
    GraphRelationship,
)

# Import plugins to register them
try:
    from caas_framework.plugins.graphdb.neo4j import Neo4jPlugin
except ImportError:
    Neo4jPlugin = None

__all__ = [
    "GraphDBPlugin",
    "GraphNode",
    "GraphRelationship",
    "GraphQueryResult",
    "Neo4jPlugin",
]
