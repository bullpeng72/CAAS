"""
CAAS Framework LLM Package

Provides integration for various LLM providers and chains.
"""

from caas_framework.llm.chains import (
    AgentDesignChain,
    AgentGenerationPipeline,
    AgentSpec,
    RequirementAnalysis,
    RequirementAnalysisChain,
    SpecGenerationChain,
    SpecValidationChain,
    TaskDesignChain,
    TaskSpec,
    ValidationResult,
)
from caas_framework.llm.client import (
    AnthropicClient,
    BaseLLMClient,
    LLMClientFactory,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
    get_langchain_llm,
    get_llm_client,
)

__all__ = [
    # Client
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "OllamaClient",
    "LLMClientFactory",
    "get_llm_client",
    "get_langchain_llm",
    # Chains
    "RequirementAnalysis",
    "AgentSpec",
    "TaskSpec",
    "ValidationResult",
    "RequirementAnalysisChain",
    "AgentDesignChain",
    "TaskDesignChain",
    "SpecGenerationChain",
    "SpecValidationChain",
    "AgentGenerationPipeline",
]
