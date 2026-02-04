"""
CAAS Framework BMAD Module

CAAS 6-Phase Methodology
6-Phase AI-driven development engine with Golden Data validation.
"""

from caas_framework.bmad.engine import BMADEngine, BMADPhase, BMADResult
from caas_framework.bmad.golden_data import GoldenDataPipeline, RequirementConcretizer
from caas_framework.bmad.models import TaskMapping
from caas_framework.bmad.reflection import ReflectionEngine

# Additional component exports (migrated from app/core/bmad)
# These are available for import but not in __all__ by default
# to maintain backward compatibility

__all__ = [
    # Core engine
    "BMADEngine",
    "BMADPhase",
    "BMADResult",
    # Golden data
    "GoldenDataPipeline",
    "RequirementConcretizer",
    # Reflection
    "ReflectionEngine",
    # Models
    "TaskMapping",
]
