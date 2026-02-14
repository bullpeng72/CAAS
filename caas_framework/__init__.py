"""
CAAS Framework - CrewAI Agent Auto-generation System

UI-independent, production-ready multi-agent framework for automated
CrewAI project generation with Golden Data validation and auto-fixing.

Example:
    >>> from caas_framework import CrewAIFramework
    >>>
    >>> framework = CrewAIFramework(
    ...     llm_provider="openai",
    ...     graph_backend="neo4j"
    ... )
    >>>
    >>> result = await framework.generate_from_requirement(
    ...     requirement="Build a chatbot that helps users book flights",
    ...     domain="CONVERSATIONAL_AI"
    ... )
"""

from caas_framework.config.loader import ConfigLoader, get_config_loader, load_config
from caas_framework.config.settings import FrameworkConfig
from caas_framework.framework import CrewAIFramework

# Models will be imported from app/models until Phase 2
# from caas_framework.models.schemas import (
#     AgentSpecModel,
#     TaskSpecModel,
#     ConcretizedRequirement,
# )

__version__ = "0.6.3"
__all__ = [
    "CrewAIFramework",
    "FrameworkConfig",
    "ConfigLoader",
    "load_config",
    "get_config_loader",
]
