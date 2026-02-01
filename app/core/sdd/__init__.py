"""
App Core SDD - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.sdd for backward compatibility.

All new code should import directly from caas_framework.sdd:
    from caas_framework.sdd import SDDEngine

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.core.sdd import SDDEngine
    from app.core.sdd.engine import CrewAISpec

    # New (recommended)
    from caas_framework.sdd import SDDEngine
    from caas_framework.sdd import CrewAISpec
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.core.sdd is deprecated. "
    "Use 'from caas_framework.sdd import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.sdd
from caas_framework.sdd import *

# Also support module-specific imports
from caas_framework.sdd import engine as engine
from caas_framework.sdd import multi_spec as multi_spec
from caas_framework.sdd import spec_converter as spec_converter
