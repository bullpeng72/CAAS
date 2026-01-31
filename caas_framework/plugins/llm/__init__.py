"""
LLM Plugins

Supported providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Ollama (Local models)
- Azure OpenAI
"""

from caas_framework.plugins.llm.base import LLMPlugin

__all__ = ["LLMPlugin"]
