"""
CAAS Graph Client Factory

설정에 따라 적절한 그래프 백엔드 (Neo4j 또는 Embedded)를 반환합니다.
"""

from typing import Union
from pathlib import Path

from app.utils.config import get_settings
from caas_framework.utils.logger import get_logger
from app.knowledge.graph.embedded_graph import EmbeddedGraphClient

logger = get_logger("knowledge.graph.factory")


def get_graph_client() -> Union[EmbeddedGraphClient, "Neo4jClient"]:
    """
    설정에 따라 그래프 클라이언트를 반환합니다.

    Returns:
        Union[EmbeddedGraphClient, Neo4jClient]: 그래프 클라이언트

    Raises:
        ValueError: 잘못된 백엔드 설정
    """
    settings = get_settings()
    backend = settings.neo4j.graph_backend.lower()

    if backend == "embedded":
        logger.info("Using embedded graph backend")
        storage_path = Path(settings.neo4j.embedded_graph_storage)
        return EmbeddedGraphClient(storage_path=storage_path)

    elif backend == "neo4j":
        logger.info("Using Neo4j graph backend")
        try:
            from app.knowledge.graph.neo4j_client import Neo4jClient
            return Neo4jClient()
        except ImportError as e:
            logger.error(f"Failed to import Neo4jClient: {e}")
            logger.warning("Falling back to embedded graph backend")
            storage_path = Path(settings.neo4j.embedded_graph_storage)
            return EmbeddedGraphClient(storage_path=storage_path)
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Falling back to embedded graph backend")
            storage_path = Path(settings.neo4j.embedded_graph_storage)
            return EmbeddedGraphClient(storage_path=storage_path)

    else:
        raise ValueError(
            f"Invalid graph backend: {backend}. Must be 'neo4j' or 'embedded'"
        )
