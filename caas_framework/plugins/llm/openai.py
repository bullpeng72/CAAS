"""
OpenAI LLM Plugin

Supports:
- GPT-4, GPT-4 Turbo
- GPT-3.5 Turbo
- Function calling
- JSON mode
"""

import os
from typing import Any, Dict

from caas_framework.plugins.llm.base import LLMPlugin


class OpenAIPlugin(LLMPlugin):
    """
    OpenAI LLM provider.

    Uses the base LLMPlugin implementation for all common logic.
    Only implements provider-specific initialization and API calls.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # OpenAI specific configuration
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.api_base = config.get("api_base")
        self.organization = config.get("organization")

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                organization=self.organization,
            )
            self._initialized = True
            self.logger.debug(f"OpenAI client initialized (model: {self.model})")

        except ImportError:
            raise ImportError(
                "OpenAI package not installed. " "Install with: pip install openai"
            )


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("openai", OpenAIPlugin)
