"""
Agent Mixins

Provides reusable mixins for agent functionality:
- PromptBuildingMixin: Standardized prompt construction
"""

from caas_framework.agents.mixins.prompt_builder import (
    PromptBuildingMixin,
    AgentPromptBuilder
)

__all__ = [
    "PromptBuildingMixin",
    "AgentPromptBuilder",
]
