"""
Plugin System for CAAS Framework

Provides pluggable architecture for:
- LLM providers (OpenAI, Anthropic, Ollama, etc.)
- Vector databases (Pinecone, Qdrant, Chroma, etc.)
- Graph databases (Neo4j, ArangoDB, Embedded, etc.)
"""

from caas_framework.plugins.base import Plugin, PluginRegistry

__all__ = ["Plugin", "PluginRegistry"]
