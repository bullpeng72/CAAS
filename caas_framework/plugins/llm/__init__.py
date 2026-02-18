"""
LLM Plugins

Supported providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Ollama (Local models)
- Azure OpenAI

Multi-Model Support:
- MultiModelRouter for intelligent model selection
- Automatic fallback chains
- Performance tracking
- Cost optimization
"""

# Import plugin implementations to trigger registration
from caas_framework.plugins.llm import openai  # noqa: F401
from caas_framework.plugins.llm import ollama  # noqa: F401
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.plugins.llm.factory import (
    create_cost_optimized_setup,
    create_default_multi_model_setup,
    create_llm_plugin,
    create_multi_model_router,
    create_performance_first_setup,
)
from caas_framework.plugins.llm.multi_model_router import (
    ModelConfig,
    ModelMetrics,
    ModelPerformanceTracker,
    ModelSelectionStrategy,
    MultiModelRouter,
)

# Global multi-model router instance
_multi_model_router = None


def get_multi_model_router() -> MultiModelRouter:
    """Get or create the global MultiModelRouter instance.

    Uses current settings if multi-model is configured, otherwise falls back
    to a default setup so the router can be listed without API keys.
    """
    global _multi_model_router
    if _multi_model_router is None:
        import os
        default_config = create_default_multi_model_setup(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        _multi_model_router = create_multi_model_router(default_config)
    return _multi_model_router


__all__ = [
    "LLMPlugin",
    "MultiModelRouter",
    "ModelConfig",
    "ModelSelectionStrategy",
    "ModelMetrics",
    "ModelPerformanceTracker",
    "create_llm_plugin",
    "create_multi_model_router",
    "create_default_multi_model_setup",
    "create_cost_optimized_setup",
    "create_performance_first_setup",
    "get_multi_model_router",
]
