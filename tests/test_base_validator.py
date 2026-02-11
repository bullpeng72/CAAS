"""
Test suite for caas_framework/validation/base_validator.py

Tests BaseValidator abstract class and common validation patterns.
Target coverage: 95%+
"""

import pytest
from caas_framework.validation.base_validator import (
    BaseValidator,
    IssueSeverity,
    ValidationIssue,
    ValidationReport,
)


# Concrete validator for testing
class ConcreteValidator(BaseValidator):
    """Concrete implementation of BaseValidator for testing."""

    def validate(self, data: dict) -> ValidationReport:
        """Simple validation implementation."""
        issues = []

        if "error_field" in data:
            issues.append(
                self.create_issue(
                    check_name="error_check",
                    severity=IssueSeverity.ERROR,
                    message="Error field found",
                    location="data.error_field",
                )
            )

        if "warning_field" in data:
            issues.append(
                self.create_issue(
                    check_name="warning_check",
                    severity=IssueSeverity.WARNING,
                    message="Warning field found",
                    auto_fix="Remove warning_field",
                )
            )

        return self.create_report(issues)


class TestIssueSeverity:
    """Test IssueSeverity enum."""

    def test_severity_values(self):
        """Test all severity levels are defined."""
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.ERROR.value == "error"
        assert IssueSeverity.WARNING.value == "warning"
        assert IssueSeverity.INFO.value == "info"

    def test_severity_comparison(self):
        """Test severity can be compared."""
        assert IssueSeverity.CRITICAL == IssueSeverity.CRITICAL
        assert IssueSeverity.ERROR != IssueSeverity.WARNING


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_create_minimal_issue(self):
        """Test creating issue with minimal fields."""
        issue = ValidationIssue(
            check_name="test_check",
            severity=IssueSeverity.ERROR,
            message="Test error",
        )
        assert issue.check_name == "test_check"
        assert issue.severity == IssueSeverity.ERROR
        assert issue.message == "Test error"
        assert issue.location is None
        assert issue.auto_fix is None
        assert issue.details == {}

    def test_create_full_issue(self):
        """Test creating issue with all fields."""
        issue = ValidationIssue(
            check_name="test_check",
            severity=IssueSeverity.CRITICAL,
            message="Critical error",
            location="file.py:42",
            auto_fix="Fix this",
            details={"key1": "value1", "key2": 42},
        )
        assert issue.check_name == "test_check"
        assert issue.severity == IssueSeverity.CRITICAL
        assert issue.message == "Critical error"
        assert issue.location == "file.py:42"
        assert issue.auto_fix == "Fix this"
        assert issue.details["key1"] == "value1"
        assert issue.details["key2"] == 42


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_create_passing_report(self):
        """Test creating a passing report."""
        report = ValidationReport(
            validator_name="TestValidator", passed=True, issues=[], score=10.0
        )
        assert report.validator_name == "TestValidator"
        assert report.passed is True
        assert len(report.issues) == 0
        assert report.score == 10.0

    def test_has_critical_issues(self):
        """Test has_critical_issues() method."""
        critical_issue = ValidationIssue(
            check_name="test",
            severity=IssueSeverity.CRITICAL,
            message="Critical",
        )
        error_issue = ValidationIssue(
            check_name="test", severity=IssueSeverity.ERROR, message="Error"
        )

        report_with_critical = ValidationReport(
            validator_name="Test", passed=False, issues=[critical_issue, error_issue]
        )
        assert report_with_critical.has_critical_issues() is True

        report_without_critical = ValidationReport(
            validator_name="Test", passed=False, issues=[error_issue]
        )
        assert report_without_critical.has_critical_issues() is False

    def test_has_errors(self):
        """Test has_errors() method."""
        critical_issue = ValidationIssue(
            check_name="test",
            severity=IssueSeverity.CRITICAL,
            message="Critical",
        )
        error_issue = ValidationIssue(
            check_name="test", severity=IssueSeverity.ERROR, message="Error"
        )
        warning_issue = ValidationIssue(
            check_name="test",
            severity=IssueSeverity.WARNING,
            message="Warning",
        )

        report_with_errors = ValidationReport(
            validator_name="Test",
            passed=False,
            issues=[error_issue, warning_issue],
        )
        assert report_with_errors.has_errors() is True

        report_with_critical = ValidationReport(
            validator_name="Test", passed=False, issues=[critical_issue]
        )
        assert report_with_critical.has_errors() is True

        report_without_errors = ValidationReport(
            validator_name="Test", passed=True, issues=[warning_issue]
        )
        assert report_without_errors.has_errors() is False

    def test_get_issues_by_severity(self):
        """Test get_issues_by_severity() method."""
        critical_issue = ValidationIssue(
            check_name="test",
            severity=IssueSeverity.CRITICAL,
            message="Critical",
        )
        error_issue = ValidationIssue(
            check_name="test", severity=IssueSeverity.ERROR, message="Error"
        )
        warning_issue = ValidationIssue(
            check_name="test",
            severity=IssueSeverity.WARNING,
            message="Warning",
        )

        report = ValidationReport(
            validator_name="Test",
            passed=False,
            issues=[critical_issue, error_issue, warning_issue],
        )

        critical_issues = report.get_issues_by_severity(IssueSeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert critical_issues[0].message == "Critical"

        error_issues = report.get_issues_by_severity(IssueSeverity.ERROR)
        assert len(error_issues) == 1
        assert error_issues[0].message == "Error"

        info_issues = report.get_issues_by_severity(IssueSeverity.INFO)
        assert len(info_issues) == 0

    def test_count_by_severity(self):
        """Test count_by_severity() method."""
        issues = [
            ValidationIssue(
                check_name="test1",
                severity=IssueSeverity.CRITICAL,
                message="C1",
            ),
            ValidationIssue(
                check_name="test2",
                severity=IssueSeverity.CRITICAL,
                message="C2",
            ),
            ValidationIssue(
                check_name="test3",
                severity=IssueSeverity.ERROR,
                message="E1",
            ),
            ValidationIssue(
                check_name="test4",
                severity=IssueSeverity.WARNING,
                message="W1",
            ),
            ValidationIssue(
                check_name="test5",
                severity=IssueSeverity.WARNING,
                message="W2",
            ),
            ValidationIssue(
                check_name="test6",
                severity=IssueSeverity.WARNING,
                message="W3",
            ),
        ]

        report = ValidationReport(
            validator_name="Test", passed=False, issues=issues
        )

        counts = report.count_by_severity()
        assert counts["critical"] == 2
        assert counts["error"] == 1
        assert counts["warning"] == 3
        assert counts["info"] == 0


class TestBaseValidator:
    """Test BaseValidator abstract class."""

    def test_init_default_name(self):
        """Test validator initialization with default name."""
        validator = ConcreteValidator()
        assert validator.name == "ConcreteValidator"

    def test_init_custom_name(self):
        """Test validator initialization with custom name."""
        validator = ConcreteValidator(name="CustomValidator")
        assert validator.name == "CustomValidator"

    def test_create_issue_minimal(self):
        """Test create_issue() with minimal parameters."""
        validator = ConcreteValidator()
        issue = validator.create_issue(
            check_name="test_check",
            severity=IssueSeverity.ERROR,
            message="Test error",
        )

        assert issue.check_name == "test_check"
        assert issue.severity == IssueSeverity.ERROR
        assert issue.message == "Test error"
        assert issue.location is None
        assert issue.auto_fix is None

    def test_create_issue_with_location(self):
        """Test create_issue() with location."""
        validator = ConcreteValidator()
        issue = validator.create_issue(
            check_name="test_check",
            severity=IssueSeverity.WARNING,
            message="Test warning",
            location="file.py:100",
        )

        assert issue.location == "file.py:100"

    def test_create_issue_with_auto_fix(self):
        """Test create_issue() with auto_fix."""
        validator = ConcreteValidator()
        issue = validator.create_issue(
            check_name="test_check",
            severity=IssueSeverity.ERROR,
            message="Test error",
            auto_fix="Fix by doing X",
        )

        assert issue.auto_fix == "Fix by doing X"

    def test_create_issue_with_details(self):
        """Test create_issue() with additional details."""
        validator = ConcreteValidator()
        issue = validator.create_issue(
            check_name="test_check",
            severity=IssueSeverity.INFO,
            message="Test info",
            detail1="value1",
            detail2=42,
        )

        assert issue.details["detail1"] == "value1"
        assert issue.details["detail2"] == 42

    def test_calculate_score_no_issues(self):
        """Test calculate_score() with no issues."""
        validator = ConcreteValidator()
        score = validator.calculate_score([])
        assert score == 10.0

    def test_calculate_score_critical_issues(self):
        """Test calculate_score() with critical issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.CRITICAL,
                message="C1",
            ),
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.CRITICAL,
                message="C2",
            ),
        ]
        score = validator.calculate_score(issues)
        assert score == 4.0  # 10.0 - 3.0 - 3.0 = 4.0

    def test_calculate_score_error_issues(self):
        """Test calculate_score() with error issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.ERROR,
                message="E1",
            ),
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.ERROR,
                message="E2",
            ),
        ]
        score = validator.calculate_score(issues)
        assert score == 6.0  # 10.0 - 2.0 - 2.0 = 6.0

    def test_calculate_score_warning_issues(self):
        """Test calculate_score() with warning issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.WARNING,
                message="W1",
            ),
        ]
        score = validator.calculate_score(issues)
        assert score == 9.0  # 10.0 - 1.0 = 9.0

    def test_calculate_score_info_issues(self):
        """Test calculate_score() with info issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.INFO,
                message="I1",
            ),
        ]
        score = validator.calculate_score(issues)
        assert score == 9.5  # 10.0 - 0.5 = 9.5

    def test_calculate_score_mixed_issues(self):
        """Test calculate_score() with mixed severity issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.CRITICAL,
                message="C",
            ),  # -3.0
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.ERROR,
                message="E",
            ),  # -2.0
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.WARNING,
                message="W",
            ),  # -1.0
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.INFO,
                message="I",
            ),  # -0.5
        ]
        score = validator.calculate_score(issues)
        assert score == 3.5  # 10.0 - 3.0 - 2.0 - 1.0 - 0.5 = 3.5

    def test_calculate_score_minimum_zero(self):
        """Test calculate_score() doesn't go below 0.0."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name=f"test{i}",
                severity=IssueSeverity.CRITICAL,
                message=f"C{i}",
            )
            for i in range(10)  # 10 critical = -30.0
        ]
        score = validator.calculate_score(issues)
        assert score == 0.0  # Can't go below 0.0

    def test_create_report_auto_detect_passed(self):
        """Test create_report() auto-detects passed status."""
        validator = ConcreteValidator()

        # No issues -> passed
        report1 = validator.create_report([])
        assert report1.passed is True

        # Only warnings -> passed
        report2 = validator.create_report(
            [
                ValidationIssue(
                    check_name="test",
                    severity=IssueSeverity.WARNING,
                    message="W",
                )
            ]
        )
        assert report2.passed is True

        # Error -> failed
        report3 = validator.create_report(
            [
                ValidationIssue(
                    check_name="test",
                    severity=IssueSeverity.ERROR,
                    message="E",
                )
            ]
        )
        assert report3.passed is False

        # Critical -> failed
        report4 = validator.create_report(
            [
                ValidationIssue(
                    check_name="test",
                    severity=IssueSeverity.CRITICAL,
                    message="C",
                )
            ]
        )
        assert report4.passed is False

    def test_create_report_override_passed(self):
        """Test create_report() with explicit passed override."""
        validator = ConcreteValidator()

        # Force passed even with errors (for testing)
        report = validator.create_report(
            [
                ValidationIssue(
                    check_name="test",
                    severity=IssueSeverity.ERROR,
                    message="E",
                )
            ],
            passed=True,
        )
        assert report.passed is True

    def test_create_report_with_metadata(self):
        """Test create_report() with metadata."""
        validator = ConcreteValidator()
        metadata = {"test_key": "test_value", "count": 42}

        report = validator.create_report([], metadata=metadata)
        assert report.metadata["test_key"] == "test_value"
        assert report.metadata["count"] == 42

    def test_create_report_calculates_score(self):
        """Test create_report() auto-calculates score."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test",
                severity=IssueSeverity.ERROR,
                message="E",
            )
        ]

        report = validator.create_report(issues)
        assert report.score == 8.0  # 10.0 - 2.0

    def test_format_report_no_issues(self):
        """Test format_report() with no issues."""
        validator = ConcreteValidator()
        report = ValidationReport(
            validator_name="TestValidator", passed=True, issues=[], score=10.0
        )

        formatted = validator.format_report(report)
        assert "TestValidator VALIDATION REPORT" in formatted
        assert "✅ PASSED" in formatted
        assert "Score: 10.0/10.0" in formatted
        assert "No issues found" in formatted

    def test_format_report_with_issues(self):
        """Test format_report() with various issues."""
        validator = ConcreteValidator()
        issues = [
            ValidationIssue(
                check_name="test1",
                severity=IssueSeverity.CRITICAL,
                message="Critical issue",
            ),
            ValidationIssue(
                check_name="test2",
                severity=IssueSeverity.ERROR,
                message="Error issue",
            ),
            ValidationIssue(
                check_name="test3",
                severity=IssueSeverity.WARNING,
                message="Warning issue",
            ),
        ]

        report = ValidationReport(
            validator_name="TestValidator", passed=False, issues=issues, score=4.0
        )

        formatted = validator.format_report(report)
        assert "❌ FAILED" in formatted
        assert "Score: 4.0/10.0" in formatted
        assert "🔴 CRITICAL (1)" in formatted
        assert "❌ ERRORS (1)" in formatted
        assert "⚠️  WARNINGS (1)" in formatted
        assert "Critical issue" in formatted
        assert "Error issue" in formatted
        assert "Warning issue" in formatted

    def test_concrete_validator_no_issues(self):
        """Test ConcreteValidator with clean data."""
        validator = ConcreteValidator()
        data = {"clean_field": "value"}

        report = validator.validate(data)
        assert report.passed is True
        assert len(report.issues) == 0
        assert report.score == 10.0

    def test_concrete_validator_with_error(self):
        """Test ConcreteValidator with error field."""
        validator = ConcreteValidator()
        data = {"error_field": "value"}

        report = validator.validate(data)
        assert report.passed is False
        assert len(report.issues) == 1
        assert report.issues[0].severity == IssueSeverity.ERROR
        assert report.score == 8.0

    def test_concrete_validator_with_warning(self):
        """Test ConcreteValidator with warning field."""
        validator = ConcreteValidator()
        data = {"warning_field": "value"}

        report = validator.validate(data)
        assert report.passed is True  # Warnings don't fail
        assert len(report.issues) == 1
        assert report.issues[0].severity == IssueSeverity.WARNING
        assert report.issues[0].auto_fix == "Remove warning_field"
        assert report.score == 9.0

    def test_concrete_validator_with_multiple_issues(self):
        """Test ConcreteValidator with multiple issues."""
        validator = ConcreteValidator()
        data = {"error_field": "value", "warning_field": "value"}

        report = validator.validate(data)
        assert report.passed is False
        assert len(report.issues) == 2
        assert report.score == 7.0  # 10.0 - 2.0 (error) - 1.0 (warning)
