"""
Configuration Loader

Loads configuration from multiple sources with priority:
1. Environment variables (.env) - HIGHEST PRIORITY
2. config.yaml
3. Code defaults (settings.py) - LOWEST PRIORITY (fallback)

This follows the standard 12-factor app pattern where environment variables
override configuration files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import ValidationError

from caas_framework.config.settings import (
    CodeGenerationConfig,
    FrameworkConfig,
    GraphConfig,
    LLMConfig,
    LoggingConfig,
    ValidationConfig,
    VectorDBConfig,
    WorkflowConfig,
)


class ConfigLoader:
    """
    Configuration loader with priority handling

    Priority (high to low):
    1. Environment variables (.env) - for secrets and environment-specific values
    2. config.yaml - for application logic and non-sensitive settings
    3. Code defaults - fallback values from settings.py
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader

        Args:
            config_path: Path to config.yaml (default: auto-detect)
        """
        self.config_path = config_path or self._find_config_file()
        self._config_data: Dict[str, Any] = {}
        self._load_config_file()

    def _find_config_file(self) -> Optional[str]:
        """
        Find config.yaml in project root or current directory

        Search order:
        1. Current directory: ./config.yaml
        2. Environment-specific: ./config.{ENVIRONMENT}.yaml
        3. Project root (2 levels up): ../../config.yaml
        4. Parent directory: ../config.yaml
        """
        # Try current directory
        current_dir = Path.cwd()
        config_file = current_dir / "config.yaml"
        if config_file.exists():
            return str(config_file)

        # Try environment-specific config
        env = os.getenv("ENVIRONMENT", "development")
        env_config = current_dir / f"config.{env}.yaml"
        if env_config.exists():
            return str(env_config)

        # Try project root (2 levels up from caas_framework/config)
        try:
            module_dir = Path(__file__).parent  # caas_framework/config
            project_root = module_dir.parent.parent  # caas/
            config_file = project_root / "config.yaml"
            if config_file.exists():
                return str(config_file)

            # Try environment-specific in project root
            env_config = project_root / f"config.{env}.yaml"
            if env_config.exists():
                return str(env_config)
        except (OSError, AttributeError) as e:
            # Failed to access file system or path resolution
            pass

        # Try parent directory
        parent_dir = current_dir.parent
        config_file = parent_dir / "config.yaml"
        if config_file.exists():
            return str(config_file)

        return None

    def _load_config_file(self):
        """Load config.yaml if exists"""
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_path}: {e}")
                self._config_data = {}

    def _get_with_priority(
        self,
        env_key: str,
        config_path: List[str],
        default: Any,
        type_converter: Optional[callable] = None,
    ) -> Any:
        """
        Get value with priority: env > config > default

        Args:
            env_key: Environment variable name
            config_path: Path in config dict (e.g., ['llm', 'model'])
            default: Default value
            type_converter: Function to convert string env value to correct type

        Returns:
            Value from highest priority source
        """
        # 1. Check environment variable (HIGHEST PRIORITY)
        env_value = os.getenv(env_key)
        if env_value is not None:
            if type_converter:
                try:
                    return type_converter(env_value)
                except (ValueError, TypeError):
                    pass  # Fall through to config/default
            return env_value

        # 2. Check config.yaml
        config_value = self._config_data
        for key in config_path:
            if isinstance(config_value, dict):
                config_value = config_value.get(key)
            else:
                config_value = None
                break

        if config_value is not None:
            return config_value

        # 3. Use default (LOWEST PRIORITY)
        return default

    def load(self) -> FrameworkConfig:
        """
        Load complete framework configuration

        Returns:
            FrameworkConfig instance with values from all sources

        Raises:
            ValueError: If configuration is invalid
        """
        # Build LLM config
        llm_config = LLMConfig(
            provider=self._get_with_priority("LLM_PROVIDER", ["llm", "provider"], "openai"),
            model=self._get_with_priority("LLM_MODEL", ["llm", "model"], "gpt-4o-mini"),
            temperature=self._get_with_priority(
                "LLM_TEMPERATURE", ["llm", "temperature"], 0.3, float
            ),
            max_tokens=self._get_with_priority("LLM_MAX_TOKENS", ["llm", "max_tokens"], 4096, int),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
            api_base=os.getenv("LLM_API_BASE"),
        )

        # Build Graph config
        graph_config = GraphConfig(
            backend=self._get_with_priority("GRAPH_BACKEND", ["graph", "backend"], "embedded"),
            uri=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            database=self._get_with_priority("NEO4J_DATABASE", ["graph", "database"], "neo4j"),
        )

        # Build VectorDB config (optional)
        vectordb_data = self._config_data.get("vectordb", {})
        vectordb_config = None
        if vectordb_data or os.getenv("VECTORDB_BACKEND"):
            vectordb_config = VectorDBConfig(
                backend=os.getenv("VECTORDB_BACKEND") or vectordb_data.get("backend"),
                api_key=os.getenv("PINECONE_API_KEY") or os.getenv("QDRANT_API_KEY"),
                environment=os.getenv("PINECONE_ENVIRONMENT") or vectordb_data.get("environment"),
                index_name=os.getenv("VECTORDB_INDEX_NAME", "caas-vectors"),
            )

        # Build Validation config
        validation_data = self._config_data.get("validation", {})
        validation_config = (
            ValidationConfig(**validation_data) if validation_data else ValidationConfig()
        )

        # Build CodeGeneration config
        codegen_data = self._config_data.get("codegen", {})
        codegen_config = (
            CodeGenerationConfig(**codegen_data) if codegen_data else CodeGenerationConfig()
        )

        # Build Workflow config
        workflow_data = self._config_data.get("workflow", {})
        workflow_config = WorkflowConfig(**workflow_data) if workflow_data else WorkflowConfig()

        # Build Logging config
        logging_data = self._config_data.get("logging", {})
        logging_config = LoggingConfig(**logging_data) if logging_data else LoggingConfig()

        # Build Artifact config
        from caas_framework.config.settings import ArtifactConfig

        artifact_enabled = os.getenv("ARTIFACT_GENERATION_ENABLED", "false").lower() == "true"
        artifact_config = ArtifactConfig(
            enabled=artifact_enabled,
            output_format=os.getenv("ARTIFACT_OUTPUT_FORMAT", "markdown"),
            output_dir=os.getenv("ARTIFACT_OUTPUT_DIR", "./artifacts"),
        )

        # Build complete config
        try:
            return FrameworkConfig(
                llm=llm_config,
                graph=graph_config,
                vectordb=vectordb_config,
                validation=validation_config,
                codegen=codegen_config,
                workflow=workflow_config,
                logging=logging_config,
                artifacts=artifact_config,
                template_dir=os.getenv("TEMPLATE_DIR"),
                output_dir=os.getenv("OUTPUT_DIR", "./output"),
                data_dir=os.getenv("DATA_DIR"),
                project_name=os.getenv("PROJECT_NAME"),
                environment=os.getenv("ENVIRONMENT", "development"),
            )
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")

    def get_timeout(self, timeout_type: str, default: float = 30.0) -> float:
        """
        Get timeout value from config

        Args:
            timeout_type: Type of timeout (health_check, api_request, llm_request, etc.)
            default: Default timeout if not found

        Returns:
            Timeout in seconds
        """
        # Check environment variable first
        env_key = f"TIMEOUT_{timeout_type.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            try:
                return float(env_value)
            except ValueError:
                pass

        # Check config.yaml
        timeouts = self._config_data.get("timeouts", {})
        timeout_value = timeouts.get(timeout_type)
        if timeout_value is not None:
            return float(timeout_value)

        # Use default
        return default

    def get_available_models(self, provider: str) -> List[str]:
        """
        Get available models for a provider from config

        Args:
            provider: LLM provider name (openai, anthropic, etc.)

        Returns:
            List of available model names
        """
        models = self._config_data.get("llm", {}).get("available_models", {})
        return models.get(provider, [])

    def get_ui_config(self) -> Dict[str, Any]:
        """
        Get UI configuration

        Returns:
            UI configuration dictionary
        """
        return self._config_data.get("ui", {})

    def save_config(self, updates: Dict[str, Any]) -> bool:
        """
        Save configuration updates to config.yaml

        Args:
            updates: Configuration updates to save

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.config_path:
            # Create config.yaml in current directory
            self.config_path = str(Path.cwd() / "config.yaml")

        try:
            # Merge updates with existing config
            for key, value in updates.items():
                if isinstance(value, dict) and key in self._config_data:
                    # Merge nested dict
                    self._config_data[key].update(value)
                else:
                    self._config_data[key] = value

            # Write to file
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(
    config_path: Optional[str] = None, force_reload: bool = False
) -> ConfigLoader:
    """
    Get or create global config loader

    Args:
        config_path: Optional path to config file
        force_reload: Force reload config loader

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None or force_reload:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def load_config(config_path: Optional[str] = None) -> FrameworkConfig:
    """
    Convenience function to load config

    Args:
        config_path: Optional path to config file

    Returns:
        FrameworkConfig instance
    """
    loader = get_config_loader(config_path)
    return loader.load()


# Class methods for ConfigLoader compatibility
class ConfigLoaderCompat:
    """Compatibility class providing class methods expected by framework.py"""

    @classmethod
    def from_env(cls) -> FrameworkConfig:
        """
        Load config from environment variables and config.yaml

        Returns:
            FrameworkConfig instance
        """
        return load_config()

    @classmethod
    def from_file(cls, config_path: str) -> FrameworkConfig:
        """
        Load config from specific config file

        Args:
            config_path: Path to config file

        Returns:
            FrameworkConfig instance
        """
        return load_config(config_path)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> FrameworkConfig:
        """
        Load config from dictionary

        Args:
            config_dict: Configuration dictionary

        Returns:
            FrameworkConfig instance
        """
        return FrameworkConfig.from_dict(config_dict)


# Make ConfigLoader support both instance and class methods
ConfigLoader.from_env = ConfigLoaderCompat.from_env
ConfigLoader.from_file = ConfigLoaderCompat.from_file
ConfigLoader.from_dict = ConfigLoaderCompat.from_dict
