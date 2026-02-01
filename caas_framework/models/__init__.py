"""
CAAS Framework Models

Data models used throughout the framework.
"""

from caas_framework.models.validation import (
    ValidationIssue,
    ValidationSeverity,
    ValidationResult,
    GoldenValidationReport,
    MissingItem,
    ExtraItem,
    MismatchedItem,
    ComplianceStatus,
    DependencyIssue,
)

from caas_framework.models.specifications import (
    AgentSpecModel,
    TaskSpecModel,
    ConcretizedRequirement,
    FeatureSpec,
    DataModel,
    NonFunctionalRequirements,
)

from caas_framework.models.artifact_types import (
    ArtifactType,
    ArtifactFormat,
    ArtifactMetadata,
    Artifact,
    ArtifactGenerationConfig,
)

from caas_framework.models.domain_types import (
    DomainType,
    ExecutionPattern,
    DomainClassification,
)

from caas_framework.models.tool_registry import (
    ToolMetadata,
    MCPServerConfig,
    ToolRegistry,
    get_tool_registry,
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
]
