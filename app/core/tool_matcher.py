"""
Tool Matcher (DEPRECATED)

⚠️ DEPRECATED: This module is no longer used and will be removed in a future version.

Use the following instead:
- app.knowledge.ontology.reasoner.OntologyReasoner for tool inference
- app.core.ontology for Tool Ontology management

This legacy module used hardcoded Python package names which are incompatible
with the new Tool Ontology system that uses CrewAI tool names.
"""

from typing import List, Dict, Set, Tuple
from app.utils.logger import get_logger
import warnings

logger = get_logger("tool_matcher")

# Deprecation warning
warnings.warn(
    "tool_matcher module is deprecated. Use OntologyReasoner instead.",
    DeprecationWarning,
    stacklevel=2
)


class ToolMatcher:
    """
    Tool 매칭 및 추천 시스템 (DEPRECATED)

    ⚠️ DEPRECATED: Use app.knowledge.ontology.reasoner.OntologyReasoner instead.

    This class used hardcoded Python package mappings which are incompatible
    with the new dynamic Tool Ontology system.
    """

    def __init__(self):
        logger.warning(
            "ToolMatcher is deprecated and no longer maintained. "
            "Use OntologyReasoner from app.knowledge.ontology.reasoner instead."
        )

    @classmethod
    def match_tools_for_agent(
        cls,
        agent_skills: List[str],
        agent_role: str,
        domain: str,
        available_tools: List[str],
    ) -> List[str]:
        """
        DEPRECATED: Use OntologyReasoner.infer_tools() instead.

        Returns empty list and logs warning.
        """
        logger.warning(
            "ToolMatcher.match_tools_for_agent() is deprecated. "
            "Use OntologyReasoner.infer_tools() instead."
        )
        return []

    @classmethod
    def match_tools_for_task(
        cls,
        task_name: str,
        task_description: str,
        task_output_type: str,
        available_tools: List[str],
    ) -> List[str]:
        """
        DEPRECATED: Use OntologyReasoner.infer_tools() instead.

        Returns empty list and logs warning.
        """
        logger.warning(
            "ToolMatcher.match_tools_for_task() is deprecated. "
            "Use OntologyReasoner.infer_tools() instead."
        )
        return []

    @classmethod
    def rank_tools(
        cls,
        tools: List[str],
        context: str,
    ) -> List[Tuple[str, float]]:
        """
        DEPRECATED: Use OntologyReasoner ranking instead.

        Returns tools with score 1.0 and logs warning.
        """
        logger.warning(
            "ToolMatcher.rank_tools() is deprecated. "
            "Use OntologyReasoner instead."
        )
        return [(tool, 1.0) for tool in tools]

    @classmethod
    def get_recommended_tools(
        cls,
        domain: str,
        agents: List[Dict],
        tasks: List[Dict],
        available_tools: List[str],
        top_k: int = 10,
    ) -> List[str]:
        """
        DEPRECATED: Use OntologyReasoner.infer_tools() instead.

        Returns empty list and logs warning.
        """
        logger.warning(
            "ToolMatcher.get_recommended_tools() is deprecated. "
            "Use OntologyReasoner.infer_tools() instead."
        )
        return []


# Legacy constants kept for reference only - DO NOT USE
_LEGACY_DOMAIN_TOOL_MAPPING = {
    "finance": ["yfinance", "pandas", "numpy", "ta-lib", "requests"],
    # ... removed for brevity
}

_LEGACY_SKILL_TOOL_MAPPING = {
    "web_search": ["duckduckgo-search", "google-search", "serp-api"],
    # ... removed for brevity
}

_LEGACY_TASK_TYPE_TOOL_MAPPING = {
    "research": ["duckduckgo-search", "wikipedia", "arxiv"],
    # ... removed for brevity
}
