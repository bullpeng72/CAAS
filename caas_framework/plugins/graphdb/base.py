"""
Graph DB Plugin Base Interface

Unified interface for all graph database providers.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from caas_framework.plugins.base import Plugin, PluginType


class GraphNode(BaseModel):
    """Graph node format"""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    """Graph relationship format"""
    id: str
    type: str
    start_node_id: str
    end_node_id: str
    properties: Optional[Dict[str, Any]] = None


class GraphQueryResult(BaseModel):
    """Graph query result"""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    records: List[Dict[str, Any]]


class GraphDBPlugin(Plugin):
    """
    Base class for Graph DB plugins

    All Graph DB providers must implement:
    - execute_query(): Run Cypher/Gremlin queries
    - create_node(): Create nodes
    - create_relationship(): Create relationships
    - find_nodes(): Search nodes
    - find_path(): Find paths between nodes
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, plugin_type=PluginType.GRAPHDB, config=config)
        self.database = config.get("database", "neo4j")

    @abstractmethod
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> GraphQueryResult:
        """
        Execute a query (Cypher, Gremlin, etc.)

        Args:
            query: Query string
            parameters: Query parameters

        Returns:
            GraphQueryResult
        """

    @abstractmethod
    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any]
    ) -> GraphNode:
        """
        Create a new node

        Args:
            labels: Node labels
            properties: Node properties

        Returns:
            Created node
        """

    @abstractmethod
    async def create_relationship(
        self,
        start_node_id: str,
        end_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> GraphRelationship:
        """
        Create a relationship between nodes

        Args:
            start_node_id: Start node ID
            end_node_id: End node ID
            relationship_type: Relationship type
            properties: Relationship properties

        Returns:
            Created relationship
        """

    @abstractmethod
    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[GraphNode]:
        """
        Find nodes by labels and properties

        Args:
            labels: Filter by labels
            properties: Filter by properties
            limit: Maximum number of results

        Returns:
            List of matching nodes
        """

    @abstractmethod
    async def find_path(
        self,
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find paths between two nodes

        Args:
            start_node_id: Start node ID
            end_node_id: End node ID
            max_depth: Maximum path depth
            relationship_types: Filter by relationship types

        Returns:
            List of paths
        """

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and its relationships

        Args:
            node_id: Node ID

        Returns:
            True if deleted
        """

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship

        Args:
            relationship_id: Relationship ID

        Returns:
            True if deleted
        """

    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """
        Get database schema

        Returns:
            Schema information (labels, relationship types, etc.)
        """

    async def health_check(self) -> bool:
        """
        Check if Graph DB is accessible

        Returns:
            True if healthy
        """
        try:
            schema = await self.get_schema()
            return schema is not None
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, database={self.database})>"
