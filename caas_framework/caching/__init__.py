"""
Advanced Caching System

Intelligent caching for LLM responses, validation results, and more.
Supports multiple backends, TTL, invalidation, and metrics.
"""

from caas_framework.caching.backends import (
    CacheBackend,
    FileCacheBackend,
    InMemoryCacheBackend,
)
from caas_framework.caching.cache_manager import (
    CacheKey,
    CacheManager,
    CacheMetrics,
)
from caas_framework.caching.llm_cache import LLMCacheWrapper

# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get or create the global CacheManager instance (in-memory backend)."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(backend=InMemoryCacheBackend())
    return _cache_manager


__all__ = [
    "CacheManager",
    "CacheKey",
    "CacheMetrics",
    "CacheBackend",
    "InMemoryCacheBackend",
    "FileCacheBackend",
    "LLMCacheWrapper",
    "get_cache_manager",
]
