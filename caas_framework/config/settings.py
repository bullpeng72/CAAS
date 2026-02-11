"""
Framework Configuration Settings

Centralized configuration for all framework components.
"""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from caas_framework.models.artifact_constants import get_default_artifact_types


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"


class GraphBackend(str, Enum):
    """Supported graph database backends"""

    NEO4J = "neo4j"
    ARANGODB = "arangodb"
    EMBEDDED = "embedded"


class VectorDBBackend(str, Enum):
    """Supported vector database backends"""

    PINECONE = "pinecone"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"


class ValidationStrictness(str, Enum):
    """Validation strictness level"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OutputFormat(str, Enum):
    """Code generation output format"""

    BASIC = "basic"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"


class LLMConstants:
    """
    LLM-related constants and default values.

    Consolidates hardcoded temperature and response format values
    from across the framework (10+ occurrences).
    """

    # Temperature settings by task type
    TEMPERATURE_CREATIVE = (
        0.7  # For architecture, design (system_architect, agent_designer)
    )
    TEMPERATURE_BALANCED = (
        0.5  # For analysis, refinement (requirement_analyst, gap_analyzer)
    )
    TEMPERATURE_PRECISE = 0.3  # For code generation, BMAD (code_generator, bmad/engine)
    TEMPERATURE_DEFAULT = 0.5

    # Response format
    RESPONSE_FORMAT_JSON = {"type": "json_object"}

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2

    # Token limits
    MAX_TOKENS_DEFAULT = 4096
    MAX_TOKENS_LARGE = 8192


class MultiModelConfig(BaseModel):
    """Multi-model configuration for a single model"""

    name: str  # Model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
    provider: LLMProvider  # Provider (openai, anthropic, etc.)
    model: str  # Model name
    cost_per_1k_tokens: float = 0.0  # Cost per 1000 tokens (USD)
    max_tokens: int = 4096  # Maximum tokens
    suitable_phases: List[str] = Field(
        default_factory=list
    )  # Best phases: ["DISCOVERY", "ARCHITECTURE"]
    priority: int = 1  # Higher = higher priority in fallback chain


class LLMConfig(BaseModel):
    """LLM configuration"""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Multi-model support
    enable_multi_model: bool = False
    model_selection_strategy: str = (
        "phase_based"  # phase_based, cost_optimized, performance_first, adaptive
    )
    enable_model_fallback: bool = True
    multi_models: List[MultiModelConfig] = Field(default_factory=list)


class GraphConfig(BaseModel):
    """Graph database configuration"""

    backend: GraphBackend = GraphBackend.EMBEDDED
    uri: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: str = "neo4j"


class VectorDBConfig(BaseModel):
    """Vector database configuration"""

    backend: Optional[VectorDBBackend] = None
    api_key: Optional[str] = None
    environment: Optional[str] = None
    index_name: str = Field(
        default_factory=lambda: os.getenv("VECTORDB_INDEX_NAME", "caas-vectors")
    )


class ValidationConfig(BaseModel):
    """Validation configuration"""

    enabled: bool = True  # Master switch for all validation
    strictness: ValidationStrictness = ValidationStrictness.MEDIUM
    auto_fix: bool = True
    max_fix_iterations: int = 5
    confidence_threshold: float = 0.8
    enable_golden_data_validation: bool = True
    enable_ontology_validation: bool = True
    enable_dependency_validation: bool = True

    # LLM Judge configuration
    enable_llm_judge: bool = True
    llm_judge_default_threshold: float = 7.0  # Default approval threshold (0-10)
    llm_judge_phase_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "DISCOVERY": 6.5,  # Lower threshold for discovery (exploratory phase)
            "ARCHITECTURE": 7.0,  # Standard threshold for architecture
            "DESIGN": 7.5,  # Higher threshold for design (critical for quality)
            "DEVELOPMENT": 7.0,  # Standard threshold for specs
            "DELIVERY": 8.0,  # Highest threshold for code (must be production-ready)
            "QUALITY_ASSURANCE": 7.0,  # Standard threshold for QA
        }
    )


class CodeGenerationConfig(BaseModel):
    """Code generation configuration"""

    output_format: OutputFormat = OutputFormat.PRODUCTION
    include_tests: bool = True
    include_docs: bool = True
    include_deployment: bool = True
    include_ci_cd: bool = True
    test_coverage_target: float = 0.8
    deployment_target: str = "docker"  # docker, kubernetes, terraform


class TimeoutConfig(BaseModel):
    """
    Timeout configuration for different operations.

    Realistic timeouts based on operation complexity and LLM response times.
    """

    # Phase-specific timeouts (seconds)
    phase_concretization: int = 180  # 3 minutes - Golden Data generation
    phase_discovery: int = 240  # 4 minutes - Requirements analysis
    phase_architecture: int = 300  # 5 minutes - Architecture design
    phase_design: int = 360  # 6 minutes - Agent/task design (most complex)
    phase_development: int = 180  # 3 minutes - Spec generation
    phase_delivery: int = 600  # 10 minutes - Code generation (slowest)
    phase_qa: int = 240  # 4 minutes - Quality assurance

    # LLM operation timeouts (seconds)
    llm_simple: int = 60  # Simple LLM calls
    llm_complex: int = 120  # Complex generation tasks
    llm_code_generation: int = 180  # Code generation

    # Validation timeouts (seconds)
    validation_quick: int = 30  # Quick validation checks
    validation_comprehensive: int = 90  # Full validation with Golden Data
    quality_gate: int = 45  # Quality gate evaluation

    # Feedback loop timeouts (seconds)
    feedback_iteration: int = 120  # Single refinement iteration
    feedback_total: int = 480  # Total feedback loop (4 iterations max)

    # Workflow timeouts (seconds)
    total_workflow: int = 1800  # 30 minutes - Total workflow execution


class CachingConfig(BaseModel):
    """Caching configuration"""

    enabled: bool = True
    backend: str = "in_memory"  # in_memory, file, redis (future)

    # Backend-specific settings
    cache_dir: str = ".cache"  # For file backend
    max_size_mb: int = 100  # For file backend
    max_entries: int = 1000  # For in-memory backend

    # TTL settings (seconds)
    default_ttl: int = 3600  # 1 hour
    llm_response_ttl: int = 3600  # 1 hour
    validation_ttl: int = 1800  # 30 minutes
    golden_data_ttl: int = 7200  # 2 hours
    phase_output_ttl: int = 3600  # 1 hour

    # Features
    enable_llm_cache: bool = True
    enable_validation_cache: bool = True
    enable_metrics: bool = True


class WorkflowConfig(BaseModel):
    """Workflow configuration"""

    enable_checkpoints: bool = True
    enable_versioning: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds (deprecated - use CachingConfig)
    max_parallel_agents: int = 5

    # Timeout configuration
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)

    # Caching configuration
    caching: CachingConfig = Field(default_factory=CachingConfig)


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: str = "INFO"
    format: str = "json"  # json or text
    output: str = "console"  # console, file, both


class ArtifactConfig(BaseModel):
    """Artifact generation configuration"""

    enabled: bool = False
    output_format: str = "markdown"  # markdown, html, pdf, json
    output_dir: str = "./artifacts"

    class Config:
        extra = "allow"


class FrameworkConfig(BaseModel):
    """
    Complete framework configuration

    Example:
        >>> config = FrameworkConfig(
        ...     llm=LLMConfig(provider="openai", model="gpt-4"),
        ...     graph=GraphConfig(backend="neo4j"),
        ...     validation=ValidationConfig(auto_fix=True)
        ... )
    """

    # Core components
    llm: LLMConfig = Field(default_factory=LLMConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    vectordb: Optional[VectorDBConfig] = None

    # Features
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    codegen: CodeGenerationConfig = Field(default_factory=CodeGenerationConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)

    # Paths
    template_dir: Optional[str] = None
    output_dir: str = "./output"
    data_dir: Optional[str] = None

    # Metadata
    project_name: Optional[str] = None
    environment: str = "development"  # development, staging, production

    class Config:
        extra = "allow"  # Allow extra fields for extensibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrameworkConfig":
        """Create from dictionary"""
        return cls(**data)

    def __repr__(self) -> str:
        return (
            f"<FrameworkConfig("
            f"llm={self.llm.provider}, "
            f"graph={self.graph.backend}, "
            f"auto_fix={self.validation.auto_fix})>"
        )


# =============================================================================
# Settings
# Provides pydantic-settings based configuration with .env file support
# =============================================================================


# Find project root
def find_project_root() -> Path:
    """Find project root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env file
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


class LLMSettings(BaseSettings):
    """LLM related settings (compatible with caas_app)"""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # OpenAI
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )

    # Anthropic
    anthropic_api_key: Optional[str] = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="qwen3:8b",
        validation_alias="OLLAMA_MODEL",
    )

    def get_openai_api_key(self) -> str:
        """Get OpenAI API key."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set. Please set it in .env file.")
        return self.openai_api_key

    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Please set it in .env file.")
        return self.anthropic_api_key


class MCPSettings(BaseSettings):
    """MCP (Model Context Protocol) settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_enabled: bool = Field(default=False, alias="MCP_ENABLED")
    mcp_transport_type: str = Field(default="http", alias="MCP_TRANSPORT_TYPE")
    mcp_server_url: str = Field(default="http://localhost:3000", alias="MCP_SERVER_URL")
    mcp_server_command: str = Field(default="python3", alias="MCP_SERVER_COMMAND")
    mcp_server_args: str = Field(default="", alias="MCP_SERVER_ARGS")
    mcp_connect_timeout: int = Field(default=30, alias="MCP_CONNECT_TIMEOUT")
    mcp_tools: str = Field(default="", alias="MCP_TOOLS")

    @property
    def mcp_tools_list(self) -> List[str]:
        """Return MCP tools as list."""
        if not self.mcp_tools:
            return []
        return [tool.strip() for tool in self.mcp_tools.split(",") if tool.strip()]

    @property
    def mcp_server_args_list(self) -> List[str]:
        """Return MCP server args as list."""
        if not self.mcp_server_args:
            return []
        return [arg.strip() for arg in self.mcp_server_args.split(",") if arg.strip()]


class Neo4jSettings(BaseSettings):
    """Neo4j database settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    graph_backend: str = Field(default="embedded", alias="GRAPH_BACKEND")
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    embedded_graph_storage: str = Field(
        default="./data/embedded_graph.json", alias="EMBEDDED_GRAPH_STORAGE"
    )


class AppSettings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="CAAS", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Streamlit
    streamlit_server_port: int = Field(default=8501, alias="STREAMLIT_SERVER_PORT")
    streamlit_server_address: str = Field(
        default="localhost", alias="STREAMLIT_SERVER_ADDRESS"
    )

    # Directories
    output_dir: str = Field(default="./generated", alias="OUTPUT_DIR")
    template_dir: str = Field(default="./data/templates", alias="TEMPLATE_DIR")

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


class ArtifactSettings(BaseSettings):
    """
    Artifact generation settings

    ⚠️ DEPRECATED (v0.5.0): Use unified.py::ArtifactConfig instead
    This class is kept for backward compatibility and will be removed in v0.6.0

    For new code, use:
        from caas_framework.config import get_config
        config = get_config()
        artifact_config = config.artifacts
    """

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        validation_alias="ARTIFACT_GENERATION_ENABLED",
        description="Enable artifact auto-generation",
    )

    # ✅ v0.5.0: Dict-based type configuration
    # ✅ Single Source: artifact_constants.py에서 import
    types: Dict[str, bool] = Field(
        default_factory=get_default_artifact_types,
        description="타입별 생성 활성화 설정",
    )

    # ⚠️ DEPRECATED: Backward compatibility (v0.5.0)
    generate_project_proposal: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_requirements_spec: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_architecture_design: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_data_design: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_api_design: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_agent_design: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_test_plan: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_test_report: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_code_review: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )
    generate_deployment_guide: Optional[bool] = Field(
        default=None, description="[DEPRECATED] Use types dict instead"
    )

    # Output settings
    output_format: str = Field(
        default="markdown", validation_alias="ARTIFACT_OUTPUT_FORMAT"
    )
    output_directory: str = Field(
        default="./artifacts", validation_alias="ARTIFACT_OUTPUT_DIR"
    )

    # Additional options
    include_diagrams: bool = Field(default=True)
    include_code_samples: bool = Field(default=True)
    language: str = Field(default="ko")

    def __init__(self, **data):
        """
        v0.5.0: Backward compatibility for old boolean fields
        """
        old_field_mapping = {
            "generate_project_proposal": "project_proposal",
            "generate_requirements_spec": "requirements_spec",
            "generate_architecture_design": "architecture_design",
            "generate_data_design": "data_design",
            "generate_api_design": "api_design",
            "generate_agent_design": "agent_design",
            "generate_test_plan": "test_plan",
            "generate_test_report": "test_report",
            "generate_code_review": "code_review",
            "generate_deployment_guide": "deployment_guide",
        }

        # If types not provided, create default
        if "types" not in data:
            # ✅ Single Source: artifact_constants.py에서 import
            data["types"] = get_default_artifact_types()

        # Merge old fields into types
        for old_field, new_key in old_field_mapping.items():
            if old_field in data and data[old_field] is not None:
                data["types"][new_key] = data[old_field]

        super().__init__(**data)


class Settings(BaseSettings):
    """
    Unified settings class.

    Provides pydantic-settings based configuration with .env file support.

    For new code, prefer using FrameworkConfig for programmatic configuration.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    artifacts: ArtifactSettings = Field(default_factory=ArtifactSettings)

    # Project paths
    project_root: Path = PROJECT_ROOT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # SECURITY: Store API keys in SecretManager
        try:
            from caas_framework.config.secrets import get_secret_manager

            secret_manager = get_secret_manager()

            if self.llm.openai_api_key:
                secret_manager.set_secret("OPENAI_API_KEY", self.llm.openai_api_key)
                self.llm.openai_api_key = None

            if self.llm.anthropic_api_key:
                secret_manager.set_secret(
                    "ANTHROPIC_API_KEY", self.llm.anthropic_api_key
                )
                self.llm.anthropic_api_key = None
        except ImportError:
            # SecretManager not available, skip
            pass


@lru_cache()
def get_settings() -> Settings:
    """
    Return settings singleton instance.

    Returns:
        Settings: Application settings object
    """
    return Settings()


# Global settings object for convenience
settings = get_settings()


def reload_settings() -> Settings:
    """Reload settings."""
    get_settings.cache_clear()
    return get_settings()


def get_api_key(key_name: str) -> Optional[str]:
    """
    Safely retrieve API key.

    Args:
        key_name: Key name (e.g., "OPENAI_API_KEY")

    Returns:
        str: API key value or None
    """
    try:
        from caas_framework.config.secrets import get_secret_manager

        secret_manager = get_secret_manager()

        # Try SecretManager first
        value = secret_manager.get_secret(key_name)
        if value:
            return value
    except ImportError:
        pass

    # Fallback to environment variable
    env_value = os.getenv(key_name)
    if env_value:
        return env_value

    # Final fallback: read directly from .env file
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
    Create environment dict for subprocess with secrets.

    Args:
        base_env: Base environment dict

    Returns:
        dict: Environment dict with secrets
    """
    env = base_env.copy() if base_env else os.environ.copy()

    try:
        from caas_framework.config.secrets import get_secret_manager

        secret_manager = get_secret_manager()

        # Add secrets only if explicitly needed for subprocess
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            if secret_manager.has_secret(key):
                env.update(secret_manager.get_for_subprocess(key))
    except ImportError:
        pass

    return env
