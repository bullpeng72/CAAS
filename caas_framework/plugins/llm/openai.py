"""
OpenAI LLM Plugin

Supports:
- GPT-4, GPT-4 Turbo
- GPT-3.5 Turbo
- Function calling
- JSON mode
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import os

from caas_framework.plugins.llm.base import LLMPlugin, LLMMessage, LLMResponse


class OpenAIPlugin(LLMPlugin):
    """OpenAI LLM provider"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, config=config)

        # OpenAI specific
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.api_base = config.get("api_base")
        self.organization = config.get("organization")

        self._client = None

    async def initialize(self) -> None:
        """Initialize OpenAI client"""
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                organization=self.organization
            )
            self._initialized = True

        except ImportError:
            raise ImportError(
                "OpenAI package not installed. "
                "Install with: pip install openai"
            )

    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Async OpenAI call"""
        if not self._initialized:
            await self.initialize()

        # Convert messages (handle both dict and object formats)
        openai_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                openai_messages.append(msg)
            else:
                openai_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature or self.temperature,
        }

        if max_tokens or self.max_tokens:
            request_params["max_tokens"] = max_tokens or self.max_tokens

        if response_format == "json":
            request_params["response_format"] = {"type": "json_object"}

        # Add extra kwargs
        request_params.update(kwargs)

        # Call OpenAI
        response = await self._client.chat.completions.create(**request_params)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Streaming OpenAI call"""
        if not self._initialized:
            await self.initialize()

        # Convert messages (handle both dict and object formats)
        openai_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                openai_messages.append(msg)
            else:
                openai_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature or self.temperature,
            "stream": True
        }

        if max_tokens or self.max_tokens:
            request_params["max_tokens"] = max_tokens or self.max_tokens

        request_params.update(kwargs)

        # Stream
        stream = await self._client.chat.completions.create(**request_params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def close(self) -> None:
        """Close OpenAI client"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False


# Register plugin
from caas_framework.plugins.base import get_plugin_registry

get_plugin_registry().register_plugin_class("openai", OpenAIPlugin)
