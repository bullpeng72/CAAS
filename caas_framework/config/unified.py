"""
Unified Configuration System - Single Source of Truth

Combines best features from:
- app/utils/config.py: SecretManager integration, Pydantic settings
- caas_framework/config/loader.py: YAML priority system

Priority (high → low):
1. Environment variables (.env)
2. User config file (--config or .caas.yaml)
3. Project config (.caas.yaml in project root)
4. Default YAML files (caas_framework/config/defaults/)
5. Code defaults

Version: 2.0 (Redesign Phase 1)
Date: 2026-02-01
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from functools import lru_cache
import yaml

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# ============================================================================
# Helper Functions
# ============================================================================

def find_project_root() -> Path:
    """Find project root directory by looking for pyproject.toml"""
    current = Path.cwd()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env file
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


# ============================================================================
# Configuration Models
# ============================================================================

class LLMConfig(BaseModel):
    """
    LLM provider configuration

    Unified from:
    - app/utils/config.py: LLMSettings
    - caas_framework/config/settings.py: LLMConfig
    """
    # Provider settings
    provider: str = Field(
        default="openai",
        description="LLM provider: openai, anthropic, ollama, azure_openai"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model name"
    )

    # API keys (will be moved to SecretManager)
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None

    # Model parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)

    # Advanced settings
    api_base: Optional[str] = None

    # Ollama settings (from app/utils/config.py)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen3:8b")

    class Config:
        extra = "ignore"


class GraphConfig(BaseModel):
    """
    Graph database configuration

    Unified from:
    - app/utils/config.py: Neo4jSettings
    - caas_framework/config/settings.py: GraphConfig
    """
    # Backend selection
    backend: str = Field(
        default="embedded",
        description="Graph backend: neo4j, arangodb, embedded"
    )

    # Neo4j settings
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: SecretStr = Field(default="password")
    neo4j_database: str = Field(default="neo4j")

    # Embedded graph settings
    embedded_storage: str = Field(default="./data/embedded_graph.json")

    class Config:
        extra = "ignore"


class MCPConfig(BaseModel):
    """
    MCP (Model Context Protocol) configuration

    From: app/utils/config.py: MCPSettings
    """
    enabled: bool = Field(default=False)
    transport_type: str = Field(default="http")  # stdio, sse, http
    server_url: str = Field(default="http://localhost:3000")
    server_command: str = Field(default="python3")
    server_args: str = Field(default="")
    connect_timeout: int = Field(default=30)
    tools: str = Field(default="")

    @property
    def tools_list(self) -> List[str]:
        """Parse comma-separated tools into list"""
        if not self.tools:
            return []
        return [tool.strip() for tool in self.tools.split(",") if tool.strip()]

    @property
    def server_args_list(self) -> List[str]:
        """Parse comma-separated args into list"""
        if not self.server_args:
            return []
        return [arg.strip() for arg in self.server_args.split(",") if arg.strip()]

    class Config:
        extra = "ignore"


class VectorDBConfig(BaseModel):
    """
    Vector database configuration

    From: caas_framework/config/settings.py: VectorDBConfig
    """
    backend: Optional[str] = None  # pinecone, qdrant, chroma, weaviate
    api_key: Optional[SecretStr] = None
    environment: Optional[str] = None
    index_name: str = Field(default="caas-vectors")

    class Config:
        extra = "ignore"


class ValidationConfig(BaseModel):
    """
    Validation configuration

    From: caas_framework/config/settings.py: ValidationConfig
    """
    enabled: bool = True
    strictness: str = Field(default="medium")  # low, medium, high
    auto_fix: bool = True
    max_fix_iterations: int = 5
    confidence_threshold: float = 0.8
    enable_golden_data_validation: bool = True
    enable_ontology_validation: bool = True
    enable_dependency_validation: bool = True

    class Config:
        extra = "ignore"


class CodeGenerationConfig(BaseModel):
    """
    Code generation configuration

    From: caas_framework/config/settings.py: CodeGenerationConfig
    """
    output_format: str = Field(default="production")  # basic, production, enterprise
    include_tests: bool = True
    include_docs: bool = True
    include_deployment: bool = True
    include_ci_cd: bool = True
    test_coverage_target: float = 0.8
    deployment_target: str = Field(default="docker")

    class Config:
        extra = "ignore"


class WorkflowConfig(BaseModel):
    """
    Workflow configuration

    From: caas_framework/config/settings.py: WorkflowConfig
    """
    enable_checkpoints: bool = True
    enable_versioning: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds
    max_parallel_agents: int = 5

    class Config:
        extra = "ignore"


class ArtifactConfig(BaseModel):
    """
    Artifact generation configuration

    Unified from:
    - app/utils/config.py: ArtifactSettings
    - caas_framework/config/settings.py: ArtifactConfig
    """
    # Master switch
    enabled: bool = Field(default=True)

    # Individual artifact types
    generate_project_proposal: bool = True
    generate_requirements_spec: bool = True
    generate_architecture_design: bool = True
    generate_data_design: bool = True
    generate_api_design: bool = False
    generate_agent_design: bool = True
    generate_test_plan: bool = False
    generate_test_report: bool = False
    generate_code_review: bool = False
    generate_deployment_guide: bool = False

    # Output settings
    output_format: str = Field(default="markdown")  # markdown, html, pdf, json
    output_dir: str = Field(default="./artifacts")

    # Additional options
    include_diagrams: bool = True
    include_code_samples: bool = True
    language: str = Field(default="ko")

    class Config:
        extra = "ignore"


class AppConfig(BaseModel):
    """
    Application-level configuration

    From: app/utils/config.py: AppSettings
    """
    app_name: str = Field(default="CAAS")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")

    # Streamlit settings (if using web UI)
    streamlit_server_port: int = Field(default=8501)
    streamlit_server_address: str = Field(default="localhost")

    # Directories
    output_dir: str = Field(default="./generated")
    template_dir: str = Field(default="./data/templates")
    data_dir: Optional[str] = None

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    class Config:
        extra = "ignore"


class CaaSConfig(BaseModel):
    """
    **SINGLE SOURCE OF TRUTH**

    Master configuration combining all components.

    Replaces:
    - app/utils/config.py: Settings
    - caas_framework/config/: FrameworkConfig

    Usage:
        >>> from caas_framework.config import get_config
        >>> config = get_config()
        >>> config.llm.model
        'gpt-4o-mini'
    """

    # Core components
    llm: LLMConfig = Field(default_factory=LLMConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    vectordb: Optional[VectorDBConfig] = None

    # Features
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    codegen: CodeGenerationConfig = Field(default_factory=CodeGenerationConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)

    # Application
    app: AppConfig = Field(default_factory=AppConfig)

    # Paths
    project_root: Path = Field(default=PROJECT_ROOT)

    # Metadata
    project_name: Optional[str] = None
    environment: str = Field(default="development")

    class Config:
        extra = "allow"  # For future extensibility
        arbitrary_types_allowed = True  # For Path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    def __repr__(self) -> str:
        return (
            f"<CaaSConfig("
            f"llm={self.llm.provider}/{self.llm.model}, "
            f"graph={self.graph.backend}, "
            f"env={self.environment})>"
        )


# ============================================================================
# Configuration Loader with Priority System
# ============================================================================

class UnifiedConfigLoader:
    """
    Unified configuration loader with priority cascade

    Priority (high → low):
    1. Environment variables (.env) - HIGHEST
    2. User config file (--config parameter)
    3. Project config (.caas.yaml in project root)
    4. Default YAML files (caas_framework/config/defaults/)
    5. Code defaults - LOWEST

    Features from both systems:
    - app/utils/config.py: SecretManager integration
    - caas_framework/config/loader.py: YAML priority handling
    """

    def __init__(
        self,
        config_file: Optional[Path] = None,
        use_secrets: bool = True
    ):
        """
        Initialize unified config loader

        Args:
            config_file: Optional path to user config file
            use_secrets: Whether to use SecretManager for API keys
        """
        self.config_file = config_file
        self.use_secrets = use_secrets
        self._config_data: Dict[str, Any] = {}
        self._load_all_sources()

    def _load_all_sources(self):
        """Load config from all sources with priority"""
        # 1. Load defaults from YAML files
        self._load_defaults()

        # 2. Override with project .caas.yaml
        project_config = PROJECT_ROOT / ".caas.yaml"
        if project_config.exists():
            self._merge_yaml(project_config)

        # 3. Override with user config file
        if self.config_file and self.config_file.exists():
            self._merge_yaml(self.config_file)

        # 4. Environment variables handled by Pydantic

    def _load_defaults(self):
        """Load default configuration from defaults/ directory"""
        defaults_dir = Path(__file__).parent / "defaults"
        if not defaults_dir.exists():
            return

        for yaml_file in sorted(defaults_dir.glob("*.yaml")):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    self._merge_dict(self._config_data, data)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

    def _merge_yaml(self, yaml_path: Path):
        """Load and merge YAML file into config"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self._merge_dict(self._config_data, data)
        except Exception as e:
            print(f"Warning: Failed to load {yaml_path}: {e}")

    @staticmethod
    def _merge_dict(base: Dict, update: Dict):
        """Deep merge update dict into base dict"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                UnifiedConfigLoader._merge_dict(base[key], value)
            else:
                base[key] = value

    def load(self, **overrides) -> CaaSConfig:
        """
        Load complete configuration

        Args:
            **overrides: Additional overrides to apply

        Returns:
            CaaSConfig instance
        """
        # Build config dict with all sources
        config_dict = self._config_data.copy()

        # Apply environment variables and overrides
        config_dict.update(overrides)

        # Create CaaSConfig instance (Pydantic handles env vars)
        config = self._build_config(config_dict)

        # Handle secrets if enabled
        if self.use_secrets:
            self._handle_secrets(config)

        return config

    def _build_config(self, config_dict: Dict) -> CaaSConfig:
        """Build CaaSConfig from config dictionary"""
        # Extract sub-configs
        llm_dict = config_dict.get("llm", {})
        graph_dict = config_dict.get("graph", {})
        mcp_dict = config_dict.get("mcp", {})
        vectordb_dict = config_dict.get("vectordb", {})
        validation_dict = config_dict.get("validation", {})
        codegen_dict = config_dict.get("codegen", {})
        workflow_dict = config_dict.get("workflow", {})
        artifacts_dict = config_dict.get("artifacts", {})
        app_dict = config_dict.get("app", {})

        # Override with environment variables (highest priority)
        self._apply_env_overrides(llm_dict, graph_dict, mcp_dict, app_dict, artifacts_dict)

        # Build config
        return CaaSConfig(
            llm=LLMConfig(**llm_dict) if llm_dict else LLMConfig(),
            graph=GraphConfig(**graph_dict) if graph_dict else GraphConfig(),
            mcp=MCPConfig(**mcp_dict) if mcp_dict else MCPConfig(),
            vectordb=VectorDBConfig(**vectordb_dict) if vectordb_dict else None,
            validation=ValidationConfig(**validation_dict) if validation_dict else ValidationConfig(),
            codegen=CodeGenerationConfig(**codegen_dict) if codegen_dict else CodeGenerationConfig(),
            workflow=WorkflowConfig(**workflow_dict) if workflow_dict else WorkflowConfig(),
            artifacts=ArtifactConfig(**artifacts_dict) if artifacts_dict else ArtifactConfig(),
            app=AppConfig(**app_dict) if app_dict else AppConfig(),
            project_root=PROJECT_ROOT,
            project_name=os.getenv("PROJECT_NAME"),
            environment=os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
        )

    @staticmethod
    def _apply_env_overrides(llm_dict, graph_dict, mcp_dict, app_dict, artifacts_dict):
        """Apply environment variable overrides"""
        # LLM
        if os.getenv("LLM_PROVIDER"):
            llm_dict["provider"] = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL") or os.getenv("DEFAULT_LLM_MODEL"):
            llm_dict["model"] = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_LLM_MODEL")
        if os.getenv("OPENAI_API_KEY"):
            llm_dict["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("ANTHROPIC_API_KEY"):
            llm_dict["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")

        # Graph
        if os.getenv("GRAPH_BACKEND"):
            graph_dict["backend"] = os.getenv("GRAPH_BACKEND")
        if os.getenv("NEO4J_URI"):
            graph_dict["neo4j_uri"] = os.getenv("NEO4J_URI")
        if os.getenv("NEO4J_USER"):
            graph_dict["neo4j_user"] = os.getenv("NEO4J_USER")
        if os.getenv("NEO4J_PASSWORD"):
            graph_dict["neo4j_password"] = os.getenv("NEO4J_PASSWORD")

        # MCP
        if os.getenv("MCP_ENABLED"):
            mcp_dict["enabled"] = os.getenv("MCP_ENABLED").lower() == "true"

        # App
        if os.getenv("APP_ENV"):
            app_dict["app_env"] = os.getenv("APP_ENV")
        if os.getenv("LOG_LEVEL"):
            app_dict["log_level"] = os.getenv("LOG_LEVEL")
        if os.getenv("OUTPUT_DIR"):
            app_dict["output_dir"] = os.getenv("OUTPUT_DIR")

        # Artifacts
        if os.getenv("ARTIFACT_GENERATION_ENABLED"):
            artifacts_dict["enabled"] = os.getenv("ARTIFACT_GENERATION_ENABLED").lower() == "true"
        if os.getenv("ARTIFACT_OUTPUT_DIR"):
            artifacts_dict["output_dir"] = os.getenv("ARTIFACT_OUTPUT_DIR")

    def _handle_secrets(self, config: CaaSConfig):
        """
        Move API keys to SecretManager for security

        From: app/utils/config.py pattern
        """
        try:
            from app.utils.secrets import get_secret_manager
            secret_manager = get_secret_manager()

            # Move OpenAI key to SecretManager
            if config.llm.openai_api_key:
                secret_manager.set_secret(
                    "OPENAI_API_KEY",
                    config.llm.openai_api_key.get_secret_value()
                )
                config.llm.openai_api_key = None

            # Move Anthropic key to SecretManager
            if config.llm.anthropic_api_key:
                secret_manager.set_secret(
                    "ANTHROPIC_API_KEY",
                    config.llm.anthropic_api_key.get_secret_value()
                )
                config.llm.anthropic_api_key = None

            # Move Neo4j password to SecretManager
            if config.graph.neo4j_password:
                secret_manager.set_secret(
                    "NEO4J_PASSWORD",
                    config.graph.neo4j_password.get_secret_value()
                )
                # Keep password in config for framework use, but secured

        except ImportError:
            # SecretManager not available, skip
            pass


# ============================================================================
# Global Instance (Singleton Pattern)
# ============================================================================

_config_instance: Optional[CaaSConfig] = None
_loader_instance: Optional[UnifiedConfigLoader] = None


@lru_cache(maxsize=1)
def get_config(
    config_file: Optional[Path] = None,
    force_reload: bool = False,
    **overrides
) -> CaaSConfig:
    """
    **PRIMARY ENTRY POINT**

    Get or create global configuration instance.

    Usage:
        >>> from caas_framework.config import get_config
        >>> config = get_config()
        >>> config.llm.model
        'gpt-4o-mini'

        >>> # With overrides
        >>> config = get_config(llm={"model": "gpt-4"})
        >>> config.llm.model
        'gpt-4'

    Args:
        config_file: Optional path to user config file
        force_reload: Force reload configuration
        **overrides: Additional configuration overrides

    Returns:
        CaaSConfig instance
    """
    global _config_instance, _loader_instance

    if _config_instance is None or force_reload:
        # Create loader
        _loader_instance = UnifiedConfigLoader(config_file=config_file)

        # Load config
        _config_instance = _loader_instance.load(**overrides)

    return _config_instance


def reload_config(**overrides) -> CaaSConfig:
    """
    Reload configuration (clears cache)

    Args:
        **overrides: Configuration overrides

    Returns:
        Fresh CaaSConfig instance
    """
    get_config.cache_clear()
    global _config_instance, _loader_instance
    _config_instance = None
    _loader_instance = None
    return get_config(**overrides)


# ============================================================================
# Helper Functions for Backward Compatibility
# ============================================================================

def get_api_key(key_name: str) -> Optional[str]:
    """
    Get API key from SecretManager or environment

    Backward compatible with: app/utils/config.py: get_api_key()

    Args:
        key_name: Key name (e.g., "OPENAI_API_KEY")

    Returns:
        API key value or None
    """
    try:
        from app.utils.secrets import get_secret_manager
        secret_manager = get_secret_manager()

        # Try SecretManager first
        value = secret_manager.get_secret(key_name)
        if value:
            return value
    except ImportError:
        pass

    # Fallback to environment
    return os.getenv(key_name)


def set_subprocess_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Create subprocess environment with secrets

    Backward compatible with: app/utils/config.py: set_subprocess_env()

    Args:
        base_env: Base environment dict

    Returns:
        Environment dict with secrets
    """
    env = base_env.copy() if base_env else os.environ.copy()

    try:
        from app.utils.secrets import get_secret_manager
        secret_manager = get_secret_manager()

        # Add necessary secrets
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            if secret_manager.has_secret(key):
                env.update(secret_manager.get_for_subprocess(key))
    except ImportError:
        pass

    return env


# ============================================================================
# Aliases for Backward Compatibility
# ============================================================================

# For code that imports Settings from app/utils/config
Settings = CaaSConfig
get_settings = get_config

# For code that imports FrameworkConfig from caas_framework/config
FrameworkConfig = CaaSConfig
load_config = get_config


__all__ = [
    "CaaSConfig",
    "get_config",
    "reload_config",
    "get_api_key",
    "set_subprocess_env",
    # Backward compatibility
    "Settings",
    "get_settings",
    "FrameworkConfig",
    "load_config",
]
