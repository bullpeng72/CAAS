"""
CAAS Knowledge Graph Package

Neo4j 기반 Knowledge Graph 관리를 제공합니다.

주요 구성요소:
- Neo4jClient: Neo4j 데이터베이스 클라이언트
- queries: Cypher 쿼리 템플릿
- PatternMatcher: 패턴 검색 및 매칭
"""

from caas_framework.knowledge.graph.neo4j_client import (
    Neo4jClient,
    Neo4jConfig,
    seed_initial_data,
    setup_schema,
)
from caas_framework.knowledge.graph.patterns import (
    AgentPattern,
    PatternMatch,
    PatternMatcher,
    PatternType,
    TemplateInfo,
)
from caas_framework.knowledge.graph.queries import (
    AGENT_QUERIES,
    ANALYSIS_QUERIES,
    PATTERN_QUERIES,
    RELATIONSHIP_QUERIES,
    TASK_QUERIES,
    TEMPLATE_QUERIES,
    TOOL_QUERIES,
    QueryTemplate,
    get_query,
)

__all__ = [
    # Client
    "Neo4jConfig",
    "Neo4jClient",
    "setup_schema",
    "seed_initial_data",
    # Queries
    "QueryTemplate",
    "get_query",
    "AGENT_QUERIES",
    "TASK_QUERIES",
    "TOOL_QUERIES",
    "PATTERN_QUERIES",
    "TEMPLATE_QUERIES",
    "RELATIONSHIP_QUERIES",
    "ANALYSIS_QUERIES",
    # Patterns
    "PatternMatcher",
    "PatternMatch",
    "AgentPattern",
    "TemplateInfo",
    "PatternType",
]
