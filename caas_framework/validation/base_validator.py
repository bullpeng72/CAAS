"""
Base Validator (v0.5.0)

Abstract base class for all validators to eliminate code duplication.

Provides:
- Common validation patterns
- Issue creation and reporting
- Auto-fix suggestion formatting
- Logging and error handling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.utils.logger import get_logger

logger = get_logger("validation.base")


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Must fix - blocks progression
    ERROR = "error"  # Should fix - may cause failures
    WARNING = "warning"  # Nice to fix - best practices
    INFO = "info"  # Informational - suggestions


@dataclass
class ValidationIssue:
    """
    Represents a validation issue.

    Used across all validators for consistency.
    """

    check_name: str
    severity: IssueSeverity
    message: str
    location: Optional[str] = None  # File path, line number, or component ID
    auto_fix: Optional[str] = None  # Suggested fix (human-readable or code)
    details: Dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class ValidationReport:
    """
    Result of validation with issues and statistics.

    Used across all validators for consistency.
    """

    validator_name: str
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 10.0  # 0.0 - 10.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_critical_issues(self) -> bool:
        """Check if any critical issues exist."""
        return any(i.severity == IssueSeverity.CRITICAL for i in self.issues)

    def has_errors(self) -> bool:
        """Check if any errors exist."""
        return any(
            i.severity in (IssueSeverity.CRITICAL, IssueSeverity.ERROR)
            for i in self.issues
        )

    def get_issues_by_severity(self, severity: IssueSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.issues if i.severity == severity]

    def count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity."""
        return {
            "critical": len(self.get_issues_by_severity(IssueSeverity.CRITICAL)),
            "error": len(self.get_issues_by_severity(IssueSeverity.ERROR)),
            "warning": len(self.get_issues_by_severity(IssueSeverity.WARNING)),
            "info": len(self.get_issues_by_severity(IssueSeverity.INFO)),
        }


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    Provides common functionality:
    - Issue creation helpers
    - Report formatting
    - Logging
    - Score calculation
    """

    def __init__(self, name: Optional[str] = None):
        """
        Initialize validator.

        Args:
            name: Validator name (defaults to class name)
        """
        self.name = name or self.__class__.__name__
        self.logger = get_logger(f"validation.{self.name.lower()}")

    @abstractmethod
    def validate(self, *args, **kwargs) -> ValidationReport:
        """
        Perform validation.

        Must be implemented by subclasses.

        Returns:
            ValidationReport with issues and score
        """

    def create_issue(
        self,
        check_name: str,
        severity: IssueSeverity,
        message: str,
        location: Optional[str] = None,
        auto_fix: Optional[str] = None,
        **details
    ) -> ValidationIssue:
        """
        Create a validation issue with consistent formatting.

        Args:
            check_name: Name of the check that failed
            severity: Issue severity level
            message: Human-readable description
            location: Where the issue occurred
            auto_fix: Suggested fix
            **details: Additional context

        Returns:
            ValidationIssue object
        """
        issue = ValidationIssue(
            check_name=check_name,
            severity=severity,
            message=message,
            location=location,
            auto_fix=auto_fix,
            details=details,
        )

        # Log issue
        log_level = self._get_log_level(severity)
        self.logger.log(
            log_level,
            f"[{check_name}] {message}" + (f" at {location}" if location else ""),
        )

        return issue

    def create_report(
        self,
        issues: List[ValidationIssue],
        passed: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """
        Create a validation report with automatic score calculation.

        Args:
            issues: List of validation issues
            passed: Override pass/fail (default: auto-detect from issues)
            metadata: Additional information

        Returns:
            ValidationReport
        """
        # Auto-detect passed if not specified
        if passed is None:
            has_critical = any(i.severity == IssueSeverity.CRITICAL for i in issues)
            has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)
            passed = not (has_critical or has_errors)

        # Calculate score
        score = self.calculate_score(issues)

        report = ValidationReport(
            validator_name=self.name,
            passed=passed,
            issues=issues,
            score=score,
            metadata=metadata or {},
        )

        # Log summary
        severity_counts = report.count_by_severity()
        self.logger.info(
            f"{self.name} validation {'PASSED' if passed else 'FAILED'}: "
            f"score={score:.1f}/10.0, "
            f"critical={severity_counts['critical']}, "
            f"errors={severity_counts['error']}, "
            f"warnings={severity_counts['warning']}"
        )

        return report

    def calculate_score(self, issues: List[ValidationIssue]) -> float:
        """
        Calculate validation score based on issues.

        Scoring:
        - Start at 10.0
        - Critical: -3.0 each
        - Error: -2.0 each
        - Warning: -1.0 each
        - Info: -0.5 each
        - Minimum: 0.0

        Args:
            issues: List of validation issues

        Returns:
            Score from 0.0 to 10.0
        """
        score = 10.0

        for issue in issues:
            if issue.severity == IssueSeverity.CRITICAL:
                score -= 3.0
            elif issue.severity == IssueSeverity.ERROR:
                score -= 2.0
            elif issue.severity == IssueSeverity.WARNING:
                score -= 1.0
            elif issue.severity == IssueSeverity.INFO:
                score -= 0.5

        return max(0.0, score)

    def format_report(self, report: ValidationReport) -> str:
        """
        Format validation report as human-readable text.

        Args:
            report: ValidationReport to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"{report.validator_name} VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Status
        status = "✅ PASSED" if report.passed else "❌ FAILED"
        lines.append(f"Status: {status}")
        lines.append(f"Score: {report.score:.1f}/10.0")
        lines.append("")

        # Issues by severity
        severity_counts = report.count_by_severity()

        if severity_counts["critical"] > 0:
            lines.append(f"🔴 CRITICAL ({severity_counts['critical']}):")
            for issue in report.get_issues_by_severity(IssueSeverity.CRITICAL):
                lines.append(self._format_issue(issue))
            lines.append("")

        if severity_counts["error"] > 0:
            lines.append(f"❌ ERRORS ({severity_counts['error']}):")
            for issue in report.get_issues_by_severity(IssueSeverity.ERROR):
                lines.append(self._format_issue(issue))
            lines.append("")

        if severity_counts["warning"] > 0:
            lines.append(f"⚠️  WARNINGS ({severity_counts['warning']}):")
            for issue in report.get_issues_by_severity(IssueSeverity.WARNING):
                lines.append(self._format_issue(issue))
            lines.append("")

        if severity_counts["info"] > 0:
            lines.append(f"ℹ️  INFO ({severity_counts['info']}):")
            for issue in report.get_issues_by_severity(IssueSeverity.INFO):
                lines.append(self._format_issue(issue))
            lines.append("")

        if not report.issues:
            lines.append("✅ No issues found - all checks passed!")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_issue(self, issue: ValidationIssue) -> str:
        """Format a single issue."""
        lines = []

        # Main message
        location_str = f" [{issue.location}]" if issue.location else ""
        lines.append(f"  • {issue.message}{location_str}")

        # Auto-fix suggestion
        if issue.auto_fix:
            lines.append(f"    💡 Fix: {issue.auto_fix}")

        return "\n".join(lines)

    def _get_log_level(self, severity: IssueSeverity) -> int:
        """Map severity to logging level."""
        import logging

        mapping = {
            IssueSeverity.CRITICAL: logging.ERROR,
            IssueSeverity.ERROR: logging.ERROR,
            IssueSeverity.WARNING: logging.WARNING,
            IssueSeverity.INFO: logging.INFO,
        }

        return mapping.get(severity, logging.INFO)


class CompositeValidator(BaseValidator):
    """
    Composite validator that runs multiple validators.

    Useful for running all validators in sequence.
    """

    def __init__(self, validators: List[BaseValidator], name: str = "CompositeValidator"):
        """
        Initialize composite validator.

        Args:
            validators: List of validators to run
            name: Composite validator name
        """
        super().__init__(name=name)
        self.validators = validators

    def validate(self, *args, **kwargs) -> ValidationReport:
        """
        Run all validators and aggregate results.

        Returns:
            Aggregated validation report
        """
        all_issues = []
        all_passed = True

        for validator in self.validators:
            try:
                report = validator.validate(*args, **kwargs)

                all_issues.extend(report.issues)
                all_passed = all_passed and report.passed

            except Exception as e:
                self.logger.error(f"Validator {validator.name} failed: {e}")

                # Create error issue
                error_issue = self.create_issue(
                    check_name=f"{validator.name}_execution",
                    severity=IssueSeverity.ERROR,
                    message=f"Validator execution failed: {str(e)}",
                    location=validator.name,
                )
                all_issues.append(error_issue)
                all_passed = False

        return self.create_report(
            issues=all_issues,
            passed=all_passed,
            metadata={"validators_run": len(self.validators)},
        )
