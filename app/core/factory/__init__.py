"""
App Core Factory - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.factory for backward compatibility.

All new code should import directly from caas_framework.factory:
    from caas_framework.factory import AgentFactory, CrewAssembler

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.core.factory import AgentFactory
    from app.core.factory.crew_assembler import CrewAssembler

    # New (recommended)
    from caas_framework.factory import AgentFactory
    from caas_framework.factory import CrewAssembler
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.core.factory is deprecated. "
    "Use 'from caas_framework.factory import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.factory
from caas_framework.factory import *

# Also support module-specific imports
from caas_framework.factory import agent_factory as agent_factory
from caas_framework.factory import task_factory as task_factory
from caas_framework.factory import tool_factory as tool_factory
from caas_framework.factory import crew_assembler as crew_assembler
from caas_framework.factory import base_factory as base_factory
