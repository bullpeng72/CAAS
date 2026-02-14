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
from caas_framework.sdd.yaml_exporter import (
    YAMLExporter,
    export_specifications,
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
    # YAML Exporter (v0.6.1 - Week 4)
    "YAMLExporter",
    "export_specifications",
]
