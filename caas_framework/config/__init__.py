"""
CaaS Framework Configuration Module - SINGLE SOURCE OF TRUTH

**Redesign Phase 1** (2026-02-01)

Primary interface:
    >>> from caas_framework.config import get_config
    >>> config = get_config()
    >>> config.llm.model
    'gpt-4o-mini'

All new code should use:
    from caas_framework.config import get_config
"""

import warnings

# Import from unified module (NEW - Single Source of Truth)
from caas_framework.config.unified import (  # Main config class; Primary entry points; Helper functions; Backward compatibility aliases
    CaaSConfig,
    FrameworkConfig,
    Settings,
    get_api_key,
    get_config,
    get_settings,
    load_config,
    reload_config,
    set_subprocess_env,
)

try:
    from caas_framework.config.loader import ConfigLoader as _OldConfigLoader
    ConfigLoader = _OldConfigLoader
except ImportError:
    # Fallback if loader is not available
    ConfigLoader = type(
        "ConfigLoader",
        (),
        {
            "from_env": classmethod(lambda cls: get_config()),
            "from_file": classmethod(lambda cls, path: get_config(config_file=path)),
        },
    )

__all__ = [
    # PRIMARY INTERFACE (use this!)
    "CaaSConfig",
    "get_config",
    "reload_config",
    # Helpers
    "get_api_key",
    "set_subprocess_env",
    # Additional exports
    "Settings",
    "get_settings",
    "FrameworkConfig",
    "load_config",
    "ConfigLoader"
]

# Version
__version__ = "0.4.1"
