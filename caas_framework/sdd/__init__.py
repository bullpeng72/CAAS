"""
CAAS SDD Package

Spec-Driven Development 구현체입니다.
"""

from caas_framework.sdd.engine import (
    AgentSpecModel,
    CrewAISpec,
    CrewConfigSpec,
    LLMConfigSpec,
    ProjectSpec,
    SDDEngine,
    SpecGenerator,
    SpecParser,
    SpecValidator,
    TaskSpecModel,
    ValidationError,
    ValidationResult,
)

__all__ = [
    # Models
    "LLMConfigSpec",
    "AgentSpecModel",
    "TaskSpecModel",
    "CrewConfigSpec",
    "ProjectSpec",
    "CrewAISpec",
    # Validation
    "ValidationError",
    "ValidationResult",
    "SpecValidator",
    # Parser & Generator
    "SpecParser",
    "SpecGenerator",
    # Engine
    "SDDEngine",
]
