"""
Cache Manager

High-level cache orchestration with intelligent key generation,
TTL management, and comprehensive metrics.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.caching.backends import CacheBackend, CacheEntry


@dataclass
class CacheKey:
    """
    Cache key builder for deterministic key generation.

    Ensures consistent cache keys across runs.
    """

    namespace: str  # e.g., "llm_response", "validation", "golden_data"
    phase: Optional[AgentPhase] = None
    model: Optional[str] = None
    requirement_hash: Optional[str] = None
    additional_params: Dict[str, Any] = field(default_factory=dict)

    def build(self) -> str:
        """
        Build deterministic cache key.

        Returns:
            SHA256 hash of all key components
        """
        components = {
            "namespace": self.namespace,
            "phase": self.phase.value if self.phase else None,
            "model": self.model,
            "requirement_hash": self.requirement_hash,
            "additional_params": self.additional_params,
        }

        # Sort dict for deterministic JSON
        json_str = json.dumps(components, sort_keys=True)
        key_hash = hashlib.sha256(json_str.encode()).hexdigest()

        return f"{self.namespace}:{key_hash}"

    @staticmethod
    def hash_requirement(requirement: str) -> str:
        """Generate hash for requirement text"""
        return hashlib.sha256(requirement.encode()).hexdigest()[:16]


@dataclass
class CacheMetrics:
    """Aggregated cache metrics"""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    hit_rate_percent: float = 0.0
    namespaces: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def add_hit(self, namespace: str):
        """Record cache hit"""
        self.total_requests += 1
        self.cache_hits += 1
        self._update_namespace(namespace, hits=1)
        self._update_hit_rate()

    def add_miss(self, namespace: str):
        """Record cache miss"""
        self.total_requests += 1
        self.cache_misses += 1
        self._update_namespace(namespace, misses=1)
        self._update_hit_rate()

    def _update_namespace(self, namespace: str, hits: int = 0, misses: int = 0):
        """Update namespace-specific metrics"""
        if namespace not in self.namespaces:
            self.namespaces[namespace] = {"hits": 0, "misses": 0}

        self.namespaces[namespace]["hits"] += hits
        self.namespaces[namespace]["misses"] += misses

    def _update_hit_rate(self):
        """Recalculate hit rate"""
        if self.total_requests > 0:
            self.hit_rate_percent = (self.cache_hits / self.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.hit_rate_percent:.1f}%",
            "namespaces": self.namespaces,
        }


class CacheManager:
    """
    High-level cache manager.

    Orchestrates caching with:
    - Intelligent key generation
    - Multiple backends
    - TTL management
    - Metrics tracking
    - Invalidation strategies
    """

    def __init__(
        self,
        backend: CacheBackend,
        default_ttl: int = 3600,
        enable_metrics: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize cache manager.

        Args:
            backend: Cache backend to use
            default_ttl: Default TTL in seconds (3600 = 1 hour)
            enable_metrics: Enable metrics tracking
            logger: Optional logger
        """
        self.backend = backend
        self.default_ttl = default_ttl
        self.enable_metrics = enable_metrics
        self.logger = logger or logging.getLogger(__name__)

        self.metrics = CacheMetrics()

        # Namespace-specific TTLs
        self.ttl_overrides: Dict[str, int] = {
            "llm_response": 3600,  # 1 hour
            "validation": 1800,  # 30 minutes
            "golden_data": 7200,  # 2 hours
            "phase_output": 3600,  # 1 hour
        }

    async def get(self, cache_key: CacheKey, default: Any = None) -> Optional[Any]:
        """
        Get cached value.

        Args:
            cache_key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        key_str = cache_key.build()
        entry = await self.backend.get(key_str)

        if entry is not None:
            if self.enable_metrics:
                self.metrics.add_hit(cache_key.namespace)

            self.logger.debug(f"✅ Cache HIT: {cache_key.namespace}")
            return entry.value
        else:
            if self.enable_metrics:
                self.metrics.add_miss(cache_key.namespace)

            self.logger.debug(f"❌ Cache MISS: {cache_key.namespace}")
            return default

    async def set(
        self,
        cache_key: CacheKey,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Set cached value.

        Args:
            cache_key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            metadata: Optional metadata
        """
        key_str = cache_key.build()

        # Determine TTL
        if ttl is None:
            ttl = self.ttl_overrides.get(cache_key.namespace, self.default_ttl)

        # Add cache metadata
        cache_metadata = metadata or {}
        cache_metadata.update(
            {
                "namespace": cache_key.namespace,
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": ttl,
            }
        )

        await self.backend.set(key=key_str, value=value, ttl_seconds=ttl, metadata=cache_metadata)

        self.logger.debug(f"💾 Cached: {cache_key.namespace} (TTL: {ttl}s)")

    async def get_or_compute(
        self, cache_key: CacheKey, compute_fn: Callable, ttl: Optional[int] = None, **compute_kwargs
    ) -> Any:
        """
        Get from cache or compute and cache.

        Args:
            cache_key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Optional TTL override
            **compute_kwargs: Arguments for compute_fn

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = await self.get(cache_key)

        if cached_value is not None:
            return cached_value

        # Compute value
        self.logger.debug(f"🔄 Computing: {cache_key.namespace}")
        computed_value = await compute_fn(**compute_kwargs)

        # Cache the result
        await self.set(cache_key, computed_value, ttl=ttl)

        return computed_value

    async def invalidate(self, cache_key: CacheKey) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            cache_key: Cache key to invalidate

        Returns:
            True if invalidated
        """
        key_str = cache_key.build()
        deleted = await self.backend.delete(key_str)

        if deleted:
            self.logger.info(f"🗑️ Invalidated: {cache_key.namespace}")

        return deleted

    async def invalidate_namespace(self, namespace: str) -> int:
        """
        Invalidate all entries in a namespace.

        Note: This requires backend support for pattern matching.
        For now, we clear the entire cache (limitation of simple backends).

        Args:
            namespace: Namespace to invalidate

        Returns:
            Number of entries invalidated
        """
        # TODO: Implement pattern-based deletion for backends that support it
        self.logger.warning(
            f"⚠️ Namespace invalidation not fully implemented. "
            f"Consider clearing entire cache or using Redis backend."
        )
        return 0

    async def clear(self) -> None:
        """Clear all cache entries"""
        await self.backend.clear()
        self.logger.info("🗑️ Cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache metrics.

        Returns:
            Dictionary with cache metrics
        """
        backend_metrics = self.backend.get_metrics()

        return {"manager_metrics": self.metrics.to_dict(), "backend_metrics": backend_metrics}

    def get_hit_rate(self, namespace: Optional[str] = None) -> float:
        """
        Get cache hit rate.

        Args:
            namespace: Optional namespace to get hit rate for

        Returns:
            Hit rate percentage (0-100)
        """
        if namespace and namespace in self.metrics.namespaces:
            ns_metrics = self.metrics.namespaces[namespace]
            total = ns_metrics["hits"] + ns_metrics["misses"]
            if total > 0:
                return (ns_metrics["hits"] / total) * 100

        return self.metrics.hit_rate_percent

    def set_ttl_override(self, namespace: str, ttl_seconds: int) -> None:
        """
        Set TTL override for a namespace.

        Args:
            namespace: Namespace to override
            ttl_seconds: TTL in seconds
        """
        self.ttl_overrides[namespace] = ttl_seconds
        self.logger.info(f"⏱️ Set TTL for '{namespace}': {ttl_seconds}s")
