"""
App Models - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.models for backward compatibility.

All new code should import directly from caas_framework.models:
    from caas_framework.models import ConcretizedRequirement

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.models.schemas import ConcretizedRequirement
    from caas_framework.models.artifact_types import ArtifactType

    # New (recommended)
    from caas_framework.models import ConcretizedRequirement
    from caas_framework.models import ArtifactType
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.models is deprecated. "
    "Use 'from caas_framework.models import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.models
from caas_framework.models import *

# Also support old module-specific imports
from caas_framework.models import specifications as specifications
from caas_framework.models import validation as validation
from caas_framework.models import artifact_types as artifact_types
from caas_framework.models import domain_types as domain_types
from caas_framework.models import tool_registry as tool_registry

# Legacy: Create 'schemas' module alias pointing to specifications
# This allows "from app.models import schemas" to work
import sys
from caas_framework.models import specifications
sys.modules['app.models.schemas'] = specifications
