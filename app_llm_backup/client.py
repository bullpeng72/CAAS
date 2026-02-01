"""
CAAS LLM Client

다양한 LLM 프로바이더 (OpenAI, Anthropic, Ollama)를 통합 관리하는 클라이언트입니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field

# 선택적 의존성
LANGCHAIN_AVAILABLE = False
ChatOpenAI = None
BaseChatModel = object

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.language_models.chat_models import BaseChatModel
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    # SECURITY: 의존성 누락을 로깅하여 디버깅 용이하게 함
    import logging
    logging.getLogger("llm.client").warning(
        f"LangChain을 사용할 수 없습니다: {e}. "
        "설치하려면: pip install langchain-openai langchain-core"
    )

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("llm.client")


class LLMProvider(str, Enum):
    """지원하는 LLM 프로바이더"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """LLM 설정 모델"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4-turbo-preview"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    
    class Config:
        use_enum_values = True


class LLMResponse(BaseModel):
    """LLM 응답 모델"""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class BaseLLMClient(ABC):
    """LLM 클라이언트 기본 클래스"""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """채팅 완성을 수행합니다."""
    
    @abstractmethod
    def get_langchain_llm(self) -> BaseChatModel:
        """LangChain 호환 LLM 객체를 반환합니다."""


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""

    def __init__(self, config: Optional[LLMConfig] = None):
        from app.utils.config import get_api_key
        from app.utils.secrets import mask_secret

        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.OPENAI,
            model=self.settings.llm.default_llm_model,
        )
        # SECURITY: SecretManager에서 API 키 가져오기
        self._api_key = get_api_key("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 OPENAI_API_KEY를 설정해주세요."
            )
        # SECURITY: 마스킹된 버전만 로깅
        logger.info(f"OpenAI 클라이언트 초기화: model={self.config.model}, key={mask_secret(self._api_key)}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """OpenAI 채팅 완성을 수행합니다."""
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
        """LangChain ChatOpenAI 객체를 반환합니다."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain가 설치되지 않았습니다. pip install langchain-openai langchain-core")
        return ChatOpenAI(
            api_key=self._api_key,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )


class AnthropicClient(BaseLLMClient):
    """Anthropic API 클라이언트"""

    def __init__(self, config: Optional[LLMConfig] = None):
        from app.utils.config import get_api_key
        from app.utils.secrets import mask_secret

        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-opus-20240229",
        )
        # SECURITY: SecretManager에서 API 키 가져오기
        self._api_key = get_api_key("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 ANTHROPIC_API_KEY를 설정해주세요."
            )
        # SECURITY: 마스킹된 버전만 로깅
        logger.info(f"Anthropic 클라이언트 초기화: model={self.config.model}, key={mask_secret(self._api_key)}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """Anthropic 채팅 완성을 수행합니다."""
        from anthropic import Anthropic
        
        client = Anthropic(api_key=self._api_key)
        
        # 시스템 메시지 분리
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
        """LangChain ChatAnthropic 객체를 반환합니다."""
        from langchain_anthropic import ChatAnthropic
        
        return ChatAnthropic(
            api_key=self._api_key,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens or 4096,
        )


class OllamaClient(BaseLLMClient):
    """Ollama (로컬 LLM) 클라이언트"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.settings = get_settings()
        self.config = config or LLMConfig(
            provider=LLMProvider.OLLAMA,
            model=self.settings.llm.ollama_model,
        )
        self._base_url = self.settings.llm.ollama_base_url
        logger.info(f"Ollama 클라이언트 초기화: model={self.config.model}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """Ollama 채팅 완성을 수행합니다."""
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
        """LangChain ChatOllama 객체를 반환합니다."""
        from langchain_community.chat_models import ChatOllama
        
        return ChatOllama(
            base_url=self._base_url,
            model=self.config.model,
            temperature=self.config.temperature,
        )


class LLMClientFactory:
    """LLM 클라이언트 팩토리"""
    
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
        LLM 클라이언트를 생성합니다.
        
        Args:
            provider: LLM 프로바이더 (openai, anthropic, ollama)
            config: LLM 설정
        
        Returns:
            BaseLLMClient: LLM 클라이언트 인스턴스
        """
        settings = get_settings()
        
        if provider is None:
            provider = settings.llm.default_llm_provider
        
        if isinstance(provider, str):
            provider = LLMProvider(provider.lower())
        
        client_class = cls._clients.get(provider)
        if not client_class:
            raise ValueError(f"지원하지 않는 프로바이더: {provider}")
        
        return client_class(config)
    
    @classmethod
    def get_default_client(cls) -> BaseLLMClient:
        """기본 설정의 LLM 클라이언트를 반환합니다."""
        return cls.create()


# 편의를 위한 함수
def get_llm_client(
    provider: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    LLM 클라이언트를 가져옵니다.
    
    Args:
        provider: LLM 프로바이더 (기본값: 환경 설정)
        **kwargs: 추가 설정
    
    Returns:
        BaseLLMClient: LLM 클라이언트
    """
    config = LLMConfig(**kwargs) if kwargs else None
    return LLMClientFactory.create(provider, config)


def get_langchain_llm(
    provider: Optional[str] = None,
    **kwargs
) -> BaseChatModel:
    """
    LangChain 호환 LLM을 가져옵니다.
    
    Args:
        provider: LLM 프로바이더
        **kwargs: 추가 설정
    
    Returns:
        BaseChatModel: LangChain LLM 객체
    """
    client = get_llm_client(provider, **kwargs)
    return client.get_langchain_llm()
