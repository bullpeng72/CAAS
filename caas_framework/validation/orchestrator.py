"""
Validation Orchestrator

Coordinates multiple validators and provides a unified validation interface.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
)
from caas_framework.models.validation import (
    ValidationResult,
    GoldenValidationReport,
    DependencyIssue,
)
from caas_framework.validation.ontology_validator import OntologyValidator
from caas_framework.validation.golden_validator import GoldenDataValidator
from caas_framework.validation.dependency_validator import DependencyValidator
from caas_framework.utils import ObjectAccessor


@dataclass
class ComprehensiveValidationResult:
    """
    Comprehensive validation result from all validators.
    """
    ontology_result: Optional[ValidationResult] = None
    golden_result: Optional[GoldenValidationReport] = None
    dependency_valid: bool = True
    dependency_issues: List[DependencyIssue] = None

    @property
    def is_valid(self) -> bool:
        """Check if all validations passed."""
        checks = []

        if self.ontology_result:
            checks.append(self.ontology_result.is_valid)

        if self.golden_result:
            checks.append(not self.golden_result.needs_fixing)

        checks.append(self.dependency_valid)

        return all(checks) if checks else True

    @property
    def needs_fixing(self) -> bool:
        """Check if any validation requires fixing."""
        # CRITICAL FIX: Added needs_fixing property to prevent AttributeError
        # at collaboration.py:190
        if self.golden_result:
            return self.golden_result.needs_fixing

        # If no golden validation, check if there are any issues
        return self.total_issues > 0

    @property
    def total_issues(self) -> int:
        """Get total number of issues across all validators."""
        count = 0

        if self.ontology_result:
            count += self.ontology_result.summary.get("total", 0)

        if self.golden_result:
            count += len(self.golden_result.missing_items)
            count += len(self.golden_result.extra_items)
            count += len(self.golden_result.mismatched_items)

        if self.dependency_issues:
            count += len(self.dependency_issues)

        return count


class ValidationOrchestrator:
    """
    Validation Orchestrator

    Coordinates ontology, golden data, and dependency validation.
    Provides a unified interface for comprehensive validation.
    """

    def __init__(
        self,
        golden_data: Optional[ConcretizedRequirement] = None,
        enabled_tools: Optional[List[str]] = None
    ):
        """
        Initialize orchestrator.

        Args:
            golden_data: Optional Golden Data for validation
            enabled_tools: Optional list of enabled tool IDs
        """
        self.golden_data = golden_data
        self.ontology_validator = OntologyValidator(enabled_tools=enabled_tools)

        if golden_data:
            self.golden_validator = GoldenDataValidator(golden_data)
        else:
            self.golden_validator = None

    def validate_design(
        self,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        validate_golden: bool = True,
        validate_ontology: bool = True,
        validate_dependencies: bool = True,
        validate_requirement_alignment: bool = True
    ) -> ComprehensiveValidationResult:
        """
        Comprehensive design validation.

        Args:
            agents: Agent specifications
            tasks: Task specifications
            validate_golden: Enable Golden Data validation
            validate_ontology: Enable ontology validation
            validate_dependencies: Enable dependency validation
            validate_requirement_alignment: Enable requirement-task alignment validation

        Returns:
            ComprehensiveValidationResult with all validation results
        """
        result = ComprehensiveValidationResult()

        # Convert to dict for validators using ObjectAccessor
        agents_dict = ObjectAccessor.to_dict_list(agents)
        tasks_dict = ObjectAccessor.to_dict_list(tasks)

        # 1. Ontology Validation
        if validate_ontology:
            result.ontology_result = self.ontology_validator.validate_agents_and_tasks(
                agents_dict,
                tasks_dict
            )

        # 2. Requirement-Task Alignment Validation
        if validate_requirement_alignment and self.golden_data:
            # Convert golden data to dict if needed
            golden_dict = ObjectAccessor.to_dict(self.golden_data) if self.golden_data else {}
            alignment_issues = self.ontology_validator.validate_requirement_task_alignment(
                golden_dict,
                tasks_dict
            )

            # Add alignment issues to ontology result
            if result.ontology_result:
                result.ontology_result.issues.extend(alignment_issues)
                # Update summary
                result.ontology_result.summary["total"] += len(alignment_issues)
                result.ontology_result.summary["warnings"] += len([i for i in alignment_issues if i.severity == "warning"])
                result.ontology_result.summary["errors"] += len([i for i in alignment_issues if i.severity == "error"])
                result.ontology_result.summary["info"] += len([i for i in alignment_issues if i.severity == "info"])
                result.ontology_result.summary["auto_fixable"] += len([i for i in alignment_issues if i.auto_fix_available])
            else:
                # Create new ontology result if not exists
                from caas_framework.models.validation import ValidationResult
                result.ontology_result = ValidationResult(
                    is_valid=len([i for i in alignment_issues if i.severity == "error"]) == 0,
                    issues=alignment_issues,
                    summary={
                        "total": len(alignment_issues),
                        "errors": len([i for i in alignment_issues if i.severity == "error"]),
                        "warnings": len([i for i in alignment_issues if i.severity == "warning"]),
                        "info": len([i for i in alignment_issues if i.severity == "info"]),
                        "auto_fixable": len([i for i in alignment_issues if i.auto_fix_available]),
                    }
                )

        # 3. Golden Data Validation
        if validate_golden and self.golden_validator:
            result.golden_result = self.golden_validator.validate_design(
                agents,
                tasks
            )

        # 4. Dependency Validation
        if validate_dependencies:
            dependency_validator = DependencyValidator(tasks_dict)
            result.dependency_valid, result.dependency_issues = dependency_validator.validate()

        return result

    def validate_code(
        self,
        generated_spec: Dict[str, Any]
    ) -> ComprehensiveValidationResult:
        """
        Validate generated code against Golden Data.

        Args:
            generated_spec: Generated YAML spec (parsed dictionary)

        Returns:
            ComprehensiveValidationResult with validation results
        """
        result = ComprehensiveValidationResult()

        if self.golden_validator:
            result.golden_result = self.golden_validator.validate_code(generated_spec)

        return result

    def get_validation_summary(self, result: ComprehensiveValidationResult) -> str:
        """
        Generate human-readable validation summary.

        Args:
            result: Comprehensive validation result

        Returns:
            Formatted summary string
        """
        lines = ["# Validation Summary\n"]

        # Overall status
        status = "✅ PASSED" if result.is_valid else "❌ FAILED"
        lines.append(f"**Overall Status**: {status}")
        lines.append(f"**Total Issues**: {result.total_issues}\n")

        # Ontology Validation
        if result.ontology_result:
            lines.append("## Ontology Validation")
            summary = result.ontology_result.summary
            lines.append(f"- **Valid**: {result.ontology_result.is_valid}")
            lines.append(f"- **Errors**: {summary.get('errors', 0)}")
            lines.append(f"- **Warnings**: {summary.get('warnings', 0)}")
            lines.append(f"- **Info**: {summary.get('info', 0)}")
            lines.append(f"- **Auto-fixable**: {summary.get('auto_fixable', 0)}\n")

        # Golden Data Validation
        if result.golden_result:
            lines.append("## Golden Data Validation")
            lines.append(f"- **Phase**: {result.golden_result.phase_name}")
            lines.append(f"- **Coverage**: {result.golden_result.coverage_score:.1%}")
            lines.append(f"- **Status**: {result.golden_result.compliance_status.value}")
            lines.append(f"- **Missing Items**: {len(result.golden_result.missing_items)}")
            lines.append(f"- **Extra Items**: {len(result.golden_result.extra_items)}")
            lines.append(f"- **Needs Fixing**: {result.golden_result.needs_fixing}\n")

        # Dependency Validation
        if result.dependency_issues is not None:
            lines.append("## Dependency Validation")
            lines.append(f"- **Valid**: {result.dependency_valid}")
            lines.append(f"- **Issues**: {len(result.dependency_issues)}")

            if result.dependency_issues:
                errors = [i for i in result.dependency_issues if i.severity == "error"]
                warnings = [i for i in result.dependency_issues if i.severity == "warning"]
                lines.append(f"  - Errors: {len(errors)}")
                lines.append(f"  - Warnings: {len(warnings)}\n")

        return "\n".join(lines)

    def get_auto_fixable_issues(self, result: ComprehensiveValidationResult) -> List[Dict[str, Any]]:
        """
        Extract all auto-fixable issues.

        Args:
            result: Comprehensive validation result

        Returns:
            List of auto-fixable issues with metadata
        """
        fixable_issues = []

        if result.ontology_result:
            for issue in result.ontology_result.issues:
                if issue.auto_fix_available:
                    fixable_issues.append({
                        "source": "ontology",
                        "issue": issue,
                    })

        return fixable_issues

    def apply_auto_fixes(
        self,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        result: ComprehensiveValidationResult
    ) -> tuple[List[AgentSpecModel], List[TaskSpecModel], List[str]]:
        """
        Apply all auto-fixable issues automatically.

        Args:
            agents: Agent specifications
            tasks: Task specifications
            result: Comprehensive validation result

        Returns:
            Tuple of (fixed_agents, fixed_tasks, fixes_applied)
        """
        # Convert to dict for processing
        agents_dict = ObjectAccessor.to_dict_list(agents)
        tasks_dict = ObjectAccessor.to_dict_list(tasks)

        fixes_applied = []

        # Apply ontology fixes
        if result.ontology_result:
            for issue in result.ontology_result.issues:
                if issue.auto_fix_available:
                    agents_dict, tasks_dict = self.ontology_validator.apply_auto_fix(
                        agents_dict,
                        tasks_dict,
                        issue
                    )
                    fixes_applied.append(f"[Ontology] {issue.message}")

        # Convert back to Pydantic models
        fixed_agents = [AgentSpecModel(**a) for a in agents_dict]
        fixed_tasks = [TaskSpecModel(**t) for t in tasks_dict]

        return fixed_agents, fixed_tasks, fixes_applied
