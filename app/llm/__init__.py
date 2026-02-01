"""
App LLM - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.llm for backward compatibility.

All new code should import directly from caas_framework.llm:
    from caas_framework.llm import get_llm_client

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.llm import get_llm_client
    from app.llm.chains import RequirementAnalysisChain

    # New (recommended)
    from caas_framework.llm import get_llm_client
    from caas_framework.llm import RequirementAnalysisChain
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.llm is deprecated. "
    "Use 'from caas_framework.llm import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.llm
from caas_framework.llm import *

# Also support module-specific imports
from caas_framework.llm import client as client
from caas_framework.llm import chains as chains
from caas_framework.llm import chain_factory as chain_factory
from caas_framework.llm import response_parser as response_parser
from caas_framework.llm import prompts as prompts
