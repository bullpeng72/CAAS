"""
Golden Data Validator (Deprecated)

This module is deprecated. Please use caas_framework.validation.golden_validator instead.

The implementation has been unified and moved to caas_framework for better modularity.

For backward compatibility, this module re-exports the unified validator.
"""

import warnings

# Re-export from unified location
from caas_framework.validation.golden_validator import GoldenDataValidator

# Issue deprecation warning
warnings.warn(
    "app.core.validation.golden_validator is deprecated. "
    "Use caas_framework.validation.golden_validator instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['GoldenDataValidator']
