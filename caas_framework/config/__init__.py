"""
CaaS Framework Configuration Module - SINGLE SOURCE OF TRUTH

**Redesign Phase 1** (2026-02-01)

Primary interface:
    >>> from caas_framework.config import get_config
    >>> config = get_config()
    >>> config.llm.model
    'gpt-4o-mini'

This module REPLACES:
- app/utils/config.py (deprecated)
- caas_framework/config/loader.py (now deprecated)
- caas_framework/config/settings.py (now deprecated)

All new code should use:
    from caas_framework.config import get_config
"""

# Import from unified module (NEW - Single Source of Truth)
from caas_framework.config.unified import (
    # Main config class
    CaaSConfig,

    # Primary entry points
    get_config,
    reload_config,

    # Helper functions
    get_api_key,
    set_subprocess_env,

    # Backward compatibility aliases
    Settings,
    get_settings,
    FrameworkConfig,
    load_config,
)

# OLD imports (DEPRECATED - kept for backward compatibility only)
# These will be removed in version 3.0
import warnings

try:
    from caas_framework.config.loader import ConfigLoader as _OldConfigLoader
    # Issue deprecation warning when old loader is imported
    warnings.warn(
        "ConfigLoader from caas_framework.config.loader is deprecated. "
        "Use 'from caas_framework.config import get_config' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    ConfigLoader = _OldConfigLoader
except ImportError:
    # Old loader might be removed, use unified
    ConfigLoader = type('ConfigLoader', (), {
        'from_env': classmethod(lambda cls: get_config()),
        'from_file': classmethod(lambda cls, path: get_config(config_file=path)),
    })

__all__ = [
    # PRIMARY INTERFACE (use this!)
    "CaaSConfig",
    "get_config",
    "reload_config",

    # Helpers
    "get_api_key",
    "set_subprocess_env",

    # BACKWARD COMPATIBILITY (deprecated in v2.0, will be removed in v3.0)
    "Settings",
    "get_settings",
    "FrameworkConfig",
    "load_config",
    "ConfigLoader",  # OLD - use get_config() instead
]

# Version
__version__ = "2.0.0"
