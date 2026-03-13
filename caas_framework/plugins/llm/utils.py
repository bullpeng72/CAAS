"""
LLM Plugin Utilities

Common utilities for LLM plugins to reduce code duplication.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Union

if TYPE_CHECKING:
    from caas_framework.plugins.llm.base import LLMMessage


def convert_messages_to_dict(
    messages: List[Union["LLMMessage", Dict[str, str]]]
) -> List[Dict[str, str]]:
    """
    Convert messages to dictionary format.

    Handles both LLMMessage objects and dictionaries.

    Args:
        messages: List of messages (LLMMessage or dict)

    Returns:
        List of message dictionaries with 'role' and 'content' keys

    Example:
        >>> msgs = [LLMMessage(role="user", content="hello")]
        >>> convert_messages_to_dict(msgs)
        [{"role": "user", "content": "hello"}]
    """
    converted = []
    for msg in messages:
        if isinstance(msg, dict):
            converted.append(msg)
        else:
            converted.append({"role": msg.role, "content": msg.content})
    return converted


def build_request_params(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int = None,
    stream: bool = False,
    response_format=None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Build common request parameters for LLM API calls.

    Args:
        model: Model name
        messages: List of message dictionaries
        temperature: Temperature setting
        max_tokens: Maximum tokens to generate
        stream: Enable streaming
        response_format: Response format ("json", {"type": "json_object"}, or None)
        **kwargs: Additional parameters

    Returns:
        Dictionary of request parameters

    Example:
        >>> params = build_request_params(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "hi"}],
        ...     temperature=0.7
        ... )
        >>> params["model"]
        'gpt-4'
    """
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    if stream:
        params["stream"] = True

    if response_format == "json" or (
        isinstance(response_format, dict) and response_format.get("type") == "json_object"
    ):
        params["response_format"] = {"type": "json_object"}
    elif isinstance(response_format, dict):
        params["response_format"] = response_format

    # Add extra kwargs
    params.update(kwargs)

    return params


def extract_usage_info(
    response: Any, default_prompt: int = 0, default_completion: int = 0
) -> Dict[str, int]:
    """
    Extract usage information from API response.

    Handles missing usage attributes gracefully.

    Args:
        response: API response object
        default_prompt: Default prompt tokens if missing
        default_completion: Default completion tokens if missing

    Returns:
        Dictionary with prompt_tokens, completion_tokens, total_tokens

    Example:
        >>> usage = extract_usage_info(response)
        >>> usage["total_tokens"]
        150
    """
    if not hasattr(response, "usage") or response.usage is None:
        return {
            "prompt_tokens": default_prompt,
            "completion_tokens": default_completion,
            "total_tokens": default_prompt + default_completion,
        }

    usage = response.usage
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", default_prompt),
        "completion_tokens": getattr(usage, "completion_tokens", default_completion),
        "total_tokens": getattr(usage, "total_tokens", default_prompt + default_completion),
    }


def format_connection_error(
    error: Exception, api_base: str, model: str, provider: str = "LLM"
) -> str:
    """
    Format connection error message with helpful troubleshooting steps.

    Args:
        error: Original exception
        api_base: API base URL
        model: Model name
        provider: Provider name (e.g., "Ollama", "OpenAI")

    Returns:
        Formatted error message with troubleshooting steps

    Example:
        >>> msg = format_connection_error(
        ...     ConnectionError(),
        ...     "http://localhost:11434",
        ...     "llama2",
        ...     "Ollama"
        ... )
        >>> "Failed to connect" in msg
        True
    """
    error_msg = str(error)

    if "Connection refused" in error_msg or "Failed to connect" in error_msg:
        if provider.lower() == "ollama":
            return (
                f"Failed to connect to {provider} server. "
                "Please ensure:\n"
                f"1. {provider} is installed: https://ollama.ai/download\n"
                f"2. {provider} server is running at {api_base}\n"
                f"3. Model '{model}' is pulled: ollama pull {model}"
            )
        else:
            return (
                f"Failed to connect to {provider} server at {api_base}. "
                "Please check:\n"
                f"1. API endpoint is accessible\n"
                f"2. Network connectivity\n"
                f"3. API credentials are valid"
            )

    elif "model" in error_msg.lower() and "not found" in error_msg.lower():
        if provider.lower() == "ollama":
            return (
                f"Model '{model}' not found. "
                f"Pull it with: ollama pull {model}\n"
                f"Or list available models: ollama list"
            )
        else:
            return f"Model '{model}' not found or not accessible. Please check model name."

    return error_msg


def parse_error_type(error: Exception) -> str:
    """
    Parse error type for categorization.

    Args:
        error: Exception object

    Returns:
        Error category: "connection", "auth", "rate_limit", "model", "unknown"

    Example:
        >>> parse_error_type(ConnectionError())
        'connection'
    """
    error_msg = str(error).lower()

    if "connection" in error_msg or "refused" in error_msg:
        return "connection"
    elif "unauthorized" in error_msg or "authentication" in error_msg or "api key" in error_msg:
        return "auth"
    elif "rate limit" in error_msg or "too many requests" in error_msg:
        return "rate_limit"
    elif "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
        return "model"
    else:
        return "unknown"
