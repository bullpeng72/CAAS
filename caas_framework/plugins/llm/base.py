"""
LLM Plugin Base Interface

Unified interface for all LLM providers.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from pydantic import BaseModel

from caas_framework.plugins.base import Plugin, PluginType


class LLMMessage(BaseModel):
    """LLM message format"""
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """LLM response format"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMPlugin(Plugin):
    """
    Base class for LLM plugins

    All LLM providers must implement:
    - invoke(): Synchronous call
    - ainvoke(): Async call
    - stream(): Streaming responses
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, plugin_type=PluginType.LLM, config=config)
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens")
        self.api_key = config.get("api_key")

    @abstractmethod
    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Async LLM call

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            response_format: "text" or "json"
            **kwargs: Provider-specific args

        Returns:
            LLMResponse
        """

    def invoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Sync LLM call (convenience wrapper)

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific args

        Returns:
            LLMResponse
        """
        import asyncio
        return asyncio.run(
            self.ainvoke(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        )

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming LLM call

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific args

        Yields:
            Token chunks
        """

    async def health_check(self) -> bool:
        """
        Check if LLM is accessible

        Returns:
            True if healthy
        """
        try:
            response = await self.ainvoke(
                messages=[LLMMessage(role="user", content="test")],
                max_tokens=5
            )
            return bool(response.content)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, model={self.model})>"
