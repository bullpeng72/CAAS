"""
CAAS Framework LLM Client

Unified client for managing various LLM providers (OpenAI, Anthropic, Ollama).
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Optional dependencies
LANGCHAIN_AVAILABLE = False
ChatOpenAI = None
BaseChatModel = object

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    # SECURITY: Log dependency issues for debugging
    logging.getLogger("caas_framework.llm.client").warning(
        f"LangChain not available: {e}. "
        "Install with: pip install langchain-openai langchain-core"
    )

from caas_framework.config import get_api_key, get_settings
from caas_framework.utils.logger import get_logger

logger = get_logger(name="caas_framework.llm.client")


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Mask secret for safe logging.

    Args:
        secret: Secret to mask
        visible_chars: Number of characters to show

    Returns:
        Masked secret (e.g., "sk-...xyz")
    """
    if not secret or len(secret) <= visible_chars:
        return "***"

    prefix_len = min(visible_chars, len(secret) // 4)
    suffix_len = min(visible_chars, len(secret) // 4)

    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """LLM configuration model"""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4-turbo-preview"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        use_enum_values = True


class LLMResponse(BaseModel):
    """LLM response model"""

    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class BaseLLMClient(ABC):
    """Base class for LLM clients"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Perform chat completion"""

    @abstractmethod
    def get_langchain_llm(self) -> BaseChatModel:
        """Return LangChain-compatible LLM object"""


class OpenAIClient(BaseLLMClient):
    """OpenAI API client"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.OPENAI,
            model=self.settings.llm.default_llm_model,
        )
        # SECURITY: Get API key from SecretManager
        self._api_key = get_api_key("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not set. " "Please set OPENAI_API_KEY in .env file.")
        # SECURITY: Only log masked version
        logger.info(
            f"OpenAI client initialized: model={self.config.model}, key={mask_secret(self._api_key)}"
        )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Perform OpenAI chat completion"""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        response = client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="openai",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            raw_response=response,
        )

    def get_langchain_llm(self):
        """Return LangChain ChatOpenAI object"""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain not installed. pip install langchain-openai langchain-core"
            )
        return ChatOpenAI(
            api_key=self._api_key,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )


class AnthropicClient(BaseLLMClient):
    """Anthropic API client"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-opus-20240229",
        )
        # SECURITY: Get API key from SecretManager
        self._api_key = get_api_key("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. " "Please set ANTHROPIC_API_KEY in .env file."
            )
        # SECURITY: Only log masked version
        logger.info(
            f"Anthropic client initialized: model={self.config.model}, key={mask_secret(self._api_key)}"
        )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Perform Anthropic chat completion"""
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)

        # Separate system message
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        response = client.messages.create(
            model=kwargs.get("model", self.config.model),
            system=system_msg,
            messages=chat_messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens or 4096),
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider="anthropic",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw_response=response,
        )

    def get_langchain_llm(self) -> BaseChatModel:
        """Return LangChain ChatAnthropic object"""
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=self._api_key,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens or 4096,
        )


class OllamaClient(BaseLLMClient):
    """Ollama (local LLM) client"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.OLLAMA,
            model=self.settings.llm.ollama_model,
        )
        self._base_url = self.settings.llm.ollama_base_url
        logger.info(f"Ollama client initialized: model={self.config.model}")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Perform Ollama chat completion"""
        import httpx

        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": kwargs.get("model", self.config.model),
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=data.get("model", self.config.model),
            provider="ollama",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )

    def get_langchain_llm(self) -> BaseChatModel:
        """Return LangChain ChatOllama object"""
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            base_url=self._base_url,
            model=self.config.model,
            temperature=self.config.temperature,
        )


class LLMClientFactory:
    """LLM client factory"""

    _clients: Dict[str, type] = {
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.ANTHROPIC: AnthropicClient,
        LLMProvider.OLLAMA: OllamaClient,
    }

    @classmethod
    def create(
        cls,
        provider: Optional[Union[str, LLMProvider]] = None,
        config: Optional[LLMConfig] = None,
    ) -> BaseLLMClient:
        """
        Create LLM client

        Args:
            provider: LLM provider (openai, anthropic, ollama)
            config: LLM configuration

        Returns:
            BaseLLMClient: LLM client instance
        """
        settings = get_settings()

        if provider is None:
            provider = settings.llm.default_llm_provider

        if isinstance(provider, str):
            provider = LLMProvider(provider.lower())

        client_class = cls._clients.get(provider)
        if not client_class:
            raise ValueError(f"Unsupported provider: {provider}")

        return client_class(config)

    @classmethod
    def get_default_client(cls) -> BaseLLMClient:
        """Return LLM client with default settings"""
        return cls.create()


# Convenience functions
def get_llm_client(provider: Optional[str] = None, **kwargs) -> BaseLLMClient:
    """
    Get LLM client

    Args:
        provider: LLM provider (default: from environment settings)
        **kwargs: Additional configuration

    Returns:
        BaseLLMClient: LLM client
    """
    config = LLMConfig(**kwargs) if kwargs else None
    return LLMClientFactory.create(provider, config)


def get_langchain_llm(provider: Optional[str] = None, **kwargs) -> BaseChatModel:
    """
    Get LangChain-compatible LLM

    Args:
        provider: LLM provider
        **kwargs: Additional configuration

    Returns:
        BaseChatModel: LangChain LLM object
    """
    client = get_llm_client(provider, **kwargs)
    return client.get_langchain_llm()
