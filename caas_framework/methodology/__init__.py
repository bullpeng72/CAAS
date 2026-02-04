"""
CAAS Framework BMAD Module

CAAS 6-Phase Methodology
6-Phase AI-driven development engine with Golden Data validation.
"""

from caas_framework.methodology.engine import SixPhaseEngine, Phase, MethodologyResult
from caas_framework.methodology.golden_data import GoldenDataPipeline, RequirementConcretizer
from caas_framework.methodology.models import TaskMapping
from caas_framework.methodology.reflection import ReflectionEngine

# Additional component exports (migrated from app/core/bmad)
# These are available for import but not in __all__ by default
# to maintain backward compatibility

__all__ = [
    # Core engine
    "SixPhaseEngine",
    "Phase",
    "MethodologyResult",
    # Golden data
    "GoldenDataPipeline",
    "RequirementConcretizer",
    # Reflection
    "ReflectionEngine",
    # Models
    "TaskMapping",
]
