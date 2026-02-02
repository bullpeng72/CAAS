"""
LLM Cache Wrapper

Transparent caching layer for LLM responses.
Wraps LLM plugins to automatically cache and retrieve responses.
"""

import hashlib
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.caching.cache_manager import CacheKey, CacheManager
from caas_framework.plugins.llm.base import LLMMessage, LLMPlugin, LLMResponse


class LLMCacheWrapper(LLMPlugin):
    """
    LLM plugin wrapper with automatic caching.

    Caches LLM responses based on:
    - Messages content
    - Model
    - Temperature
    - Phase (if provided)
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        cache_manager: CacheManager,
        enable_cache: bool = True,
        cache_ttl: int = 3600,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize LLM cache wrapper.

        Args:
            llm_plugin: LLM plugin to wrap
            cache_manager: Cache manager
            enable_cache: Enable caching (can be disabled for debugging)
            cache_ttl: Cache TTL in seconds
            logger: Optional logger
        """
        # Initialize as LLMPlugin with wrapped plugin's config
        super().__init__(
            name=f"{llm_plugin.name}-cached",
            config={
                "model": llm_plugin.model,
                "temperature": llm_plugin.temperature,
                "max_tokens": llm_plugin.max_tokens,
            },
        )

        self.llm = llm_plugin
        self.cache_manager = cache_manager
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.logger = logger or logging.getLogger(__name__)

        # Update model from wrapped plugin
        self.model = llm_plugin.model

    async def initialize(self) -> None:
        """Initialize wrapped LLM plugin"""
        if not self.llm.is_initialized:
            await self.llm.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close wrapped LLM plugin"""
        await self.llm.close()

    async def health_check(self) -> bool:
        """Check health of wrapped plugin"""
        return await self.llm.health_check()

    def _build_cache_key(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float],
        max_tokens: Optional[int],
        response_format: Optional[str],
        phase: Optional[AgentPhase] = None,
        **kwargs,
    ) -> CacheKey:
        """
        Build cache key from LLM call parameters.

        Args:
            messages: Messages
            temperature: Temperature
            max_tokens: Max tokens
            response_format: Response format
            phase: Optional phase
            **kwargs: Additional params

        Returns:
            CacheKey
        """
        # Create deterministic hash of messages
        messages_dict = [
            {
                "role": msg.role if hasattr(msg, "role") else msg.get("role"),
                "content": msg.content if hasattr(msg, "content") else msg.get("content"),
            }
            for msg in messages
        ]
        messages_json = json.dumps(messages_dict, sort_keys=True)
        messages_hash = hashlib.sha256(messages_json.encode()).hexdigest()[:16]

        # Build cache key
        cache_key = CacheKey(
            namespace="llm_response",
            phase=phase,
            model=self.model,
            requirement_hash=messages_hash,
            additional_params={
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
                "response_format": response_format,
            },
        )

        return cache_key

    async def ainvoke(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        phase: Optional[AgentPhase] = None,
        bypass_cache: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """
        Async LLM call with caching.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            response_format: "text" or "json"
            phase: Optional phase for cache key
            bypass_cache: Skip cache and force LLM call
            **kwargs: Provider-specific args

        Returns:
            LLMResponse (from cache or LLM)
        """
        # Build cache key
        cache_key = self._build_cache_key(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            phase=phase,
            **kwargs,
        )

        # Try cache first (if enabled and not bypassed)
        if self.enable_cache and not bypass_cache:
            cached_response = await self.cache_manager.get(cache_key)

            if cached_response is not None:
                self.logger.debug(
                    f"💾 Cache HIT for {self.model} " f"(phase: {phase.value if phase else 'none'})"
                )
                return cached_response

        # Cache miss - call LLM
        self.logger.debug(
            f"🔄 Cache MISS for {self.model} - calling LLM "
            f"(phase: {phase.value if phase else 'none'})"
        )

        response = await self.llm.ainvoke(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs,
        )

        # Cache the response (if enabled)
        if self.enable_cache:
            await self.cache_manager.set(
                cache_key=cache_key,
                value=response,
                ttl=self.cache_ttl,
                metadata={
                    "model": self.model,
                    "phase": phase.value if phase else None,
                    "tokens_used": response.usage.get("total_tokens", 0) if response.usage else 0,
                },
            )

        return response

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Streaming LLM call.

        Note: Streaming responses are not cached.

        Args:
            messages: List of messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific args

        Yields:
            Token chunks
        """
        self.logger.debug(f"🔄 Streaming (no cache) for {self.model}")

        async for chunk in self.llm.stream(
            messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        ):
            yield chunk

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        hit_rate = self.cache_manager.get_hit_rate(namespace="llm_response")

        return {
            "enabled": self.enable_cache,
            "ttl_seconds": self.cache_ttl,
            "hit_rate": f"{hit_rate:.1f}%",
            "model": self.model,
        }

    async def invalidate_cache(self, phase: Optional[AgentPhase] = None) -> None:
        """
        Invalidate cached responses.

        Args:
            phase: Optional phase to invalidate (invalidates all if None)
        """
        if phase:
            self.logger.info(f"🗑️ Invalidating cache for phase: {phase.value}")
            # Note: Namespace invalidation requires backend support
            await self.cache_manager.invalidate_namespace("llm_response")
        else:
            self.logger.info("🗑️ Invalidating all LLM cache")
            await self.cache_manager.clear()


def wrap_llm_with_cache(
    llm_plugin: LLMPlugin,
    cache_manager: CacheManager,
    enable_cache: bool = True,
    cache_ttl: int = 3600,
) -> LLMCacheWrapper:
    """
    Wrap an LLM plugin with caching.

    Convenience function to create cached LLM wrapper.

    Args:
        llm_plugin: LLM plugin to wrap
        cache_manager: Cache manager
        enable_cache: Enable caching
        cache_ttl: Cache TTL in seconds

    Returns:
        LLMCacheWrapper instance
    """
    return LLMCacheWrapper(
        llm_plugin=llm_plugin,
        cache_manager=cache_manager,
        enable_cache=enable_cache,
        cache_ttl=cache_ttl,
    )
