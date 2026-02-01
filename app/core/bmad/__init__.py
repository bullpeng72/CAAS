"""
App Core BMAD - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.bmad for backward compatibility.

All new code should import directly from caas_framework.bmad:
    from caas_framework.bmad import BMADEngine

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.core.bmad import BMADEngine
    from app.core.bmad.reflection import ReflectionEngine
    from app.core.bmad.analyzer import AnalysisResult

    # New (recommended)
    from caas_framework.bmad import BMADEngine
    from caas_framework.bmad.reflection import ReflectionEngine
    from caas_framework.bmad.code_analyzer import CodeAnalyzer

Component Name Changes:
    analyzer → code_analyzer
    validator → completeness_validator
    mapper → semantic_mapper
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.core.bmad is deprecated. "
    "Use 'from caas_framework.bmad import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.bmad
from caas_framework.bmad import *

# Component aliases for backward compatibility
from caas_framework.bmad import code_analyzer as analyzer
from caas_framework.bmad import completeness_validator as validator
from caas_framework.bmad import semantic_mapper as mapper
from caas_framework.bmad import reflection
from caas_framework.bmad import models
from caas_framework.bmad import adaptive
from caas_framework.bmad import personality
from caas_framework.bmad import planner
from caas_framework.bmad import sharding
from caas_framework.bmad import task_refiner
from caas_framework.bmad import tester
from caas_framework.bmad import deployer

# Provide direct aliases for commonly imported classes
try:
    from caas_framework.bmad.code_analyzer import CodeAnalyzer as Analyzer
except ImportError:
    pass

try:
    from caas_framework.bmad.completeness_validator import CompletenessValidator as Validator
except ImportError:
    pass

try:
    from caas_framework.bmad.semantic_mapper import SemanticMapper as Mapper
except ImportError:
    pass
