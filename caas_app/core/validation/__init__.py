"""
CAAS Validation Module

코드 및 요구사항 검증 모듈입니다.
"""

from caas_app.core.validation.traceability import (
    TraceabilityValidator,
    TraceabilityReport,
    TraceabilityIssue,
    TraceabilityIssueType,
    TraceabilitySeverity,
)

from caas_app.core.validation.design_validator import (
    DesignValidator,
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
)

__all__ = [
    "TraceabilityValidator",
    "TraceabilityReport",
    "TraceabilityIssue",
    "TraceabilityIssueType",
    "TraceabilitySeverity",
    "DesignValidator",
    "ValidationResult",
    "ValidationIssue",
    "IssueSeverity",
    "IssueCategory",
]
