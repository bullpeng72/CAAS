"""
CAAS Framework Fixing Module

3-level auto-fixing system: Template → Rule → LLM-based fixes.
"""

from caas_framework.fixing.auto_fixer import AutoFixer, FixResult
from caas_framework.fixing.levels import LLMFixer, RuleFixer, TemplateFixer

__all__ = [
    "AutoFixer",
    "FixResult",
    "TemplateFixer",
    "RuleFixer",
    "LLMFixer",
]
