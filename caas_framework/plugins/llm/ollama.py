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
from typing import Any, AsyncIterator, Dict, List, Optional

from caas_framework.plugins.llm.base import LLMMessage, LLMPlugin, LLMResponse


class OllamaPlugin(LLMPlugin):
    """Ollama LLM provider for local execution"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # Ollama specific
        self.api_base = config.get("api_base") or os.getenv(
            "OLLAMA_API_BASE", "http://localhost:11434/v1"
        )

        # Ollama doesn't require API key but we accept it for compatibility
        self.api_key = config.get("api_key") or os.getenv("OLLAMA_API_KEY", "ollama")

        self._client = None

    async def initialize(self) -> None:
        """Initialize Ollama client"""
        try:
            from openai import AsyncOpenAI

            # Ollama uses OpenAI-compatible API
            self._client = AsyncOpenAI(
                api_key=self.api_key,  # Ollama doesn't validate but required by client
                base_url=self.api_base,
            )
            self._initialized = True

        except ImportError:
            raise ImportError(
                "OpenAI package not installed. "
                "Ollama plugin uses OpenAI-compatible API. "
                "Install with: pip install openai"
            )

    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Async Ollama call"""
        if not self._initialized:
            await self.initialize()

        # Convert messages (handle both dict and object formats)
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                ollama_messages.append(msg)
            else:
                ollama_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_params = {
            "model": self.model,
            "messages": ollama_messages,
            "temperature": temperature or self.temperature,
        }

        if max_tokens or self.max_tokens:
            request_params["max_tokens"] = max_tokens or self.max_tokens

        # Note: Ollama may not support all OpenAI features like JSON mode
        # JSON mode support depends on the specific model
        if response_format == "json":
            # Some Ollama models support format parameter
            request_params["format"] = "json"

        # Add extra kwargs
        request_params.update(kwargs)

        try:
            # Call Ollama via OpenAI-compatible API
            response = await self._client.chat.completions.create(**request_params)

            # Ollama response format is OpenAI-compatible
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(
                        response.usage, "completion_tokens", 0
                    ),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                },
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            # Provide helpful error message for common Ollama issues
            error_msg = str(e)
            if "Connection refused" in error_msg or "Failed to connect" in error_msg:
                raise RuntimeError(
                    "Failed to connect to Ollama server. "
                    "Please ensure:\n"
                    "1. Ollama is installed: https://ollama.ai/download\n"
                    f"2. Ollama server is running at {self.api_base}\n"
                    f"3. Model '{self.model}' is pulled: ollama pull {self.model}"
                ) from e
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                raise RuntimeError(
                    f"Model '{self.model}' not found. "
                    f"Pull it with: ollama pull {self.model}\n"
                    f"Or list available models: ollama list"
                ) from e
            else:
                raise

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Streaming Ollama call"""
        if not self._initialized:
            await self.initialize()

        # Convert messages (handle both dict and object formats)
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                ollama_messages.append(msg)
            else:
                ollama_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_params = {
            "model": self.model,
            "messages": ollama_messages,
            "temperature": temperature or self.temperature,
            "stream": True,
        }

        if max_tokens or self.max_tokens:
            request_params["max_tokens"] = max_tokens or self.max_tokens

        request_params.update(kwargs)

        try:
            # Stream
            stream = await self._client.chat.completions.create(**request_params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                raise RuntimeError(
                    f"Failed to connect to Ollama server at {self.api_base}. "
                    "Please ensure Ollama is running."
                ) from e
            else:
                raise

    async def close(self) -> None:
        """Close Ollama client"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("ollama", OllamaPlugin)
