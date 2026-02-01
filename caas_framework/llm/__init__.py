"""
CAAS Framework LLM Package

Provides integration for various LLM providers and chains.
"""

from caas_framework.llm.client import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    OllamaClient,
    LLMClientFactory,
    get_llm_client,
    get_langchain_llm,
)
from caas_framework.llm.chains import (
    RequirementAnalysis,
    AgentSpec,
    TaskSpec,
    ValidationResult,
    RequirementAnalysisChain,
    AgentDesignChain,
    TaskDesignChain,
    SpecGenerationChain,
    SpecValidationChain,
    AgentGenerationPipeline,
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
