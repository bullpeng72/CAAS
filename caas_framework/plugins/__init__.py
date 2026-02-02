"""
Plugin System for CAAS Framework

Provides pluggable architecture for:
- LLM providers (OpenAI, Anthropic, Ollama, etc.)
- Vector databases (Pinecone, Qdrant, Chroma, etc.)
- Graph databases (Neo4j, ArangoDB, Embedded, etc.)
"""

from caas_framework.plugins.base import Plugin, PluginRegistry

# Import plugin modules to trigger registration
from caas_framework.plugins import llm  # noqa: F401
from caas_framework.plugins import graphdb  # noqa: F401
from caas_framework.plugins import vectordb  # noqa: F401

__all__ = ["Plugin", "PluginRegistry"]
