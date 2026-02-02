"""
Neo4j Graph DB Plugin

Supports:
- Neo4j 4.x and 5.x
- Cypher queries
- APOC procedures
"""

import os
from typing import Any, Dict, List, Optional

from caas_framework.plugins.graphdb.base import (
    GraphDBPlugin,
    GraphNode,
    GraphQueryResult,
    GraphRelationship,
)


class Neo4jPlugin(GraphDBPlugin):
    """Neo4j Graph DB provider"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # Neo4j specific
        self.uri = config.get("uri") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = config.get("username") or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = config.get("password") or os.getenv("NEO4J_PASSWORD")
        self.database = config.get("database", "neo4j")

        self._driver = None

    async def initialize(self) -> None:
        """Initialize Neo4j driver"""
        try:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.username, self.password))

            # Verify connectivity
            await self._driver.verify_connectivity()
            self._initialized = True

        except ImportError:
            raise ImportError("Neo4j package not installed. " "Install with: pip install neo4j")

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> GraphQueryResult:
        """Execute Cypher query"""
        if not self._initialized:
            await self.initialize()

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})

            nodes = []
            relationships = []
            records = []

            async for record in result:
                # Extract nodes and relationships
                for value in record.values():
                    if hasattr(value, "labels"):  # It's a node
                        nodes.append(
                            GraphNode(
                                id=str(value.element_id),
                                labels=list(value.labels),
                                properties=dict(value.items()),
                            )
                        )
                    elif hasattr(value, "type"):  # It's a relationship
                        relationships.append(
                            GraphRelationship(
                                id=str(value.element_id),
                                type=value.type,
                                start_node_id=str(value.start_node.element_id),
                                end_node_id=str(value.end_node.element_id),
                                properties=dict(value.items()),
                            )
                        )

                # Store raw record
                records.append(dict(record))

            return GraphQueryResult(nodes=nodes, relationships=relationships, records=records)

    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> GraphNode:
        """Create a new node"""
        if not self._initialized:
            await self.initialize()

        labels_str = ":".join(labels)
        query = f"CREATE (n:{labels_str} $properties) RETURN n"

        result = await self.execute_query(query, {"properties": properties})

        if result.nodes:
            return result.nodes[0]
        else:
            raise Exception("Failed to create node")

    async def create_relationship(
        self,
        start_node_id: str,
        end_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> GraphRelationship:
        """Create a relationship between nodes"""
        if not self._initialized:
            await self.initialize()

        query = (
            """
        MATCH (a), (b)
        WHERE elementId(a) = $start_id AND elementId(b) = $end_id
        CREATE (a)-[r:"""
            + relationship_type
            + """ $properties]->(b)
        RETURN r
        """
        )

        result = await self.execute_query(
            query,
            {"start_id": start_node_id, "end_id": end_node_id, "properties": properties or {}},
        )

        if result.relationships:
            return result.relationships[0]
        else:
            raise Exception("Failed to create relationship")

    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[GraphNode]:
        """Find nodes by labels and properties"""
        if not self._initialized:
            await self.initialize()

        # Build query
        label_str = ":" + ":".join(labels) if labels else ""
        where_clauses = []

        if properties:
            for key in properties.keys():
                where_clauses.append(f"n.{key} = ${key}")

        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"MATCH (n{label_str}){where_str} RETURN n LIMIT {limit}"

        result = await self.execute_query(query, properties or {})
        return result.nodes

    async def find_path(
        self,
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find paths between two nodes"""
        if not self._initialized:
            await self.initialize()

        rel_str = ""
        if relationship_types:
            rel_str = ":" + "|".join(relationship_types)

        query = f"""
        MATCH p = shortestPath((a)-[{rel_str}*..{max_depth}]-(b))
        WHERE elementId(a) = $start_id AND elementId(b) = $end_id
        RETURN p
        """

        result = await self.execute_query(query, {"start_id": start_node_id, "end_id": end_node_id})

        paths = []
        for record in result.records:
            if "p" in record:
                path = record["p"]
                paths.append(
                    {
                        "nodes": [dict(node) for node in path.nodes],
                        "relationships": [dict(rel) for rel in path.relationships],
                        "length": len(path),
                    }
                )

        return paths

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships"""
        if not self._initialized:
            await self.initialize()

        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        DETACH DELETE n
        """

        try:
            await self.execute_query(query, {"node_id": node_id})
            return True
        except Exception:
            return False

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship"""
        if not self._initialized:
            await self.initialize()

        query = """
        MATCH ()-[r]->()
        WHERE elementId(r) = $rel_id
        DELETE r
        """

        try:
            await self.execute_query(query, {"rel_id": relationship_id})
            return True
        except Exception:
            return False

    async def get_schema(self) -> Dict[str, Any]:
        """Get database schema"""
        if not self._initialized:
            await self.initialize()

        # Get node labels
        labels_result = await self.execute_query("CALL db.labels()")
        labels = [record["label"] for record in labels_result.records]

        # Get relationship types
        types_result = await self.execute_query("CALL db.relationshipTypes()")
        relationship_types = [record["relationshipType"] for record in types_result.records]

        # Get property keys
        props_result = await self.execute_query("CALL db.propertyKeys()")
        property_keys = [record["propertyKey"] for record in props_result.records]

        return {
            "labels": labels,
            "relationship_types": relationship_types,
            "property_keys": property_keys,
        }

    async def close(self) -> None:
        """Close Neo4j driver"""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._initialized = False


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("neo4j", Neo4jPlugin)
