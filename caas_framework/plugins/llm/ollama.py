"""
Ollama LLM Plugin

Supports local LLM execution with Ollama.

Ollama provides OpenAI-compatible API for local models:
- Llama 2, Llama 3
- Mistral, Mixtral
- CodeLlama
- And many more open-source models

Installation:
1. Install Ollama: https://ollama.ai/download
2. Pull a model: ollama pull llama2
3. Start Ollama server (usually auto-starts)
4. Use with CAAS!
"""

import os
from typing import Any, Dict, List, Optional

from caas_framework.plugins.llm.base import LLMPlugin


class OllamaPlugin(LLMPlugin):
    """
    Ollama LLM provider for local execution.

    Uses the base LLMPlugin implementation for all common logic.
    Only implements provider-specific initialization and API calls.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # Ollama specific configuration
        self.api_base = config.get("api_base") or os.getenv(
            "OLLAMA_API_BASE", "http://localhost:11434/v1"
        )

        # Ollama doesn't require API key but we accept it for compatibility
        self.api_key = config.get("api_key") or os.getenv("OLLAMA_API_KEY", "ollama")

    async def initialize(self) -> None:
        """Initialize Ollama client."""
        try:
            from openai import AsyncOpenAI

            # Ollama uses OpenAI-compatible API
            self._client = AsyncOpenAI(
                api_key=self.api_key,  # Ollama doesn't validate but required by client
                base_url=self.api_base,
            )
            self._initialized = True
            self.logger.debug(
                f"Ollama client initialized (model: {self.model}, base: {self.api_base})"
            )

        except ImportError:
            raise ImportError(
                "OpenAI package not installed. "
                "Ollama plugin uses OpenAI-compatible API. "
                "Install with: pip install openai"
            )

    def _build_request_params(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Build Ollama-specific request parameters.

        Ollama uses "format" instead of "response_format" for JSON mode.

        Args:
            messages: Converted messages
            temperature: Temperature override
            max_tokens: Max tokens override
            response_format: Response format ("json" or None)
            stream: Enable streaming
            **kwargs: Additional parameters

        Returns:
            Dictionary of request parameters
        """
        # Use base implementation
        params = super()._build_request_params(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=None,  # Don't use base JSON format
            stream=stream,
            **kwargs,
        )

        # Ollama uses "format" instead of "response_format"
        if response_format == "json":
            # Remove OpenAI-style response_format if it exists
            params.pop("response_format", None)
            # Add Ollama-style format parameter
            params["format"] = "json"

        return params


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("ollama", OllamaPlugin)
