"""
Test suite for refactored LLM plugin system.

Verifies:
1. No breaking changes to public API
2. All plugins can be instantiated
3. Base class provides common functionality
4. Error handling works correctly
5. Provider-specific features still work
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from caas_framework.plugins.llm.base import LLMMessage, LLMPlugin, LLMResponse
from caas_framework.plugins.llm.openai import OpenAIPlugin
from caas_framework.plugins.llm.ollama import OllamaPlugin
from caas_framework.plugins.llm.utils import (
    build_request_params,
    convert_messages_to_dict,
    extract_usage_info,
    format_connection_error,
    parse_error_type,
)


class TestLLMUtilities:
    """Test utility functions"""

    def test_convert_messages_to_dict_with_objects(self):
        """Test message conversion with LLMMessage objects"""
        messages = [
            LLMMessage(role="user", content="hello"),
            LLMMessage(role="assistant", content="hi"),
        ]

        result = convert_messages_to_dict(messages)

        assert result == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

    def test_convert_messages_to_dict_with_dicts(self):
        """Test message conversion with dictionaries"""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

        result = convert_messages_to_dict(messages)

        assert result == messages

    def test_convert_messages_to_dict_mixed(self):
        """Test message conversion with mixed types"""
        messages = [
            LLMMessage(role="user", content="hello"),
            {"role": "assistant", "content": "hi"},
        ]

        result = convert_messages_to_dict(messages)

        assert result == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

    def test_build_request_params_basic(self):
        """Test basic request parameter building"""
        messages = [{"role": "user", "content": "test"}]

        params = build_request_params(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
        )

        assert params["model"] == "gpt-4"
        assert params["messages"] == messages
        assert params["temperature"] == 0.7
        assert "stream" not in params

    def test_build_request_params_with_max_tokens(self):
        """Test request params with max_tokens"""
        messages = [{"role": "user", "content": "test"}]

        params = build_request_params(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )

        assert params["max_tokens"] == 100

    def test_build_request_params_with_json_format(self):
        """Test request params with JSON response format"""
        messages = [{"role": "user", "content": "test"}]

        params = build_request_params(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            response_format="json",
        )

        assert params["response_format"] == {"type": "json_object"}

    def test_build_request_params_with_streaming(self):
        """Test request params with streaming enabled"""
        messages = [{"role": "user", "content": "test"}]

        params = build_request_params(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            stream=True,
        )

        assert params["stream"] is True

    def test_extract_usage_info_with_usage(self):
        """Test usage extraction from response with usage"""
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        usage = extract_usage_info(mock_response)

        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    def test_extract_usage_info_without_usage(self):
        """Test usage extraction from response without usage"""
        mock_response = MagicMock()
        mock_response.usage = None

        usage = extract_usage_info(mock_response)

        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0

    def test_parse_error_type_connection(self):
        """Test error type parsing for connection errors"""
        error = ConnectionError("Connection refused")
        assert parse_error_type(error) == "connection"

    def test_parse_error_type_auth(self):
        """Test error type parsing for authentication errors"""
        error = Exception("Unauthorized: Invalid API key")
        assert parse_error_type(error) == "auth"

    def test_parse_error_type_rate_limit(self):
        """Test error type parsing for rate limit errors"""
        error = Exception("Rate limit exceeded")
        assert parse_error_type(error) == "rate_limit"

    def test_parse_error_type_model(self):
        """Test error type parsing for model not found errors"""
        error = Exception("Model not found")
        assert parse_error_type(error) == "model"

    def test_format_connection_error_ollama(self):
        """Test connection error formatting for Ollama"""
        error = ConnectionError("Connection refused")

        msg = format_connection_error(
            error,
            api_base="http://localhost:11434",
            model="llama2",
            provider="Ollama",
        )

        assert "Failed to connect to Ollama server" in msg
        assert "ollama pull llama2" in msg

    def test_format_connection_error_openai(self):
        """Test connection error formatting for OpenAI"""
        error = ConnectionError("Connection refused")

        msg = format_connection_error(
            error,
            api_base="https://api.openai.com",
            model="gpt-4",
            provider="OpenAI",
        )

        assert "Failed to connect to OpenAI server" in msg
        assert "API credentials" in msg


class TestOpenAIPlugin:
    """Test OpenAI plugin after refactoring"""

    def test_instantiation(self):
        """Test that OpenAI plugin can be instantiated"""
        plugin = OpenAIPlugin(
            name="test",
            config={"model": "gpt-4", "api_key": "test-key"},
        )

        assert plugin.name == "test"
        assert plugin.model == "gpt-4"
        assert plugin.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_ainvoke_with_mock(self):
        """Test ainvoke method with mocked API call"""
        plugin = OpenAIPlugin(
            name="test",
            config={"model": "gpt-4", "api_key": "test-key"},
        )

        # Mock client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello!"
        mock_response.model = "gpt-4"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 2
        mock_response.usage.total_tokens = 7
        mock_response.choices[0].finish_reason = "stop"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        plugin._client = mock_client
        plugin._initialized = True

        # Test ainvoke
        messages = [LLMMessage(role="user", content="test")]
        response = await plugin.ainvoke(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello!"
        assert response.model == "gpt-4"
        assert response.usage["total_tokens"] == 7


class TestOllamaPlugin:
    """Test Ollama plugin after refactoring"""

    def test_instantiation(self):
        """Test that Ollama plugin can be instantiated"""
        plugin = OllamaPlugin(
            name="test",
            config={"model": "llama2"},
        )

        assert plugin.name == "test"
        assert plugin.model == "llama2"
        assert plugin.api_base == "http://localhost:11434/v1"

    def test_custom_api_base(self):
        """Test Ollama with custom API base"""
        plugin = OllamaPlugin(
            name="test",
            config={"model": "llama2", "api_base": "http://custom:8080/v1"},
        )

        assert plugin.api_base == "http://custom:8080/v1"

    @pytest.mark.asyncio
    async def test_ainvoke_with_mock(self):
        """Test ainvoke method with mocked API call"""
        plugin = OllamaPlugin(
            name="test",
            config={"model": "llama2"},
        )

        # Mock client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from Ollama!"
        mock_response.model = "llama2"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 3
        mock_response.usage.total_tokens = 8
        mock_response.choices[0].finish_reason = "stop"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        plugin._client = mock_client
        plugin._initialized = True

        # Test ainvoke
        messages = [LLMMessage(role="user", content="test")]
        response = await plugin.ainvoke(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello from Ollama!"
        assert response.model == "llama2"

    def test_build_request_params_json_format(self):
        """Test that Ollama uses 'format' instead of 'response_format'"""
        plugin = OllamaPlugin(
            name="test",
            config={"model": "llama2"},
        )

        messages = [{"role": "user", "content": "test"}]
        params = plugin._build_request_params(
            messages=messages,
            response_format="json",
        )

        # Ollama should use "format" not "response_format"
        assert "format" in params
        assert params["format"] == "json"
        assert "response_format" not in params


class TestPluginErrorHandling:
    """Test error handling in refactored plugins"""

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test that connection errors are properly handled"""
        plugin = OpenAIPlugin(
            name="test",
            config={"model": "gpt-4", "api_key": "test-key"},
        )

        # Mock client that raises connection error
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        plugin._client = mock_client
        plugin._initialized = True

        # Should raise RuntimeError with helpful message
        with pytest.raises(RuntimeError) as exc_info:
            messages = [LLMMessage(role="user", content="test")]
            await plugin.ainvoke(messages)

        # Error message should be enhanced
        assert "Failed to connect" in str(exc_info.value) or "Connection refused" in str(
            exc_info.value
        )


class TestBackwardCompatibility:
    """Test that refactoring maintains backward compatibility"""

    def test_llm_message_still_works(self):
        """Test that LLMMessage class still works"""
        msg = LLMMessage(role="user", content="test")
        assert msg.role == "user"
        assert msg.content == "test"

    def test_llm_response_still_works(self):
        """Test that LLMResponse class still works"""
        response = LLMResponse(
            content="Hello",
            model="gpt-4",
            usage={"total_tokens": 10},
            finish_reason="stop",
        )
        assert response.content == "Hello"
        assert response.model == "gpt-4"

    def test_plugin_abstract_interface(self):
        """Test that LLMPlugin is still abstract"""
        # Should not be able to instantiate LLMPlugin directly
        with pytest.raises(TypeError):
            LLMPlugin(name="test", config={})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
