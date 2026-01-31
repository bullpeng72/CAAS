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
]
