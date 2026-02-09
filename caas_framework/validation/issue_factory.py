"""
ValidationIssueFactory - Unified Issue Conversion

Eliminates duplicate issue extraction logic across the codebase.
Provides consistent conversion from various validation results to ValidationIssue objects.
"""

from typing import Any, Dict, List

from caas_framework.models.validation import ValidationIssue

from caas_framework.utils.logger import get_logger

logger = get_logger(__name__)



class ValidationIssueFactory:
    """
    Factory for creating ValidationIssue objects from various sources.

    Consolidates duplicate issue extraction logic found in:
    - SafeFeedbackLoop._extract_issues() (collaboration.py:284-318)
    - ExpertAgentCollaboration._extract_validation_issues() (collaboration.py:1289-1334)
    - BaseExpertAgent._format_validation_issues() (base.py:326-352)
    """

    @staticmethod
    def from_golden_validation(golden_result) -> List[ValidationIssue]:
        """
        Convert Golden Data validation result to ValidationIssue list.

        Args:
            golden_result: GoldenValidationReport from validator

        Returns:
            List of ValidationIssue objects

        Example:
            issues = ValidationIssueFactory.from_golden_validation(validation_result.golden_result)
        """
        issues = []

        if not golden_result:
            return issues

        # Missing items (features, tasks, agents not implemented)
        if hasattr(golden_result, "missing_items"):
            for missing in golden_result.missing_items:
                item_type = (
                    missing.item_type if hasattr(missing, "item_type") else "unknown"
                )
                issues.append(
                    ValidationIssue(
                        issue_type=f"missing_{item_type}",
                        severity=missing.severity
                        if hasattr(missing, "severity")
                        else "medium",
                        message=f"Missing {item_type}: {missing.item_name if hasattr(missing, 'item_name') else str(missing)}",
                        field=f"{item_type}s",
                    )
                )

        # Extra items (unexpected implementations)
        if hasattr(golden_result, "extra_items"):
            for extra in golden_result.extra_items:
                item_type = (
                    extra.item_type if hasattr(extra, "item_type") else "unknown"
                )
                issues.append(
                    ValidationIssue(
                        issue_type=f"extra_{item_type}",
                        severity="low",
                        message=f"Extra {item_type}: {extra.item_name if hasattr(extra, 'item_name') else str(extra)} (not in requirements)",
                        field=f"{item_type}s",
                    )
                )

        # Mismatched items (incorrect implementations)
        if hasattr(golden_result, "mismatched_items"):
            for mismatch in golden_result.mismatched_items:
                expected = mismatch.expected if hasattr(mismatch, "expected") else "N/A"
                actual = mismatch.actual if hasattr(mismatch, "actual") else "N/A"
                item_type = (
                    mismatch.item_type if hasattr(mismatch, "item_type") else "unknown"
                )
                item_name = (
                    mismatch.item_name
                    if hasattr(mismatch, "item_name")
                    else str(mismatch)
                )
                issues.append(
                    ValidationIssue(
                        issue_type=f"mismatch_{item_type}",
                        severity="medium",
                        message=f"Mismatch in {item_name}: expected {expected}, got {actual}",
                        field=item_type,
                    )
                )

        return issues

    @staticmethod
    def from_llm_evaluation(evaluation) -> List[ValidationIssue]:
        """
        Convert LLM Judge evaluation to ValidationIssue list.

        Args:
            evaluation: EvaluationResult from LLM Judge

        Returns:
            List of ValidationIssue objects

        Example:
            issues = ValidationIssueFactory.from_llm_evaluation(llm_eval)
        """
        issues = []

        if not evaluation:
            return issues

        # LLM-identified issues
        if hasattr(evaluation, "issues"):
            for issue_data in evaluation.issues:
                if isinstance(issue_data, dict):
                    issues.append(
                        ValidationIssue(
                            issue_type=issue_data.get("type", "quality"),
                            message=issue_data.get("message", "Quality issue detected"),
                            severity=issue_data.get("severity", "medium"),
                            field=issue_data.get("name", "unnamed"),
                        )
                    )
                else:
                    # Handle string issues
                    issues.append(
                        ValidationIssue(
                            issue_type="quality",
                            message=str(issue_data),
                            severity="medium",
                            field="llm_feedback",
                        )
                    )

        # Low quality score
        if hasattr(evaluation, "overall_score") and evaluation.overall_score < 7.0:
            issues.append(
                ValidationIssue(
                    issue_type="quality",
                    message=f"Quality score below threshold: {evaluation.overall_score:.1f}/10.0",
                    severity="medium" if evaluation.overall_score >= 5.0 else "high",
                    field="overall_quality",
                )
            )

        # Specific quality dimensions
        if hasattr(evaluation, "dimensions"):
            for dimension, score in evaluation.dimensions.items():
                if score < 7.0:
                    issues.append(
                        ValidationIssue(
                            issue_type="quality",
                            message=f"{dimension.capitalize()} needs improvement: {score:.1f}/10.0",
                            severity="low" if score >= 5.0 else "medium",
                            field=dimension,
                        )
                    )

        return issues

    @staticmethod
    def from_comprehensive_validation(validation_result) -> List[ValidationIssue]:
        """
        Convert ComprehensiveValidationResult to ValidationIssue list.

        Handles both Golden Data validation and LLM evaluation.

        Args:
            validation_result: ComprehensiveValidationResult

        Returns:
            Combined list of ValidationIssue objects

        Example:
            issues = ValidationIssueFactory.from_comprehensive_validation(validation_result)
        """
        issues = []

        # Golden Data validation
        if (
            hasattr(validation_result, "golden_result")
            and validation_result.golden_result
        ):
            issues.extend(
                ValidationIssueFactory.from_golden_validation(
                    validation_result.golden_result
                )
            )

        # LLM evaluation
        if (
            hasattr(validation_result, "llm_evaluation")
            and validation_result.llm_evaluation
        ):
            issues.extend(
                ValidationIssueFactory.from_llm_evaluation(
                    validation_result.llm_evaluation
                )
            )

        # Ontology validation errors
        if (
            hasattr(validation_result, "ontology_errors")
            and validation_result.ontology_errors
        ):
            for error in validation_result.ontology_errors:
                issues.append(
                    ValidationIssue(
                        issue_type="ontology",
                        message=str(error),
                        severity="medium",
                        field=(
                            error.get("entity", "unknown")
                            if isinstance(error, dict)
                            else "unknown"
                        ),
                    )
                )

        # Dependency errors
        if (
            hasattr(validation_result, "dependency_errors")
            and validation_result.dependency_errors
        ):
            for error in validation_result.dependency_errors:
                issues.append(
                    ValidationIssue(
                        issue_type="dependency",
                        message=str(error),
                        severity="high",
                        field="circular"
                        if "circular" in str(error).lower()
                        else "dependency",
                    )
                )

        return issues

    @staticmethod
    def format_for_agent(issues: List[ValidationIssue], max_issues: int = 20) -> str:
        """
        Format validation issues for agent prompt.

        Provides consistent, readable format for agents to understand issues.

        Args:
            issues: List of ValidationIssue objects
            max_issues: Maximum number of issues to include (prevents prompt overflow)

        Returns:
            Formatted string for agent prompt

        Example:
            formatted = ValidationIssueFactory.format_for_agent(issues)
        """
        if not issues:
            return "✅ No validation issues found. Output is acceptable."

        formatted = "## Validation Issues\n\n"

        # Group by severity
        by_severity = {"high": [], "medium": [], "low": []}
        for issue in issues:
            severity = issue.severity if hasattr(issue, "severity") else "medium"
            by_severity.get(severity, by_severity["medium"]).append(issue)

        # Format by severity
        total_shown = 0
        for severity in ["high", "medium", "low"]:
            severity_issues = by_severity[severity]
            if not severity_issues:
                continue

            # Severity marker
            marker = {"high": "🔴", "medium": "🟡", "low": "🟢"}[severity]
            formatted += f"### {marker} {severity.upper()} Priority\n\n"

            # Show issues (up to limit)
            for i, issue in enumerate(severity_issues):
                if total_shown >= max_issues:
                    remaining = len(issues) - total_shown
                    formatted += f"\n... and {remaining} more issues (truncated)\n"
                    return formatted

                field_name = (
                    issue.field
                    if hasattr(issue, "field")
                    else (
                        issue.issue_type if hasattr(issue, "issue_type") else "unknown"
                    )
                )
                message = issue.message if hasattr(issue, "message") else str(issue)

                formatted += f"{i + 1}. **{field_name}**: {message}\n"
                total_shown += 1

            formatted += "\n"

        return formatted

    @staticmethod
    def format_summary(issues: List[ValidationIssue]) -> Dict[str, Any]:
        """
        Generate summary statistics of validation issues.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            Dictionary with summary statistics

        Example:
            summary = ValidationIssueFactory.format_summary(issues)
            logger.info(f"Total issues: {summary['total']}")
        """
        summary = {
            "total": len(issues),
            "by_severity": {"high": 0, "medium": 0, "low": 0},
            "by_type": {},
            "critical_issues": [],
        }

        for issue in issues:
            # By severity
            severity = issue.severity if hasattr(issue, "severity") else "medium"
            summary["by_severity"][severity] = (
                summary["by_severity"].get(severity, 0) + 1
            )

            # By type
            issue_type = issue.issue_type if hasattr(issue, "issue_type") else "unknown"
            summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1

            # Critical issues (high severity)
            if severity == "high":
                summary["critical_issues"].append(
                    {
                        "name": (
                            issue.field
                            if hasattr(issue, "field")
                            else (
                                issue.issue_type
                                if hasattr(issue, "issue_type")
                                else "unknown"
                            )
                        ),
                        "message": issue.message
                        if hasattr(issue, "message")
                        else str(issue),
                    }
                )

        return summary

    @staticmethod
    def filter_by_severity(
        issues: List[ValidationIssue], min_severity: str = "low"
    ) -> List[ValidationIssue]:
        """
        Filter issues by minimum severity level.

        Args:
            issues: List of ValidationIssue objects
            min_severity: Minimum severity to include ("low", "medium", "high")

        Returns:
            Filtered list of issues

        Example:
            critical = ValidationIssueFactory.filter_by_severity(issues, min_severity="high")
        """
        severity_order = {"low": 0, "medium": 1, "high": 2}
        min_level = severity_order.get(min_severity, 0)

        return [
            issue
            for issue in issues
            if severity_order.get(
                issue.severity if hasattr(issue, "severity") else "medium", 1
            )
            >= min_level
        ]

    @staticmethod
    def filter_by_type(
        issues: List[ValidationIssue], item_types: List[str]
    ) -> List[ValidationIssue]:
        """
        Filter issues by type.

        Args:
            issues: List of ValidationIssue objects
            item_types: List of types to include (e.g., ["feature", "task"])

        Returns:
            Filtered list of issues

        Example:
            feature_issues = ValidationIssueFactory.filter_by_type(issues, ["feature"])
        """
        return [
            issue
            for issue in issues
            if (hasattr(issue, "issue_type") and issue.issue_type in item_types)
        ]

    # ============================================================================
    # Builder Methods - Create individual issues with consistent patterns
    # ============================================================================

    @staticmethod
    def create_syntax_error(
        exception: Exception,
        context: str = "code",
        severity: str = "error",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for syntax errors.

        Standardizes syntax error reporting across all validators.
        Eliminates 42+ duplicate try/except blocks in validators.

        Args:
            exception: SyntaxError or parsing exception
            context: Context where error occurred (e.g., "agents.py", "tasks.py")
            severity: Issue severity (default: "error")

        Returns:
            ValidationIssue for the syntax error

        Example:
            try:
                ast.parse(code)
            except SyntaxError as e:
                issue = ValidationIssueFactory.create_syntax_error(e, "agents.py")
        """
        line_no = getattr(exception, "lineno", None)
        return ValidationIssue(
            severity=severity,
            issue_type="syntax_error",
            message=f"Syntax error in {context}: {str(exception)}",
            line=line_no,
            field=context,
        )

    @staticmethod
    def create_missing_required(
        field_name: str,
        item_name: str = "",
        severity: str = "high",
        suggestion: str = "",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for missing required fields/items.

        Args:
            field_name: Name of the missing field
            item_name: Optional name of the item with missing field
            severity: Issue severity (default: "high")
            suggestion: Optional suggestion for fixing

        Returns:
            ValidationIssue for the missing required field

        Example:
            issue = ValidationIssueFactory.create_missing_required(
                "role", "agent_1", suggestion="Add role='Analyst'"
            )
        """
        item_context = f" in {item_name}" if item_name else ""
        message = f"Missing required field: {field_name}{item_context}"
        if suggestion:
            message += f". Suggestion: {suggestion}"

        return ValidationIssue(
            severity=severity,
            issue_type="missing_required",
            message=message,
            field=field_name,
        )

    @staticmethod
    def create_invalid_value(
        field_name: str,
        actual_value: Any,
        expected: str = "",
        item_name: str = "",
        severity: str = "medium",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for invalid field values.

        Args:
            field_name: Name of the field with invalid value
            actual_value: The actual invalid value
            expected: Description of expected value format
            item_name: Optional name of the item
            severity: Issue severity (default: "medium")

        Returns:
            ValidationIssue for the invalid value

        Example:
            issue = ValidationIssueFactory.create_invalid_value(
                "tools", "invalid_tool", expected="valid tool name from registry"
            )
        """
        item_context = f" in {item_name}" if item_name else ""
        message = f"Invalid value for {field_name}{item_context}: {actual_value}"
        if expected:
            message += f". Expected: {expected}"

        return ValidationIssue(
            severity=severity,
            issue_type="invalid_value",
            message=message,
            field=field_name,
        )

    @staticmethod
    def create_deprecated_usage(
        feature_name: str,
        alternative: str = "",
        item_name: str = "",
        severity: str = "low",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for deprecated feature usage.

        Args:
            feature_name: Name of the deprecated feature
            alternative: Recommended alternative
            item_name: Optional name of the item using deprecated feature
            severity: Issue severity (default: "low")

        Returns:
            ValidationIssue for the deprecated usage

        Example:
            issue = ValidationIssueFactory.create_deprecated_usage(
                "Agent(function_calling_llm=...)",
                alternative="Use llm parameter instead"
            )
        """
        item_context = f" in {item_name}" if item_name else ""
        message = f"Deprecated feature used{item_context}: {feature_name}"
        if alternative:
            message += f". Use {alternative} instead"

        return ValidationIssue(
            severity=severity,
            issue_type="deprecated",
            message=message,
            field=feature_name,
        )

    @staticmethod
    def create_missing_item(
        item_type: str,
        item_name: str,
        severity: str = "medium",
        context: str = "",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for missing items (features, tasks, agents, etc.).

        Args:
            item_type: Type of missing item (e.g., "feature", "task", "agent")
            item_name: Name of the missing item
            severity: Issue severity (default: "medium")
            context: Optional context information

        Returns:
            ValidationIssue for the missing item

        Example:
            issue = ValidationIssueFactory.create_missing_item(
                "feature", "user_authentication", context="required by golden data"
            )
        """
        message = f"Missing {item_type}: {item_name}"
        if context:
            message += f" ({context})"

        return ValidationIssue(
            severity=severity,
            issue_type=f"missing_{item_type}",
            message=message,
            field=f"{item_type}s",
        )

    @staticmethod
    def create_extra_item(
        item_type: str,
        item_name: str,
        severity: str = "low",
        reason: str = "not in requirements",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for extra/unexpected items.

        Args:
            item_type: Type of extra item (e.g., "feature", "task", "agent")
            item_name: Name of the extra item
            severity: Issue severity (default: "low")
            reason: Reason why this is extra

        Returns:
            ValidationIssue for the extra item

        Example:
            issue = ValidationIssueFactory.create_extra_item(
                "agent", "unnecessary_agent", reason="not specified in golden data"
            )
        """
        return ValidationIssue(
            severity=severity,
            issue_type=f"extra_{item_type}",
            message=f"Extra {item_type}: {item_name} ({reason})",
            field=f"{item_type}s",
        )

    @staticmethod
    def create_circular_dependency(
        task1: str,
        task2: str,
        severity: str = "high",
    ) -> ValidationIssue:
        """
        Create a ValidationIssue for circular dependencies.

        Args:
            task1: First task in circular dependency
            task2: Second task in circular dependency
            severity: Issue severity (default: "high")

        Returns:
            ValidationIssue for the circular dependency

        Example:
            issue = ValidationIssueFactory.create_circular_dependency("task_a", "task_b")
        """
        return ValidationIssue(
            severity=severity,
            issue_type="circular_dependency",
            message=f"Circular dependency detected: {task1} ↔ {task2}",
            field="dependencies",
        )

    # ============================================================================
    # Summary and Counting Utilities
    # ============================================================================

    @staticmethod
    def create_validation_summary(issues: List[ValidationIssue]) -> Dict[str, Any]:
        """
        Generate standardized validation summary from issues.

        Consolidates 15+ duplicate summary generation patterns across validators.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            Dictionary with summary statistics

        Example:
            summary = ValidationIssueFactory.create_validation_summary(issues)
            is_valid = summary["is_valid"]
            error_count = summary["errors"]
        """
        by_severity = {"error": 0, "warning": 0, "info": 0, "low": 0, "medium": 0, "high": 0}
        auto_fixable = 0

        for issue in issues:
            severity = getattr(issue, "severity", "info")
            # Normalize severity names
            if severity in by_severity:
                by_severity[severity] += 1

            if getattr(issue, "auto_fix_available", False):
                auto_fixable += 1

        return {
            "total": len(issues),
            "errors": by_severity["error"] + by_severity["high"],
            "warnings": by_severity["warning"] + by_severity["medium"],
            "info": by_severity["info"] + by_severity["low"],
            "auto_fixable": auto_fixable,
            "is_valid": (by_severity["error"] + by_severity["high"]) == 0,
            "by_severity": by_severity,
        }

    @staticmethod
    def count_errors(issues: List[ValidationIssue]) -> int:
        """
        Count error-level issues.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            Number of error/high severity issues

        Example:
            if ValidationIssueFactory.count_errors(issues) > 0:
                logger.error("Validation failed")
        """
        return len([
            i for i in issues
            if getattr(i, "severity", "") in ("error", "high")
        ])

    @staticmethod
    def count_warnings(issues: List[ValidationIssue]) -> int:
        """
        Count warning-level issues.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            Number of warning/medium severity issues

        Example:
            warnings = ValidationIssueFactory.count_warnings(issues)
        """
        return len([
            i for i in issues
            if getattr(i, "severity", "") in ("warning", "medium")
        ])

    @staticmethod
    def count_by_severity(issues: List[ValidationIssue], severity: str) -> int:
        """
        Count issues by specific severity level.

        Args:
            issues: List of ValidationIssue objects
            severity: Severity level to count

        Returns:
            Number of issues with that severity

        Example:
            high_issues = ValidationIssueFactory.count_by_severity(issues, "high")
        """
        return len([
            i for i in issues
            if getattr(i, "severity", "") == severity
        ])
