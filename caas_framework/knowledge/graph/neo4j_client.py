"""
CAAS Neo4j Client

Knowledge Graph를 위한 Neo4j 데이터베이스 클라이언트입니다.
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# 선택적 의존성
try:
    from neo4j import Driver, GraphDatabase, Session

    NEO4J_AVAILABLE = True
except ImportError as e:
    # SECURITY: 의존성 누락을 로깅하여 디버깅 용이하게 함
    import logging

    logging.getLogger("knowledge.neo4j").warning(
        f"Neo4j 드라이버를 사용할 수 없습니다: {e}. " "설치하려면: pip install neo4j"
    )
    GraphDatabase = None
    Driver = None
    Session = None
    NEO4J_AVAILABLE = False

from caas_framework.config.settings import get_settings
from caas_framework.utils.logger import LoggerMixin, get_logger
from caas_framework.utils.security import (
    sanitize_neo4j_label,
    sanitize_neo4j_property_key,
    sanitize_neo4j_relationship_type,
    validate_cypher_limit,
)

logger = get_logger("knowledge.neo4j")


class Neo4jConfig(BaseModel):
    """Neo4j 연결 설정"""

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class Neo4jClient(LoggerMixin):
    """
    Neo4j 데이터베이스 클라이언트

    Knowledge Graph 저장 및 조회를 담당합니다.
    """

    def __init__(self, config: Optional[Neo4jConfig] = None):
        if config:
            self.config = config
        else:
            try:
                settings = get_settings()
                self.config = Neo4jConfig(
                    uri=settings.neo4j.neo4j_uri,
                    user=settings.neo4j.neo4j_user,
                    password=settings.neo4j.neo4j_password,
                )
            except Exception:
                self.config = Neo4jConfig()
        self._driver = None

    @property
    def driver(self):
        """Neo4j 드라이버를 반환합니다."""
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j가 설치되지 않았습니다. pip install neo4j")
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
            )
        return self._driver

    def close(self):
        """연결을 종료합니다."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self):
        """세션 컨텍스트 매니저"""
        session = self.driver.session(database=self.config.database)
        try:
            yield session
        finally:
            session.close()

    def verify_connectivity(self) -> bool:
        """연결 상태를 확인합니다."""
        if not NEO4J_AVAILABLE:
            self.logger.warning("neo4j 패키지가 설치되지 않았습니다.")
            return False
        try:
            self.driver.verify_connectivity()
            self.logger.info("Neo4j 연결 성공")
            return True
        except Exception as e:
            self.logger.error(f"Neo4j 연결 실패: {e}")
            return False

    def run_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Cypher 쿼리를 실행합니다.

        Args:
            query: Cypher 쿼리
            parameters: 쿼리 파라미터

        Returns:
            List[Dict]: 쿼리 결과
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        노드를 생성합니다.

        Args:
            label: 노드 레이블
            properties: 노드 속성

        Returns:
            Dict: 생성된 노드

        Raises:
            ValueError: label 또는 properties가 유효하지 않은 경우
        """
        # SECURITY: label 검증
        safe_label = sanitize_neo4j_label(label)

        # SECURITY: 속성 키 검증
        for key in properties.keys():
            sanitize_neo4j_property_key(key)

        # 파라미터화된 쿼리 사용 (안전함)
        query = f"CREATE (n:{safe_label} $props) RETURN n"
        result = self.run_query(query, {"props": properties})
        return result[0] if result else {}

    def create_relationship(
        self,
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        관계를 생성합니다.

        Args:
            from_label: 시작 노드 레이블
            from_id: 시작 노드 ID
            to_label: 끝 노드 레이블
            to_id: 끝 노드 ID
            rel_type: 관계 유형
            properties: 관계 속성

        Returns:
            bool: 성공 여부

        Raises:
            ValueError: 입력이 유효하지 않은 경우
        """
        # SECURITY: label 및 관계 타입 검증
        safe_from_label = sanitize_neo4j_label(from_label)
        safe_to_label = sanitize_neo4j_label(to_label)
        safe_rel_type = sanitize_neo4j_relationship_type(rel_type)

        # SECURITY: 속성 키가 제공된 경우 검증
        if properties:
            for key in properties.keys():
                sanitize_neo4j_property_key(key)

        # 파라미터화된 쿼리 사용 (안전함)
        query = f"""
        MATCH (a:{safe_from_label} {{id: $from_id}})
        MATCH (b:{safe_to_label} {{id: $to_id}})
        CREATE (a)-[r:{safe_rel_type} $props]->(b)
        RETURN r
        """
        result = self.run_query(
            query,
            {
                "from_id": from_id,
                "to_id": to_id,
                "props": properties or {},
            },
        )
        return len(result) > 0

    def find_nodes(
        self,
        label: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        노드를 검색합니다.

        Args:
            label: 노드 레이블
            filters: 필터 조건
            limit: 최대 결과 수

        Returns:
            List[Dict]: 검색 결과

        Raises:
            ValueError: 입력이 유효하지 않은 경우
        """
        # SECURITY: label 검증
        safe_label = sanitize_neo4j_label(label)

        # SECURITY: limit 검증
        safe_limit = validate_cypher_limit(limit)

        # WHERE 절을 안전하게 구성
        where_clause = ""
        params = {}
        if filters:
            conditions = []
            for key, value in filters.items():
                # SECURITY: 속성 키 검증
                safe_key = sanitize_neo4j_property_key(key)
                # 파라미터화된 쿼리 사용 (안전함)
                param_name = f"filter_{safe_key}"
                conditions.append(f"n.{safe_key} = ${param_name}")
                params[param_name] = value
            where_clause = "WHERE " + " AND ".join(conditions)

        # 검증된 limit와 함께 파라미터화된 쿼리 사용
        query = f"""
        MATCH (n:{safe_label})
        {where_clause}
        RETURN n
        LIMIT {safe_limit}
        """
        return self.run_query(query, params)

    def get_neighbors(
        self,
        label: str,
        node_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both",
    ) -> List[Dict[str, Any]]:
        """
        노드의 이웃을 조회합니다.

        Args:
            label: 노드 레이블
            node_id: 노드 ID
            rel_type: 관계 유형 (선택)
            direction: 방향 (in, out, both)

        Returns:
            List[Dict]: 이웃 노드 목록

        Raises:
            ValueError: 입력이 유효하지 않은 경우
        """
        # SECURITY: label 검증
        safe_label = sanitize_neo4j_label(label)

        # SECURITY: 관계 타입 검증 (제공된 경우)
        if rel_type:
            safe_rel_type = sanitize_neo4j_relationship_type(rel_type)
            rel_pattern = f"[r:{safe_rel_type}]"
        else:
            rel_pattern = "[r]"

        # SECURITY: direction 검증
        if direction not in ("in", "out", "both"):
            raise ValueError(
                f"유효하지 않은 방향 (in/out/both 중 하나여야 함): {direction}"
            )

        # direction에 따라 패턴 구성
        if direction == "out":
            pattern = f"(n:{safe_label})-{rel_pattern}->(m)"
        elif direction == "in":
            pattern = f"(n:{safe_label})<-{rel_pattern}-(m)"
        else:
            pattern = f"(n:{safe_label})-{rel_pattern}-(m)"

        # 파라미터화된 쿼리 사용 (안전함)
        query = f"""
        MATCH {pattern}
        WHERE n.id = $node_id
        RETURN m, type(r) as rel_type
        """
        return self.run_query(query, {"node_id": node_id})


# =============================================================================
# Knowledge Graph Schema Setup
# =============================================================================


def setup_schema(client: Neo4jClient):
    """
    Knowledge Graph 스키마를 설정합니다.
    인덱스 및 제약조건을 생성합니다.
    """
    schema_queries = [
        # Agent 노드 인덱스
        "CREATE INDEX agent_id IF NOT EXISTS FOR (n:Agent) ON (n.id)",
        "CREATE INDEX agent_role IF NOT EXISTS FOR (n:Agent) ON (n.role)",
        # Task 노드 인덱스
        "CREATE INDEX task_id IF NOT EXISTS FOR (n:Task) ON (n.id)",
        # Tool 노드 인덱스
        "CREATE INDEX tool_id IF NOT EXISTS FOR (n:Tool) ON (n.id)",
        # Pattern 노드 인덱스 및 제약조건
        "CREATE INDEX pattern_id IF NOT EXISTS FOR (n:Pattern) ON (n.id)",
        "CREATE INDEX pattern_name IF NOT EXISTS FOR (n:Pattern) ON (n.name)",
        "CREATE INDEX pattern_version IF NOT EXISTS FOR (n:Pattern) ON (n.version)",
        "CREATE INDEX pattern_latest IF NOT EXISTS FOR (n:Pattern) ON (n.latest)",
        # Pattern 유니크 제약조건 (id + version)
        "CREATE CONSTRAINT pattern_id_version_unique IF NOT EXISTS FOR (n:Pattern) REQUIRE (n.id, n.version) IS UNIQUE",
        # Domain 노드 인덱스
        "CREATE INDEX domain_id IF NOT EXISTS FOR (n:Domain) ON (n.id)",
        # Template 노드 인덱스
        "CREATE INDEX template_id IF NOT EXISTS FOR (n:Template) ON (n.id)",
        # CodeTemplate 노드 인덱스 및 제약조건 (새로운 노드 타입)
        "CREATE INDEX code_template_id IF NOT EXISTS FOR (n:CodeTemplate) ON (n.id)",
        "CREATE INDEX code_template_language IF NOT EXISTS FOR (n:CodeTemplate) ON (n.language)",
        "CREATE CONSTRAINT code_template_id_unique IF NOT EXISTS FOR (n:CodeTemplate) REQUIRE n.id IS UNIQUE",
    ]

    for query in schema_queries:
        try:
            client.run_query(query)
        except Exception as e:
            logger.warning(f"스키마 설정 경고: {e}")

    logger.info("Knowledge Graph 스키마 설정 완료")


def seed_initial_data(client: Neo4jClient):
    """
    초기 데이터를 시딩합니다.
    기본 도메인, 도구, 패턴 등을 추가합니다.
    """
    # 기본 도메인
    domains = [
        {
            "id": "finance",
            "name": "Finance",
            "description": "Financial services and analysis",
        },
        {
            "id": "healthcare",
            "name": "Healthcare",
            "description": "Medical and health services",
        },
        {
            "id": "education",
            "name": "Education",
            "description": "Learning and training",
        },
        {
            "id": "technology",
            "name": "Technology",
            "description": "Software and IT services",
        },
        {
            "id": "marketing",
            "name": "Marketing",
            "description": "Marketing and advertising",
        },
        {"id": "research", "name": "Research", "description": "Research and analysis"},
    ]

    for domain in domains:
        client.create_node("Domain", domain)

    # 기본 도구
    tools = [
        {"id": "web_search", "name": "Web Search", "type": "builtin"},
        {"id": "file_read", "name": "File Read", "type": "builtin"},
        {"id": "file_write", "name": "File Write", "type": "builtin"},
        {"id": "code_interpreter", "name": "Code Interpreter", "type": "builtin"},
        {"id": "scrape_website", "name": "Website Scraper", "type": "builtin"},
    ]

    for tool in tools:
        client.create_node("Tool", tool)

    # 기본 패턴
    patterns = [
        {
            "id": "research_report",
            "name": "Research Report Generation",
            "description": "Pattern for generating research reports",
            "use_case": "Creating comprehensive reports from research",
        },
        {
            "id": "data_etl",
            "name": "Data ETL Pipeline",
            "description": "Extract, Transform, Load pattern",
            "use_case": "Processing and transforming data",
        },
        {
            "id": "content_creation",
            "name": "Content Creation",
            "description": "Pattern for creating various content",
            "use_case": "Blog posts, articles, documentation",
        },
    ]

    for pattern in patterns:
        client.create_node("Pattern", pattern)

    logger.info("초기 데이터 시딩 완료")
