"""
LLM Plugin Base Interface

Unified interface for all LLM providers with common implementation patterns.
"""

import logging

from typing import Any, AsyncIterator, Dict, List, Optional, Union

from pydantic import BaseModel

from caas_framework.plugins.base import Plugin, PluginType
from caas_framework.plugins.llm.utils import (
    build_request_params,
    convert_messages_to_dict,
    extract_usage_info,
    format_connection_error,
    parse_error_type,
)


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
    Base class for LLM plugins with common implementation patterns.

    This class provides:
    - Message conversion utilities
    - Request parameter building
    - Error handling helpers
    - Usage information extraction

    Subclasses must implement:
    - _call_api(): Provider-specific API call logic
    - _stream_api(): Provider-specific streaming logic
    - initialize(): Client initialization

    Optional overrides:
    - _convert_messages(): Custom message conversion
    - _build_request_params(): Custom parameter building
    - _handle_api_error(): Custom error handling
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name, plugin_type=PluginType.LLM, config=config)
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens")
        self.api_key = config.get("api_key")
        self._client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _convert_messages(
        self, messages: List[Union[LLMMessage, Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """
        Convert messages to dictionary format.

        Can be overridden for provider-specific message formatting.

        Args:
            messages: List of messages

        Returns:
            List of message dictionaries
        """
        return convert_messages_to_dict(messages)

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
        Build request parameters for API call.

        Can be overridden for provider-specific parameter formatting.

        Args:
            messages: Converted messages
            temperature: Temperature override
            max_tokens: Max tokens override
            response_format: Response format
            stream: Enable streaming
            **kwargs: Additional parameters

        Returns:
            Dictionary of request parameters
        """
        return build_request_params(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=stream,
            response_format=response_format,
            **kwargs,
        )

    def _extract_usage_info(self, response: Any) -> Dict[str, int]:
        """
        Extract usage information from API response.

        Can be overridden for provider-specific usage extraction.

        Args:
            response: API response object

        Returns:
            Dictionary with token usage
        """
        return extract_usage_info(response)

    def _handle_api_error(self, error: Exception, context: str = "") -> Exception:
        """
        Handle API errors with helpful error messages.

        Can be overridden for provider-specific error handling.

        Args:
            error: Original exception
            context: Additional context (e.g., "invoke", "stream")

        Returns:
            Enhanced exception with helpful message
        """
        error_type = parse_error_type(error)
        provider_name = self.__class__.__name__.replace("Plugin", "")

        if error_type in ("connection", "model"):
            api_base = getattr(self, "api_base", "unknown")
            formatted_msg = format_connection_error(
                error, api_base, self.model, provider_name
            )
            return RuntimeError(formatted_msg)

        return error

    async def _call_api(self, request_params: Dict[str, Any]) -> Any:
        """
        Default OpenAI-compatible API call.

        Override for provider-specific behavior.

        Args:
            request_params: Request parameters from _build_request_params()

        Returns:
            Provider-specific response object

        Raises:
            Exception: Provider-specific errors
        """
        return await self._client.chat.completions.create(**request_params)

    async def _stream_api(self, request_params: Dict[str, Any]) -> AsyncIterator[Any]:
        """
        Default OpenAI-compatible streaming API call.

        Override for provider-specific behavior.

        Args:
            request_params: Request parameters from _build_request_params()

        Yields:
            Provider-specific response chunks

        Raises:
            Exception: Provider-specific errors
        """
        stream = await self._client.chat.completions.create(**request_params)
        async for chunk in stream:
            yield chunk

    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Async LLM call with automatic error handling.

        This method handles common logic:
        1. Convert messages to provider format
        2. Build request parameters
        3. Call provider API
        4. Extract usage information
        5. Handle errors with helpful messages

        Subclasses only need to implement _call_api().

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            response_format: "text" or "json"
            **kwargs: Provider-specific args

        Returns:
            LLMResponse

        Raises:
            RuntimeError: On API errors with helpful troubleshooting
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Convert messages
            converted_messages = self._convert_messages(messages)

            # Build request params
            request_params = self._build_request_params(
                messages=converted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                stream=False,
                **kwargs,
            )

            # Call provider API
            response = await self._call_api(request_params)

            # Extract standard response
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=self._extract_usage_info(response),
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            enhanced_error = self._handle_api_error(e, context="ainvoke")
            raise enhanced_error from e

    def invoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
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
                **kwargs,
            )
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Streaming LLM call with automatic error handling.

        This method handles common logic:
        1. Convert messages to provider format
        2. Build request parameters
        3. Call provider streaming API
        4. Handle errors with helpful messages

        Subclasses only need to implement _stream_api().

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific args

        Yields:
            Token chunks

        Raises:
            RuntimeError: On API errors with helpful troubleshooting
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Convert messages
            converted_messages = self._convert_messages(messages)

            # Build request params
            request_params = self._build_request_params(
                messages=converted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            # Stream from provider API
            async for chunk in self._stream_api(request_params):
                if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            enhanced_error = self._handle_api_error(e, context="stream")
            raise enhanced_error from e

    async def close(self) -> None:
        """
        Close LLM client connection.

        Default implementation closes AsyncOpenAI-style clients.
        Override for custom cleanup logic.
        """
        if self._client:
            if hasattr(self._client, "close"):
                await self._client.close()
            self._client = None
            self._initialized = False

    async def health_check(self) -> bool:
        """
        Check if LLM is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.ainvoke(
                messages=[LLMMessage(role="user", content="test")], max_tokens=5
            )
            return bool(response.content)
        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, model={self.model})>"
