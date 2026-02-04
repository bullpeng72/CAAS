"""
LLM Plugin Factory

Helper functions to create LLM plugins and multi-model routers from configuration.
"""

import logging
from typing import Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.config.settings import LLMConfig, LLMProvider, MultiModelConfig
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.plugins.llm.multi_model_router import (
    ModelConfig,
    ModelSelectionStrategy,
    MultiModelRouter,
)


def create_llm_plugin(
    provider: LLMProvider,
    model: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> LLMPlugin:
    """
    Create an LLM plugin based on provider.

    Args:
        provider: LLM provider
        model: Model name
        api_key: API key
        api_base: Optional API base URL
        temperature: Default temperature
        max_tokens: Max tokens
        **kwargs: Additional provider-specific config

    Returns:
        LLMPlugin instance
    """
    config = {
        "model": model,
        "api_key": api_key,
        "api_base": api_base,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs,
    }

    if provider == LLMProvider.OPENAI:
        from caas_framework.plugins.llm.openai import OpenAIPlugin

        return OpenAIPlugin(name=f"openai-{model}", config=config)

    elif provider == LLMProvider.ANTHROPIC:
        # Future: Anthropic plugin
        raise NotImplementedError("Anthropic plugin not yet implemented")

    elif provider == LLMProvider.OLLAMA:
        from caas_framework.plugins.llm.ollama import OllamaPlugin

        return OllamaPlugin(name=f"ollama-{model}", config=config)

    elif provider == LLMProvider.AZURE_OPENAI:
        # Future: Azure OpenAI plugin
        raise NotImplementedError("Azure OpenAI plugin not yet implemented")

    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_multi_model_router(
    llm_config: LLMConfig, logger: Optional[logging.Logger] = None
) -> MultiModelRouter:
    """
    Create a multi-model router from configuration.

    Args:
        llm_config: LLM configuration with multi-model settings
        logger: Optional logger

    Returns:
        MultiModelRouter instance
    """
    if not llm_config.enable_multi_model:
        raise ValueError("Multi-model not enabled in configuration")

    if not llm_config.multi_models:
        raise ValueError("No models configured for multi-model routing")

    # Create model configs
    model_configs = []

    for multi_model_cfg in llm_config.multi_models:
        # Create LLM plugin for this model
        plugin = create_llm_plugin(
            provider=multi_model_cfg.provider,
            model=multi_model_cfg.model,
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
            temperature=llm_config.temperature,
            max_tokens=multi_model_cfg.max_tokens,
        )

        # Map phase names to AgentPhase enum
        suitable_phases = []
        for phase_name in multi_model_cfg.suitable_phases:
            try:
                phase = AgentPhase[phase_name]
                suitable_phases.append(phase)
            except KeyError:
                logger.warning(f"Unknown phase: {phase_name}")

        # Create ModelConfig
        model_config = ModelConfig(
            name=multi_model_cfg.name,
            plugin=plugin,
            cost_per_1k_tokens=multi_model_cfg.cost_per_1k_tokens,
            max_tokens=multi_model_cfg.max_tokens,
            suitable_phases=suitable_phases,
            priority=multi_model_cfg.priority,
        )

        model_configs.append(model_config)

    # Parse strategy
    try:
        strategy = ModelSelectionStrategy(llm_config.model_selection_strategy)
    except ValueError:
        logger.warning(
            f"Unknown strategy: {llm_config.model_selection_strategy}, "
            f"using PHASE_BASED"
        )
        strategy = ModelSelectionStrategy.PHASE_BASED

    # Create router
    router = MultiModelRouter(
        name="multi-model-router",
        models=model_configs,
        strategy=strategy,
        enable_fallback=llm_config.enable_model_fallback,
        logger=logger,
    )

    return router


def create_default_multi_model_setup(
    api_key: Optional[str] = None, logger: Optional[logging.Logger] = None
) -> LLMConfig:
    """
    Create a default multi-model configuration with sensible defaults.

    Default setup:
    - GPT-4 Turbo for complex tasks (Architecture, Design, Delivery)
    - GPT-3.5 Turbo for simple tasks (Discovery, QA)
    - Fallback chain: GPT-4 → GPT-3.5

    Args:
        api_key: OpenAI API key
        logger: Optional logger

    Returns:
        LLMConfig with multi-model setup
    """
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4-turbo",  # Default primary model
        temperature=0.3,
        api_key=api_key,
        enable_multi_model=True,
        model_selection_strategy="phase_based",
        enable_model_fallback=True,
        multi_models=[
            # GPT-4 Turbo - Premium model for complex phases
            MultiModelConfig(
                name="gpt-4-turbo",
                provider=LLMProvider.OPENAI,
                model="gpt-4-turbo-preview",
                cost_per_1k_tokens=0.01,  # $0.01 per 1K tokens (input)
                max_tokens=4096,
                suitable_phases=["ARCHITECTURE", "DESIGN", "DELIVERY"],
                priority=2,  # Higher priority
            ),
            # GPT-3.5 Turbo - Fast, cost-effective for simpler phases
            MultiModelConfig(
                name="gpt-3.5-turbo",
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                cost_per_1k_tokens=0.0005,  # $0.0005 per 1K tokens
                max_tokens=4096,
                suitable_phases=["DISCOVERY", "QUALITY_ASSURANCE"],
                priority=1,  # Lower priority (fallback)
            ),
        ],
    )


def create_cost_optimized_setup(
    api_key: Optional[str] = None, logger: Optional[logging.Logger] = None
) -> LLMConfig:
    """
    Create a cost-optimized multi-model configuration.

    Uses GPT-3.5 Turbo for everything with GPT-4 as fallback only.

    Args:
        api_key: OpenAI API key
        logger: Optional logger

    Returns:
        LLMConfig with cost-optimized setup
    """
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        temperature=0.3,
        api_key=api_key,
        enable_multi_model=True,
        model_selection_strategy="cost_optimized",
        enable_model_fallback=True,
        multi_models=[
            # GPT-3.5 Turbo - Primary for cost savings
            MultiModelConfig(
                name="gpt-3.5-turbo",
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                cost_per_1k_tokens=0.0005,
                max_tokens=4096,
                suitable_phases=[
                    "DISCOVERY",
                    "ARCHITECTURE",
                    "DESIGN",
                    "DELIVERY",
                    "QUALITY_ASSURANCE",
                ],
                priority=2,  # Higher priority
            ),
            # GPT-4 - Fallback only for when 3.5 fails
            MultiModelConfig(
                name="gpt-4",
                provider=LLMProvider.OPENAI,
                model="gpt-4",
                cost_per_1k_tokens=0.03,
                max_tokens=4096,
                suitable_phases=["ARCHITECTURE", "DESIGN", "DELIVERY"],
                priority=1,  # Lower priority (fallback)
            ),
        ],
    )


def create_performance_first_setup(
    api_key: Optional[str] = None, logger: Optional[logging.Logger] = None
) -> LLMConfig:
    """
    Create a performance-first multi-model configuration.

    Uses GPT-4 for everything with GPT-3.5 as backup.

    Args:
        api_key: OpenAI API key
        logger: Optional logger

    Returns:
        LLMConfig with performance-first setup
    """
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4-turbo",
        temperature=0.3,
        api_key=api_key,
        enable_multi_model=True,
        model_selection_strategy="performance_first",
        enable_model_fallback=True,
        multi_models=[
            # GPT-4 Turbo - Primary for best quality
            MultiModelConfig(
                name="gpt-4-turbo",
                provider=LLMProvider.OPENAI,
                model="gpt-4-turbo-preview",
                cost_per_1k_tokens=0.01,
                max_tokens=4096,
                suitable_phases=[
                    "DISCOVERY",
                    "ARCHITECTURE",
                    "DESIGN",
                    "DELIVERY",
                    "QUALITY_ASSURANCE",
                ],
                priority=2,
            ),
            # GPT-3.5 - Fallback
            MultiModelConfig(
                name="gpt-3.5-turbo",
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                cost_per_1k_tokens=0.0005,
                max_tokens=4096,
                suitable_phases=["DISCOVERY", "QUALITY_ASSURANCE"],
                priority=1,
            ),
        ],
    )
