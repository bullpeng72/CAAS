"""
Code Analysis Models

Models for code analysis, runtime error fixing, and business logic verification.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    CRITICAL = "critical"  # Blocks execution
    HIGH = "high"  # Major functionality broken
    MEDIUM = "medium"  # Minor functionality affected
    LOW = "low"  # Cosmetic or non-critical
    INFO = "info"  # Informational only


class ErrorCategory(str, Enum):
    """Error category types"""

    SYNTAX = "syntax"  # Python syntax errors
    IMPORT = "import"  # Import/module errors
    TYPE = "type"  # Type errors
    NAME = "name"  # NameError, UnboundLocalError
    ATTRIBUTE = "attribute"  # AttributeError
    KEY = "key"  # KeyError
    INDEX = "index"  # IndexError
    VALUE = "value"  # ValueError
    RUNTIME = "runtime"  # General runtime errors
    LOGIC = "logic"  # Business logic errors
    DEPENDENCY = "dependency"  # Missing dependencies
    CONFIGURATION = "configuration"  # Configuration errors


class RuntimeErrorInfo(BaseModel):
    """Information about a runtime error"""

    error_type: str
    error_message: str
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    traceback: Optional[str] = None
    context_lines: List[str] = Field(default_factory=list)
    category: ErrorCategory = ErrorCategory.RUNTIME
    severity: ErrorSeverity = ErrorSeverity.HIGH


class CodeFix(BaseModel):
    """A code fix for an error"""

    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)  # 0.0 to 1.0


class RuntimeErrorFix(BaseModel):
    """Complete fix for a runtime error"""

    error_info: RuntimeErrorInfo
    fixes: List[CodeFix]
    root_cause: str
    fix_strategy: str
    test_command: Optional[str] = None
    additional_notes: List[str] = Field(default_factory=list)


class BusinessRuleViolation(BaseModel):
    """A violation of business rules from Golden Data"""

    rule_id: str
    feature_id: str
    feature_name: str
    violation_type: str  # "missing", "incorrect", "incomplete"
    description: str
    affected_files: List[str] = Field(default_factory=list)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    suggested_fix: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)


class ImplementationGap(BaseModel):
    """Gap between Golden Data requirements and actual implementation"""

    feature_id: str
    feature_name: str
    expected: str
    actual: str
    gap_type: str  # "missing", "partial", "incorrect"
    impact: str  # Description of the impact
    priority: str = "medium"  # low, medium, high, critical


class TraceabilityResult(BaseModel):
    """Result of traceability analysis"""

    feature_id: str
    feature_name: str
    is_implemented: bool
    implementation_files: List[str] = Field(default_factory=list)
    coverage_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    missing_requirements: List[str] = Field(default_factory=list)
    gaps: List[ImplementationGap] = Field(default_factory=list)


class ImplementationAnalysisResult(BaseModel):
    """Complete implementation analysis result"""

    project_name: str
    total_features: int
    implemented_features: int
    partial_features: int
    missing_features: int
    overall_coverage: float = Field(ge=0.0, le=100.0, default=0.0)
    traceability_results: List[TraceabilityResult] = Field(default_factory=list)
    business_rule_violations: List[BusinessRuleViolation] = Field(default_factory=list)
    implementation_gaps: List[ImplementationGap] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CodeAnalysisReport(BaseModel):
    """Complete code analysis report"""

    analysis_type: str  # "completeness", "runtime_error", "business_rules"
    project_path: str
    timestamp: str
    summary: Dict[str, Any] = Field(default_factory=dict)
    implementation_analysis: Optional[ImplementationAnalysisResult] = None
    runtime_error_fixes: List[RuntimeErrorFix] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
