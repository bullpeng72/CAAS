"""
ValidationIssueFactory - Unified Issue Conversion

Eliminates duplicate issue extraction logic across the codebase.
Provides consistent conversion from various validation results to ValidationIssue objects.
"""

from typing import List, Dict, Any
from caas_framework.models.validation import ValidationIssue


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
        if hasattr(golden_result, 'missing_items'):
            for missing in golden_result.missing_items:
                item_type = missing.item_type if hasattr(missing, 'item_type') else "unknown"
                issues.append(ValidationIssue(
                    issue_type=f"missing_{item_type}",
                    severity=missing.severity if hasattr(missing, 'severity') else "medium",
                    message=f"Missing {item_type}: {missing.item_name if hasattr(missing, 'item_name') else str(missing)}",
                    field=f"{item_type}s"
                ))

        # Extra items (unexpected implementations)
        if hasattr(golden_result, 'extra_items'):
            for extra in golden_result.extra_items:
                item_type = extra.item_type if hasattr(extra, 'item_type') else "unknown"
                issues.append(ValidationIssue(
                    issue_type=f"extra_{item_type}",
                    severity="low",
                    message=f"Extra {item_type}: {extra.item_name if hasattr(extra, 'item_name') else str(extra)} (not in requirements)",
                    field=f"{item_type}s"
                ))

        # Mismatched items (incorrect implementations)
        if hasattr(golden_result, 'mismatched_items'):
            for mismatch in golden_result.mismatched_items:
                expected = mismatch.expected if hasattr(mismatch, 'expected') else "N/A"
                actual = mismatch.actual if hasattr(mismatch, 'actual') else "N/A"
                item_type = mismatch.item_type if hasattr(mismatch, 'item_type') else "unknown"
                item_name = mismatch.item_name if hasattr(mismatch, 'item_name') else str(mismatch)
                issues.append(ValidationIssue(
                    issue_type=f"mismatch_{item_type}",
                    severity="medium",
                    message=f"Mismatch in {item_name}: expected {expected}, got {actual}",
                    field=item_type
                ))

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
        if hasattr(evaluation, 'issues'):
            for issue_data in evaluation.issues:
                if isinstance(issue_data, dict):
                    issues.append(ValidationIssue(
                        issue_type=issue_data.get("type", "quality"),
                        message=issue_data.get("message", "Quality issue detected"),
                        severity=issue_data.get("severity", "medium"),
                        field=issue_data.get("name", "unnamed")
                    ))
                else:
                    # Handle string issues
                    issues.append(ValidationIssue(
                        issue_type="quality",
                        message=str(issue_data),
                        severity="medium",
                        field="llm_feedback"
                    ))

        # Low quality score
        if hasattr(evaluation, 'overall_score') and evaluation.overall_score < 7.0:
            issues.append(ValidationIssue(
                issue_type="quality",
                message=f"Quality score below threshold: {evaluation.overall_score:.1f}/10.0",
                severity="medium" if evaluation.overall_score >= 5.0 else "high",
                field="overall_quality"
            ))

        # Specific quality dimensions
        if hasattr(evaluation, 'dimensions'):
            for dimension, score in evaluation.dimensions.items():
                if score < 7.0:
                    issues.append(ValidationIssue(
                        issue_type="quality",
                        message=f"{dimension.capitalize()} needs improvement: {score:.1f}/10.0",
                        severity="low" if score >= 5.0 else "medium",
                        field=dimension
                    ))

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
        if hasattr(validation_result, 'golden_result') and validation_result.golden_result:
            issues.extend(ValidationIssueFactory.from_golden_validation(
                validation_result.golden_result
            ))

        # LLM evaluation
        if hasattr(validation_result, 'llm_evaluation') and validation_result.llm_evaluation:
            issues.extend(ValidationIssueFactory.from_llm_evaluation(
                validation_result.llm_evaluation
            ))

        # Ontology validation errors
        if hasattr(validation_result, 'ontology_errors') and validation_result.ontology_errors:
            for error in validation_result.ontology_errors:
                issues.append(ValidationIssue(
                    issue_type="ontology",
                    message=str(error),
                    severity="medium",
                    field=error.get("entity", "unknown") if isinstance(error, dict) else "unknown"
                ))

        # Dependency errors
        if hasattr(validation_result, 'dependency_errors') and validation_result.dependency_errors:
            for error in validation_result.dependency_errors:
                issues.append(ValidationIssue(
                    issue_type="dependency",
                    message=str(error),
                    severity="high",
                    field="circular" if "circular" in str(error).lower() else "dependency"
                ))

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
            severity = issue.severity if hasattr(issue, 'severity') else "medium"
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

                field_name = issue.field if hasattr(issue, 'field') else (issue.issue_type if hasattr(issue, 'issue_type') else "unknown")
                message = issue.message if hasattr(issue, 'message') else str(issue)

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
            print(f"Total issues: {summary['total']}")
        """
        summary = {
            "total": len(issues),
            "by_severity": {"high": 0, "medium": 0, "low": 0},
            "by_type": {},
            "critical_issues": []
        }

        for issue in issues:
            # By severity
            severity = issue.severity if hasattr(issue, 'severity') else "medium"
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            # By type
            issue_type = issue.issue_type if hasattr(issue, 'issue_type') else "unknown"
            summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1

            # Critical issues (high severity)
            if severity == "high":
                summary["critical_issues"].append({
                    "name": issue.field if hasattr(issue, 'field') else (issue.issue_type if hasattr(issue, 'issue_type') else "unknown"),
                    "message": issue.message if hasattr(issue, 'message') else str(issue)
                })

        return summary

    @staticmethod
    def filter_by_severity(issues: List[ValidationIssue], min_severity: str = "low") -> List[ValidationIssue]:
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
            issue for issue in issues
            if severity_order.get(
                issue.severity if hasattr(issue, 'severity') else "medium",
                1
            ) >= min_level
        ]

    @staticmethod
    def filter_by_type(issues: List[ValidationIssue], item_types: List[str]) -> List[ValidationIssue]:
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
            issue for issue in issues
            if (hasattr(issue, 'issue_type') and issue.issue_type in item_types)
        ]
