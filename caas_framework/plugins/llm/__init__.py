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
]
