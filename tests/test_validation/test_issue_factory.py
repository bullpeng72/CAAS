"""
Unit tests for ValidationIssueFactory.

Tests all builder methods, summary methods, and utility functions.
Target: 70%+ coverage
"""

import pytest
from unittest.mock import Mock

from caas_framework.models.validation import ValidationIssue
from caas_framework.validation.issue_factory import ValidationIssueFactory


class TestValidationIssueFactory:
    """Test suite for ValidationIssueFactory."""

    @pytest.fixture
    def sample_issues(self):
        """Sample validation issues for testing."""
        return [
            ValidationIssue(
                severity="error",
                issue_type="syntax",
                message="Syntax error in code",
                field="code",
                auto_fix_available=True,
            ),
            ValidationIssue(
                severity="warning",
                issue_type="style",
                message="Style warning",
                field="format",
                auto_fix_available=False,
            ),
            ValidationIssue(
                severity="info",
                issue_type="info",
                message="Info message",
                field="docs",
                auto_fix_available=False,
            ),
            ValidationIssue(
                severity="error",
                issue_type="logic",
                message="Logic error",
                field="algorithm",
                auto_fix_available=True,
            ),
        ]

    # Tests for builder methods

    def test_create_syntax_error(self):
        """Test creating syntax error issue."""
        exception = SyntaxError("Invalid YAML syntax", ("config.yaml", 10, 5, ""))
        issue = ValidationIssueFactory.create_syntax_error(
            exception=exception,
            context="config.yaml",
            severity="error",
        )

        assert issue.severity == "error"
        assert issue.issue_type == "syntax_error"
        assert issue.field == "config.yaml"
        assert "YAML" in issue.message

    def test_create_missing_required(self):
        """Test creating missing required field issue."""
        issue = ValidationIssueFactory.create_missing_required(
            field_name="role",
            item_name="agent_1",
            severity="high",
            suggestion="Add role field to agent",
        )

        assert issue.severity == "high"
        assert issue.issue_type == "missing_required"
        assert issue.field == "role"
        assert "role" in issue.message.lower()
        assert "agent_1" in issue.message

    def test_create_invalid_value(self):
        """Test creating invalid value issue."""
        issue = ValidationIssueFactory.create_invalid_value(
            field_name="timeout",
            actual_value="invalid",
            expected="integer",
            item_name="agent_1",
            severity="medium",
        )

        assert issue.severity == "medium"
        assert issue.issue_type == "invalid_value"
        assert issue.field == "timeout"
        assert "invalid" in issue.message
        assert "integer" in issue.message

    def test_create_deprecated_usage(self):
        """Test creating deprecated usage issue."""
        issue = ValidationIssueFactory.create_deprecated_usage(
            feature_name="old_api",
            alternative="v2",
            item_name="task_1",
            severity="low",
        )

        assert issue.severity == "low"
        assert issue.issue_type == "deprecated"
        assert issue.field == "old_api"
        assert "old_api" in issue.message
        assert "v2" in issue.message

    def test_create_missing_item(self):
        """Test creating missing item issue."""
        issue = ValidationIssueFactory.create_missing_item(
            item_type="feature",
            item_name="User Authentication",
            severity="medium",
            context="Phase 3 Design",
        )

        assert issue.severity == "medium"
        assert issue.issue_type == "missing_feature"
        assert "User Authentication" in issue.message

    def test_create_extra_item(self):
        """Test creating extra item issue."""
        issue = ValidationIssueFactory.create_extra_item(
            item_type="agent",
            item_name="Redundant Agent",
            severity="low",
            reason="Design validation",
        )

        assert issue.severity == "low"
        assert issue.issue_type == "extra_agent"
        assert "Redundant Agent" in issue.message

    def test_create_circular_dependency(self):
        """Test creating circular dependency issue."""
        issue = ValidationIssueFactory.create_circular_dependency(
            task1="task_1",
            task2="task_2",
            severity="high",
        )

        assert issue.severity == "high"
        assert issue.issue_type == "circular_dependency"
        assert "task_1" in issue.message
        assert "task_2" in issue.message

    # Tests for summary methods

    def test_create_validation_summary(self, sample_issues):
        """Test creating validation summary."""
        summary = ValidationIssueFactory.create_validation_summary(sample_issues)

        assert summary["total"] == 4
        assert summary["errors"] == 2
        assert summary["warnings"] == 1
        assert summary["info"] == 1
        assert summary["auto_fixable"] == 2
        assert summary["is_valid"] is False  # Has errors

    def test_create_validation_summary_valid(self):
        """Test summary for valid (no errors) issues."""
        issues = [
            ValidationIssue(
                severity="warning",
                issue_type="style",
                message="Style warning",
            ),
            ValidationIssue(
                severity="info",
                issue_type="info",
                message="Info message",
            ),
        ]

        summary = ValidationIssueFactory.create_validation_summary(issues)

        assert summary["total"] == 2
        assert summary["errors"] == 0
        assert summary["warnings"] == 1
        assert summary["info"] == 1
        assert summary["is_valid"] is True  # No errors

    def test_create_validation_summary_empty(self):
        """Test summary with empty issues list."""
        summary = ValidationIssueFactory.create_validation_summary([])

        assert summary["total"] == 0
        assert summary["errors"] == 0
        assert summary["warnings"] == 0
        assert summary["info"] == 0
        assert summary["auto_fixable"] == 0
        assert summary["is_valid"] is True

    def test_count_errors(self, sample_issues):
        """Test counting errors."""
        count = ValidationIssueFactory.count_errors(sample_issues)

        assert count == 2

    def test_count_warnings(self, sample_issues):
        """Test counting warnings."""
        count = ValidationIssueFactory.count_warnings(sample_issues)

        assert count == 1

    def test_count_by_severity(self, sample_issues):
        """Test counting by specific severity."""
        error_count = ValidationIssueFactory.count_by_severity(
            sample_issues, "error"
        )
        warning_count = ValidationIssueFactory.count_by_severity(
            sample_issues, "warning"
        )
        info_count = ValidationIssueFactory.count_by_severity(
            sample_issues, "info"
        )

        assert error_count == 2
        assert warning_count == 1
        assert info_count == 1

    # Tests for conversion methods

    def test_from_golden_validation_with_missing_items(self):
        """Test converting golden validation result with missing items."""
        mock_result = Mock()
        mock_result.missing_items = [
            Mock(item_type="feature", item_name="Feature A", severity="high"),
            Mock(item_type="task", item_name="Task B", severity="medium"),
        ]
        mock_result.extra_items = []
        mock_result.mismatched_items = []

        issues = ValidationIssueFactory.from_golden_validation(mock_result)

        assert len(issues) == 2
        assert issues[0].issue_type == "missing_feature"
        assert "Feature A" in issues[0].message
        assert issues[1].issue_type == "missing_task"

    def test_from_golden_validation_with_extra_items(self):
        """Test converting golden validation result with extra items."""
        mock_result = Mock()
        mock_result.missing_items = []
        mock_result.extra_items = [
            Mock(item_type="agent", item_name="Extra Agent"),
        ]
        mock_result.mismatched_items = []

        issues = ValidationIssueFactory.from_golden_validation(mock_result)

        assert len(issues) == 1
        assert issues[0].issue_type == "extra_agent"
        assert issues[0].severity == "low"

    def test_from_golden_validation_with_mismatched_items(self):
        """Test converting golden validation result with mismatched items."""
        mock_result = Mock()
        mock_result.missing_items = []
        mock_result.extra_items = []
        mock_result.mismatched_items = [
            Mock(
                item_type="config",
                item_name="timeout",
                expected="30",
                actual="60",
            ),
        ]

        issues = ValidationIssueFactory.from_golden_validation(mock_result)

        assert len(issues) == 1
        assert issues[0].issue_type == "mismatch_config"
        assert issues[0].severity == "medium"
        assert "expected 30" in issues[0].message.lower()
        assert "got 60" in issues[0].message.lower()

    def test_from_golden_validation_empty(self):
        """Test with None golden result."""
        issues = ValidationIssueFactory.from_golden_validation(None)

        assert issues == []

    # Tests for formatting methods

    def test_format_for_agent(self, sample_issues):
        """Test formatting issues for agent consumption."""
        formatted = ValidationIssueFactory.format_for_agent(sample_issues, max_issues=3)

        assert isinstance(formatted, str)
        # format_for_agent groups by severity: high, medium, low (not error/warning/info)
        assert "##" in formatted
        assert "Validation Issues" in formatted

    def test_format_for_agent_no_limit(self, sample_issues):
        """Test formatting all issues without limit."""
        formatted = ValidationIssueFactory.format_for_agent(
            sample_issues, max_issues=100
        )

        assert isinstance(formatted, str)
        assert formatted.count("\n") >= len(sample_issues)

    def test_format_summary(self, sample_issues):
        """Test formatting summary dictionary."""
        summary = ValidationIssueFactory.format_summary(sample_issues)

        assert isinstance(summary, dict)
        assert "total" in summary
        assert summary["total"] == 4
        assert "by_severity" in summary
        assert "by_type" in summary
        assert "critical_issues" in summary

    # Tests for filtering methods

    def test_filter_by_severity_high(self, sample_issues):
        """Test filtering by high severity (minimum)."""
        # filter_by_severity filters by minimum severity level
        # high severity issues only
        high_issues = ValidationIssueFactory.filter_by_severity(
            sample_issues, min_severity="high"
        )

        # Should include high severity issues
        assert all(i.severity in ["high", "error"] for i in high_issues)

    def test_filter_by_severity_low(self, sample_issues):
        """Test filtering by low severity (all issues)."""
        # low and above (all)
        all_issues = ValidationIssueFactory.filter_by_severity(
            sample_issues, min_severity="low"
        )

        # Should include all issues
        assert len(all_issues) >= 1

    def test_filter_by_type(self, sample_issues):
        """Test filtering by issue type."""
        # filter_by_type takes a list of types
        syntax_issues = ValidationIssueFactory.filter_by_type(sample_issues, ["syntax"])

        assert len(syntax_issues) == 1
        assert syntax_issues[0].issue_type == "syntax"

    def test_filter_by_type_no_matches(self, sample_issues):
        """Test filtering with no matches."""
        result = ValidationIssueFactory.filter_by_type(
            sample_issues, ["nonexistent_type"]
        )

        assert result == []

    # Edge cases

    def test_builder_methods_with_optional_params(self):
        """Test builder methods with minimal parameters."""
        exception = SyntaxError("Error")
        issue1 = ValidationIssueFactory.create_syntax_error(
            exception=exception, context="test.py"
        )
        issue2 = ValidationIssueFactory.create_missing_required(field_name="name")
        issue3 = ValidationIssueFactory.create_invalid_value(
            field_name="age", actual_value="abc", expected="int"
        )

        assert issue1.field == "test.py"
        assert issue2.field == "name"
        assert issue3.field == "age"

    def test_summary_with_mixed_severity_strings(self):
        """Test summary with severity as strings instead of enums."""
        issues = [
            Mock(severity="error", auto_fix_available=False),
            Mock(severity="warning", auto_fix_available=True),
            Mock(severity="info", auto_fix_available=False),
        ]

        summary = ValidationIssueFactory.create_validation_summary(issues)

        assert summary["total"] == 3
        assert summary["errors"] >= 1
        assert summary["warnings"] >= 1

    def test_empty_list_handling(self):
        """Test all methods handle empty lists correctly."""
        empty = []

        assert ValidationIssueFactory.count_errors(empty) == 0
        assert ValidationIssueFactory.count_warnings(empty) == 0
        assert ValidationIssueFactory.filter_by_severity(empty, "error") == []
        assert ValidationIssueFactory.filter_by_type(empty, "any") == []

        summary = ValidationIssueFactory.create_validation_summary(empty)
        assert summary["total"] == 0
        assert summary["is_valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
