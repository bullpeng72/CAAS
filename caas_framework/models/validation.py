"""
Validation Models

Models for validation results and reports.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass


# ==================== Validation Severity ====================

class ValidationSeverity(str, Enum):
    """검증 결과 심각도"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


# ==================== Compliance Status ====================

class ComplianceStatus(str, Enum):
    """Golden Data 준수 상태"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"


# ==================== Ontology Validation ====================

class ValidationIssue(BaseModel):
    """
    Unified Validation Issue Model

    Consolidates ValidationIssue definitions from:
    - agents/base.py
    - validation/crewai_validator.py
    - validation/python311_validator.py
    - codegen/execution_validator.py

    Supports both string severity and enum severity for backward compatibility.
    """
    # Core fields (required)
    severity: str  # "error", "warning", "info" (or ValidationSeverity enum value)
    issue_type: str  # "syntax", "import", "type", "runtime", "role", "task", "tool", etc.
    message: str

    # Context fields (optional)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    field: Optional[str] = None  # Specific field that has the issue

    # Source location (optional, for code validation)
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None

    # Fix suggestions (optional)
    suggested_fix: Optional[str] = None
    auto_fix_available: bool = False
    auto_fix_data: Optional[Dict[str, Any]] = None

    # Legacy field aliases (for backward compatibility)
    @property
    def category(self) -> str:
        """Alias for issue_type (legacy compatibility)"""
        return self.issue_type

    @property
    def suggestion(self) -> Optional[str]:
        """Alias for suggested_fix (legacy compatibility)"""
        return self.suggested_fix


class ValidationResult(BaseModel):
    """
    Unified Validation Result Model

    Consolidates ValidationResult definitions from validation modules.
    """
    is_valid: bool = True
    issues: List[ValidationIssue] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)

    @property
    def error_count(self) -> int:
        """Count of error-level issues"""
        return len([i for i in self.issues if i.severity == "error"])

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues"""
        return len([i for i in self.issues if i.severity == "warning"])

    @property
    def info_count(self) -> int:
        """Count of info-level issues"""
        return len([i for i in self.issues if i.severity == "info"])


# ==================== Golden Data Validation ====================

class MissingItem(BaseModel):
    """누락된 항목"""
    item_type: str  # "feature", "task", "component", etc.
    item_id: str
    item_name: str
    description: str
    severity: str  # "high", "medium", "low"


class ExtraItem(BaseModel):
    """추가된 항목 (hallucination)"""
    item_type: str
    item_id: str
    item_name: str
    description: str
    severity: str


class MismatchedItem(BaseModel):
    """일치하지 않는 항목"""
    item_type: str
    item_id: str
    item_name: str
    description: str
    expected: str
    actual: str
    severity: str


class GoldenValidationReport(BaseModel):
    """Golden Data 검증 리포트"""
    phase_name: str
    coverage_score: float = Field(ge=0.0, le=1.0)
    missing_items: List[MissingItem] = Field(default_factory=list)
    extra_items: List[ExtraItem] = Field(default_factory=list)
    mismatched_items: List[MismatchedItem] = Field(default_factory=list)
    compliance_status: ComplianceStatus
    needs_fixing: bool
    recommendations: List[str] = Field(default_factory=list)
    timestamp: str


# ==================== Dependency Validation ====================

@dataclass
class DependencyIssue:
    """의존성 이슈"""
    severity: str  # "error", "warning", "info"
    task_id: str
    message: str
    path: Optional[List[str]] = None
