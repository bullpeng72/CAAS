"""
Framework Configuration Settings

Centralized configuration for all framework components.
"""

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


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
    TEMPERATURE_CREATIVE = 0.7      # For architecture, design (system_architect, agent_designer)
    TEMPERATURE_BALANCED = 0.5      # For analysis, refinement (requirement_analyst, gap_analyzer)
    TEMPERATURE_PRECISE = 0.3       # For code generation, BMAD (code_generator, bmad/engine)
    TEMPERATURE_DEFAULT = 0.5

    # Response format
    RESPONSE_FORMAT_JSON = {"type": "json_object"}

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2

    # Token limits
    MAX_TOKENS_DEFAULT = 4096
    MAX_TOKENS_LARGE = 8192


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None


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
    index_name: str = Field(default_factory=lambda: os.getenv("VECTORDB_INDEX_NAME", "caas-vectors"))


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


class CodeGenerationConfig(BaseModel):
    """Code generation configuration"""
    output_format: OutputFormat = OutputFormat.PRODUCTION
    include_tests: bool = True
    include_docs: bool = True
    include_deployment: bool = True
    include_ci_cd: bool = True
    test_coverage_target: float = 0.8
    deployment_target: str = "docker"  # docker, kubernetes, terraform


class WorkflowConfig(BaseModel):
    """Workflow configuration"""
    enable_checkpoints: bool = True
    enable_versioning: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds
    max_parallel_agents: int = 5


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
