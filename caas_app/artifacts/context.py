"""
Artifact Generation Context - Phase 1 Task P1.3

Consolidates 15 parameters into a single context object.
Replaces parameter list in generate_all_artifacts() and _build_context().
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ArtifactGenerationContext:
    """
    Context object for artifact generation.

    Replaces 15 individual parameters with a single context object,
    following the Introduce Parameter Object refactoring pattern.

    Before:
        def generate_all_artifacts(
            self, project_name, requirement, golden_data, bmad_mapping,
            agents, tasks, test_summary, test_results, coverage,
            validation_result, code_files, code_metrics, security_issues,
            performance_issues
        )

    After:
        def generate_all_artifacts(self, context: ArtifactGenerationContext)
    """

    # Core project info (required)
    project_name: str
    requirement: str

    # Design phase data (optional)
    golden_data: Optional[Dict[str, Any]] = None
    bmad_mapping: Optional[Dict[str, Any]] = None
    agents: Optional[List[Dict[str, Any]]] = None
    tasks: Optional[List[Dict[str, Any]]] = None

    # Test phase data (optional)
    test_summary: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    coverage: Optional[Dict[str, Any]] = None

    # Validation data (optional)
    validation_result: Optional[Dict[str, Any]] = None

    # Code review data (optional)
    code_files: Optional[List[Dict[str, Any]]] = None
    code_metrics: Optional[Dict[str, Any]] = None
    security_issues: Optional[Dict[str, Any]] = None
    performance_issues: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        """Validate required fields"""
        if not self.project_name:
            raise ValueError("project_name is required")
        if not self.requirement:
            raise ValueError("requirement is required")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactGenerationContext":
        """
        Create context from dictionary.

        Useful for JSON/YAML deserialization.
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary.

        Returns:
            Dict with all non-None fields
        """
        return {
            k: v for k, v in self.__dict__.items()
            if v is not None
        }

    def has_design_data(self) -> bool:
        """Check if design phase data is available"""
        return any([
            self.golden_data,
            self.bmad_mapping,
            self.agents,
            self.tasks,
        ])

    def has_test_data(self) -> bool:
        """Check if test phase data is available"""
        return any([
            self.test_summary,
            self.test_results,
            self.coverage,
        ])

    def has_code_review_data(self) -> bool:
        """Check if code review data is available"""
        return any([
            self.code_files,
            self.code_metrics,
            self.security_issues,
            self.performance_issues,
        ])
