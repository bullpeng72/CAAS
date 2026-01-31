"""
CAAS Framework Validation Module

Multi-phase validation system with Golden Data, ontology, dependency validation,
traceability matrix, and LLM-based quality evaluation.
"""

from caas_framework.validation.ontology_validator import OntologyValidator
from caas_framework.validation.golden_validator import GoldenDataValidator
from caas_framework.validation.dependency_validator import DependencyValidator
from caas_framework.validation.orchestrator import ValidationOrchestrator
from caas_framework.validation.traceability import (
    TraceabilityManager,
    TraceabilityMatrix,
    TraceabilityLink,
    CoverageReport,
    build_traceability,
)
from caas_framework.validation.llm_judge import (
    LLMJudge,
    EvaluationResult,
    DimensionScore,
    EvaluationDimension,
    evaluate_with_llm_judge,
)

__all__ = [
    # Validators
    "OntologyValidator",
    "GoldenDataValidator",
    "DependencyValidator",
    "ValidationOrchestrator",
    # Traceability
    "TraceabilityManager",
    "TraceabilityMatrix",
    "TraceabilityLink",
    "CoverageReport",
    "build_traceability",
    # LLM Judge
    "LLMJudge",
    "EvaluationResult",
    "DimensionScore",
    "EvaluationDimension",
    "evaluate_with_llm_judge",
]
