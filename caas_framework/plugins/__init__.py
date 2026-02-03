"""
Plugin System for CAAS Framework

Provides pluggable architecture for:
- LLM providers (OpenAI, Anthropic, Ollama, etc.)
- Vector databases (Pinecone, Qdrant, Chroma, etc.)
- Graph databases (Neo4j, ArangoDB, Embedded, etc.)
"""

# Import plugin modules to trigger registration
from caas_framework.plugins import (
    graphdb,  # noqa: F401
    llm,  # noqa: F401
    vectordb,  # noqa: F401
)
from caas_framework.plugins.base import Plugin, PluginRegistry

__all__ = ["Plugin", "PluginRegistry"]
