"""
CAAS SDD Package

Spec-Driven Development 구현체입니다.
"""

from caas_framework.sdd.engine import (
    LLMConfigSpec,
    AgentSpecModel,
    TaskSpecModel,
    CrewConfigSpec,
    ProjectSpec,
    CrewAISpec,
    ValidationError,
    ValidationResult,
    SpecValidator,
    SpecParser,
    SpecGenerator,
    SDDEngine,
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
