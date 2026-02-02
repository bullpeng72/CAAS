"""
CAAS Framework Models

Data models used throughout the framework.
"""

from caas_framework.models.analysis import (
    AgentRequirement,
    ArchitecturalPattern,
    ArchitectureDesign,
    BackendAPIRequirement,
    ComponentSpec,
    ComponentType,
    DataFlow,
    HTTPMethod,
    LLMConfigSpec,
    ProjectTemplate,
    QualityMetrics,
    RequirementAnalysis,
    TaskRequirement,
    TechnologyStack,
    UIComponentRequirement,
    UIPageRequirement,
    WorkflowType,
)
from caas_framework.models.artifact_types import (
    Artifact,
    ArtifactFormat,
    ArtifactGenerationConfig,
    ArtifactMetadata,
    ArtifactType,
)
from caas_framework.models.domain_types import DomainClassification, DomainType, ExecutionPattern
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    DataModel,
    FeatureSpec,
    NonFunctionalRequirements,
    TaskSpecModel,
)
from caas_framework.models.tool_registry import (
    MCPServerConfig,
    ToolMetadata,
    ToolRegistry,
    get_tool_registry,
)
from caas_framework.models.validation import (
    ComplianceStatus,
    DependencyIssue,
    ExtraItem,
    GoldenValidationReport,
    MismatchedItem,
    MissingItem,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

__all__ = [
    # Validation models
    "ValidationIssue",
    "ValidationSeverity",
    "ValidationResult",
    "GoldenValidationReport",
    "MissingItem",
    "ExtraItem",
    "MismatchedItem",
    "ComplianceStatus",
    "DependencyIssue",
    # Specification models
    "AgentSpecModel",
    "TaskSpecModel",
    "ConcretizedRequirement",
    "FeatureSpec",
    "DataModel",
    "NonFunctionalRequirements",
    # Artifact types (migrated from app.models)
    "ArtifactType",
    "ArtifactFormat",
    "ArtifactMetadata",
    "Artifact",
    "ArtifactGenerationConfig",
    # Domain types (migrated from app.models)
    "DomainType",
    "ExecutionPattern",
    "DomainClassification",
    # Tool registry (migrated from app.models)
    "ToolMetadata",
    "MCPServerConfig",
    "ToolRegistry",
    "get_tool_registry",
    # Analysis models (migrated from app.models.schemas)
    "RequirementAnalysis",
    "ArchitectureDesign",
    "QualityMetrics",
    "AgentRequirement",
    "TaskRequirement",
    "UIComponentRequirement",
    "UIPageRequirement",
    "BackendAPIRequirement",
    "WorkflowType",
    "ProjectTemplate",
    "HTTPMethod",
    "LLMConfigSpec",
    "ArchitecturalPattern",
    "ComponentType",
    "ComponentSpec",
    "DataFlow",
    "TechnologyStack",
]
