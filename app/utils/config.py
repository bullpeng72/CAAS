"""
CAAS Configuration Management

환경 변수 및 설정을 관리하는 모듈입니다.
.env 파일에서 설정을 로드하고 애플리케이션 전체에서 사용할 수 있도록 합니다.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# 프로젝트 루트 디렉토리 찾기
def find_project_root() -> Path:
    """프로젝트 루트 디렉토리를 찾습니다."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env file explicitly using python-dotenv
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


class LLMSettings(BaseSettings):
    """LLM 관련 설정"""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # OpenAI 설정
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )

    # Anthropic 설정
    anthropic_api_key: Optional[str] = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )

    # 기본 LLM 설정
    default_llm_provider: str = Field(
        default="openai",
        validation_alias="DEFAULT_LLM_PROVIDER",
    )
    default_llm_model: str = Field(
        default="gpt-4-turbo-preview",
        validation_alias="DEFAULT_LLM_MODEL",
    )

    # Ollama 설정 (로컬 LLM)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="qwen3:8b",
        validation_alias="OLLAMA_MODEL",
    )
    
    def get_openai_api_key(self) -> str:
        """OpenAI API 키를 반환합니다."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 OPENAI_API_KEY를 설정해주세요."
            )
        return self.openai_api_key
    
    def get_anthropic_api_key(self) -> str:
        """Anthropic API 키를 반환합니다."""
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 ANTHROPIC_API_KEY를 설정해주세요."
            )
        return self.anthropic_api_key


class MCPSettings(BaseSettings):
    """MCP (Model Context Protocol) 설정"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MCP 활성화 여부
    mcp_enabled: bool = Field(default=False, alias="MCP_ENABLED")

    # MCP 전송 타입: stdio, sse, http
    mcp_transport_type: str = Field(default="http", alias="MCP_TRANSPORT_TYPE")

    # MCP 서버 URL (sse/http용)
    mcp_server_url: str = Field(default="http://localhost:3000", alias="MCP_SERVER_URL")

    # MCP 서버 명령어 (stdio용)
    mcp_server_command: str = Field(default="python3", alias="MCP_SERVER_COMMAND")

    # MCP 서버 인자 (stdio용, 쉼표로 구분)
    mcp_server_args: str = Field(default="", alias="MCP_SERVER_ARGS")

    # 연결 타임아웃 (초)
    mcp_connect_timeout: int = Field(default=30, alias="MCP_CONNECT_TIMEOUT")

    # 사용할 MCP 도구 목록 (쉼표로 구분)
    mcp_tools: str = Field(default="", alias="MCP_TOOLS")

    @property
    def mcp_tools_list(self) -> List[str]:
        """MCP 도구 목록을 리스트로 반환"""
        if not self.mcp_tools:
            return []
        return [tool.strip() for tool in self.mcp_tools.split(",") if tool.strip()]

    @property
    def mcp_server_args_list(self) -> List[str]:
        """MCP 서버 인자를 리스트로 반환"""
        if not self.mcp_server_args:
            return []
        return [arg.strip() for arg in self.mcp_server_args.split(",") if arg.strip()]


class Neo4jSettings(BaseSettings):
    """Neo4j 데이터베이스 설정"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 그래프 백엔드 선택: "neo4j" 또는 "embedded"
    graph_backend: str = Field(default="embedded", alias="GRAPH_BACKEND")

    # Neo4j 설정 (graph_backend="neo4j"일 때 사용)
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")

    # 임베디드 그래프 설정 (graph_backend="embedded"일 때 사용)
    embedded_graph_storage: str = Field(
        default="./data/embedded_graph.json",
        alias="EMBEDDED_GRAPH_STORAGE"
    )


class AppSettings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    app_name: str = Field(default="CAAS", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Streamlit 설정
    streamlit_server_port: int = Field(default=8501, alias="STREAMLIT_SERVER_PORT")
    streamlit_server_address: str = Field(default="localhost", alias="STREAMLIT_SERVER_ADDRESS")
    
    # 디렉토리 설정
    output_dir: str = Field(default="./generated", alias="OUTPUT_DIR")
    template_dir: str = Field(default="./data/templates", alias="TEMPLATE_DIR")
    
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


class ArtifactSettings(BaseSettings):
    """산출물 생성 설정"""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # 산출물 생성 활성화
    enabled: bool = Field(
        default=True,
        validation_alias="ARTIFACT_GENERATION_ENABLED",
        description="산출물 자동 생성 활성화"
    )

    # 생성할 산출물 타입
    generate_project_proposal: bool = Field(default=True)
    generate_requirements_spec: bool = Field(default=True)
    generate_architecture_design: bool = Field(default=True)
    generate_data_design: bool = Field(default=True)
    generate_api_design: bool = Field(default=False)
    generate_agent_design: bool = Field(default=True)
    generate_test_plan: bool = Field(default=False)
    generate_test_report: bool = Field(default=False)
    generate_code_review: bool = Field(default=False)
    generate_deployment_guide: bool = Field(default=False)

    # 출력 설정
    output_format: str = Field(
        default="markdown",
        validation_alias="ARTIFACT_OUTPUT_FORMAT"
    )
    output_directory: str = Field(
        default="./artifacts",
        validation_alias="ARTIFACT_OUTPUT_DIR"
    )

    # 추가 옵션
    include_diagrams: bool = Field(default=True)
    include_code_samples: bool = Field(default=True)
    language: str = Field(default="ko")


class Settings(BaseSettings):
    """통합 설정 클래스"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 하위 설정들
    llm: LLMSettings = Field(default_factory=LLMSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    artifacts: ArtifactSettings = Field(default_factory=ArtifactSettings)
    
    # 프로젝트 경로
    project_root: Path = PROJECT_ROOT
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # SECURITY: API 키를 os.environ 대신 SecretManager에 저장
        from app.utils.secrets import get_secret_manager
        secret_manager = get_secret_manager()

        if self.llm.openai_api_key:
            secret_manager.set_secret("OPENAI_API_KEY", self.llm.openai_api_key)
            # 인스턴스에서 제거하여 노출 방지
            self.llm.openai_api_key = None

        if self.llm.anthropic_api_key:
            secret_manager.set_secret("ANTHROPIC_API_KEY", self.llm.anthropic_api_key)
            self.llm.anthropic_api_key = None


@lru_cache()
def get_settings() -> Settings:
    """
    설정 싱글톤 인스턴스를 반환합니다.
    
    Returns:
        Settings: 애플리케이션 설정 객체
    """
    return Settings()


# 편의를 위한 전역 설정 객체
settings = get_settings()


def reload_settings() -> Settings:
    """설정을 다시 로드합니다."""
    get_settings.cache_clear()
    return get_settings()


def get_api_key(key_name: str) -> Optional[str]:
    """
    API 키를 안전하게 검색.

    Args:
        key_name: 키 이름 (예: "OPENAI_API_KEY")

    Returns:
        str: API 키 값 또는 None
    """
    from app.utils.secrets import get_secret_manager

    secret_manager = get_secret_manager()

    # SecretManager 먼저 시도
    value = secret_manager.get_secret(key_name)
    if value:
        return value

    # 환경 변수로 폴백 (하위 호환성)
    env_value = os.getenv(key_name)
    if env_value:
        return env_value

    # .env 파일에서 직접 읽기 (최종 폴백)
    if ENV_FILE.exists():
        try:
            from dotenv import dotenv_values
            env_dict = dotenv_values(ENV_FILE)
            return env_dict.get(key_name)
        except Exception:
            pass

    return None


def set_subprocess_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    필요한 비밀이 포함된 서브프로세스용 환경 dict 생성.

    Args:
        base_env: 기본 환경 dict

    Returns:
        dict: 비밀이 포함된 환경 dict
    """
    from app.utils.secrets import get_secret_manager

    env = base_env.copy() if base_env else os.environ.copy()

    secret_manager = get_secret_manager()

    # 서브프로세스에 명시적으로 필요한 경우에만 비밀 추가
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if secret_manager.has_secret(key):
            env.update(secret_manager.get_for_subprocess(key))

    return env
