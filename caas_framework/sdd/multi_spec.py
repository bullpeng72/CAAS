"""
Multi-Artifact Specification Models

CrewAI 에이전트 외에 Backend, Frontend, Database 등
다양한 아티팩트의 스펙을 정의합니다.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from caas_framework.sdd.engine import CrewAISpec
from caas_framework.sdd.engine import ProjectSpec as BaseProjectSpec


class ArtifactType(str, Enum):
    """생성할 아티팩트 타입"""

    AGENT_SYSTEM = "agent_system"  # CrewAI 에이전트
    BACKEND_API = "backend_api"  # FastAPI/Flask
    FRONTEND_UI = "frontend_ui"  # Streamlit/Gradio/React
    DATABASE = "database"  # Schema/Models
    UTILITY = "utility"  # 헬퍼 함수
    CONFIG = "config"  # 설정 파일
    DEPLOYMENT = "deployment"  # Docker/K8s


class ProjectTemplate(str, Enum):
    """프로젝트 템플릿"""

    AGENT_ONLY = "agent_only"  # CrewAI만
    AGENT_WITH_API = "agent_with_api"  # CrewAI + FastAPI
    AGENT_WITH_STREAMLIT = "agent_with_streamlit"  # CrewAI + Streamlit
    FULL_STACK = "full_stack"  # CrewAI + FastAPI + React
    CHATBOT = "chatbot"  # CrewAI + Gradio


# ============================================================================
# Backend Specifications
# ============================================================================


class HTTPMethod(str, Enum):
    """HTTP 메서드"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class APIEndpoint(BaseModel):
    """API 엔드포인트 정의"""

    path: str
    method: HTTPMethod
    description: str
    summary: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class BackendFramework(str, Enum):
    """Backend 프레임워크"""

    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"


class BackendSpec(BaseModel):
    """Backend API 스펙"""

    framework: BackendFramework = BackendFramework.FASTAPI
    api_endpoints: List[APIEndpoint] = Field(default_factory=list)
    middlewares: List[str] = Field(default_factory=lambda: ["cors", "logging"])
    dependencies: List[str] = Field(default_factory=list)

    # CrewAI 통합
    agent_integration: Dict[str, str] = Field(
        default_factory=lambda: {
            "import_path": "agents.crew",
            "run_function": "run_crew",
        }
    )

    # Database 연결
    database_url: str = "sqlite:///./app.db"
    use_async: bool = True


# ============================================================================
# Frontend Specifications
# ============================================================================


class FrontendFramework(str, Enum):
    """Frontend 프레임워크"""

    STREAMLIT = "streamlit"
    GRADIO = "gradio"
    REACT = "react"
    VUE = "vue"


class UIComponentType(str, Enum):
    """UI 컴포넌트 타입"""

    TEXT_INPUT = "text_input"
    TEXT_AREA = "text_area"
    BUTTON = "button"
    SELECT = "select"
    TABLE = "table"
    CHART = "chart"
    FILE_UPLOAD = "file_upload"
    MARKDOWN = "markdown"


class UIComponent(BaseModel):
    """UI 컴포넌트 정의"""

    component_id: str
    component_type: UIComponentType
    label: str
    description: Optional[str] = None
    props: Dict[str, Any] = Field(default_factory=dict)
    validation: Optional[Dict[str, Any]] = None


class UIPage(BaseModel):
    """UI 페이지 정의"""

    name: str
    title: str
    description: Optional[str] = None
    components: List[UIComponent] = Field(default_factory=list)
    layout: str = "single_column"  # single_column, two_columns, tabs


class FrontendSpec(BaseModel):
    """Frontend UI 스펙"""

    framework: FrontendFramework = FrontendFramework.STREAMLIT
    pages: List[UIPage] = Field(default_factory=list)
    theme: Dict[str, Any] = Field(default_factory=dict)
    port: int = 8600  # Configurable frontend port (default: 8600)

    # Backend API 연결
    api_client: Dict[str, str] = Field(
        default_factory=lambda: {"base_url": "http://localhost:8000", "timeout": "30"}
    )

    # 추가 설정
    enable_auth: bool = False
    sidebar_components: List[UIComponent] = Field(default_factory=list)


# ============================================================================
# Database Specifications
# ============================================================================


class DatabaseType(str, Enum):
    """데이터베이스 타입"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class FieldType(str, Enum):
    """필드 타입"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"
    JSON = "json"


class DataField(BaseModel):
    """데이터 필드 정의"""

    name: str
    field_type: FieldType
    nullable: bool = False
    default: Optional[Any] = None
    unique: bool = False
    index: bool = False
    description: Optional[str] = None


class DataModel(BaseModel):
    """데이터 모델 정의"""

    model_name: str
    table_name: str
    fields: List[DataField]
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    indexes: List[List[str]] = Field(default_factory=list)


class DatabaseSpec(BaseModel):
    """Database 스펙"""

    db_type: DatabaseType = DatabaseType.SQLITE
    database_url: str = "sqlite:///./app.db"
    models: List[DataModel] = Field(default_factory=list)
    use_alembic: bool = True  # Migration 도구 사용 여부


# ============================================================================
# Integration & Deployment
# ============================================================================


class IntegrationType(str, Enum):
    """통합 타입"""

    API_CALL = "api_call"
    EVENT = "event"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"


class IntegrationPoint(BaseModel):
    """통합 지점 정의"""

    from_component: str
    to_component: str
    integration_type: IntegrationType
    description: str
    config: Dict[str, Any] = Field(default_factory=dict)


class DeploymentConfig(BaseModel):
    """배포 설정"""

    use_docker: bool = True
    use_docker_compose: bool = True
    use_kubernetes: bool = False

    # Docker 설정
    docker_base_image: str = "python:3.11-slim"
    docker_ports: List[int] = Field(default_factory=lambda: [8000, 8501])

    # 환경 변수
    env_vars: Dict[str, str] = Field(default_factory=dict)


# ============================================================================
# Unified Project Specification
# ============================================================================


class MultiProjectSpec(BaseModel):
    """
    통합 프로젝트 스펙

    CrewAI 에이전트뿐만 아니라 Backend, Frontend, Database 등
    전체 프로젝트 스택의 스펙을 포함합니다.
    """

    # 프로젝트 정보
    project: BaseProjectSpec

    # 프로젝트 템플릿
    template: ProjectTemplate = ProjectTemplate.AGENT_ONLY

    # 각 레이어별 스펙
    agent_spec: Optional[CrewAISpec] = None
    backend_spec: Optional[BackendSpec] = None
    frontend_spec: Optional[FrontendSpec] = None
    database_spec: Optional[DatabaseSpec] = None

    # 통합 정보
    integration_points: List[IntegrationPoint] = Field(default_factory=list)
    deployment_config: Optional[DeploymentConfig] = None

    # 추가 파일
    additional_files: Dict[str, str] = Field(
        default_factory=dict, description="추가로 생성할 파일들 {파일경로: 내용}"
    )

    # Domain Classification (for frontend/backend logic generation)
    domain_classification: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Domain classification 결과 (DomainType, confidence, etc.)",
    )

    def has_backend(self) -> bool:
        """Backend가 포함되어 있는지 확인"""
        return self.backend_spec is not None

    def has_frontend(self) -> bool:
        """Frontend가 포함되어 있는지 확인"""
        return self.frontend_spec is not None

    def has_database(self) -> bool:
        """Database가 포함되어 있는지 확인"""
        return self.database_spec is not None

    def get_all_dependencies(self) -> List[str]:
        """모든 의존성 패키지 목록 반환"""
        deps = set()

        # CrewAI 기본 의존성 (Python 3.11 필수)
        # 검증된 버전 조합으로 의존성 충돌 방지 (Python 3.11 기준)
        if self.agent_spec:
            deps.update(
                [
                    "crewai>=1.7.0,<1.8.0",
                    "crewai-tools>=1.7.0,<1.8.0",
                    "langchain>=0.3.20,<0.4.0",
                    "langchain-core>=0.3.70,<0.4.0",
                    "langchain-openai>=0.3.20,<0.4.0",
                    "openai>=1.0.0,<2.0.0",
                    "python-dotenv>=1.0.0",
                ]
            )

        # Backend 의존성
        if self.backend_spec:
            if self.backend_spec.framework == BackendFramework.FASTAPI:
                deps.update(["fastapi", "uvicorn", "pydantic"])
            elif self.backend_spec.framework == BackendFramework.FLASK:
                deps.update(["flask", "flask-cors"])

            if self.backend_spec.dependencies:
                deps.update(self.backend_spec.dependencies)

        # Frontend 의존성
        if self.frontend_spec:
            if self.frontend_spec.framework == FrontendFramework.STREAMLIT:
                deps.update(["streamlit", "requests"])
            elif self.frontend_spec.framework == FrontendFramework.GRADIO:
                deps.update(["gradio"])

        # Database 의존성
        if self.database_spec:
            deps.add("sqlalchemy")
            if self.database_spec.use_alembic:
                deps.add("alembic")

            if self.database_spec.db_type == DatabaseType.POSTGRESQL:
                deps.add("psycopg2-binary")
            elif self.database_spec.db_type == DatabaseType.MYSQL:
                deps.add("pymysql")
            elif self.database_spec.db_type == DatabaseType.MONGODB:
                deps.add("pymongo")

        return sorted(list(deps))
