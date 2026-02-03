"""
Tests for Advanced Caching System

Tests cache backends, cache manager, and LLM caching.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from caas_framework.agents.base import AgentPhase
from caas_framework.caching.backends import (
    CacheEntry,
    FileCacheBackend,
    InMemoryCacheBackend,
)
from caas_framework.caching.cache_manager import CacheKey, CacheManager, CacheMetrics
from caas_framework.caching.llm_cache import LLMCacheWrapper
from caas_framework.plugins.llm.base import LLMMessage, LLMResponse

# ==================== Backend Tests ====================

@pytest.mark.asyncio
async def test_in_memory_backend_basic():
    """Test basic in-memory cache operations"""
    backend = InMemoryCacheBackend(max_size=10)

    # Set value
    await backend.set("key1", "value1", ttl_seconds=60)

    # Get value
    entry = await backend.get("key1")
    assert entry is not None
    assert entry.value == "value1"
    assert not entry.is_expired()

    # Exists
    exists = await backend.exists("key1")
    assert exists is True

    # Delete
    deleted = await backend.delete("key1")
    assert deleted is True

    # Get after delete
    entry = await backend.get("key1")
    assert entry is None


@pytest.mark.asyncio
async def test_in_memory_lru_eviction():
    """Test LRU eviction in memory cache"""
    backend = InMemoryCacheBackend(max_size=3)

    # Fill cache
    await backend.set("key1", "value1")
    await backend.set("key2", "value2")
    await backend.set("key3", "value3")

    # Add one more - should evict key1 (LRU)
    await backend.set("key4", "value4")

    # key1 should be evicted
    assert await backend.exists("key1") is False
    assert await backend.exists("key2") is True
    assert await backend.exists("key3") is True
    assert await backend.exists("key4") is True


@pytest.mark.asyncio
async def test_in_memory_metrics():
    """Test in-memory cache metrics"""
    backend = InMemoryCacheBackend()

    # Generate some hits and misses
    await backend.set("key1", "value1")
    await backend.get("key1")  # Hit
    await backend.get("key2")  # Miss

    metrics = backend.get_metrics()

    assert metrics["backend"] == "in_memory"
    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert "50.0%" in metrics["hit_rate"]


@pytest.mark.asyncio
async def test_file_backend_basic():
    """Test basic file cache operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = FileCacheBackend(cache_dir=tmpdir)

        # Set value
        await backend.set("key1", {"data": "test"}, ttl_seconds=60)

        # Get value
        entry = await backend.get("key1")
        assert entry is not None
        assert entry.value == {"data": "test"}

        # File should exist
        cache_files = list(Path(tmpdir).glob("*.cache"))
        assert len(cache_files) == 1

        # Clear cache
        await backend.clear()
        cache_files = list(Path(tmpdir).glob("*.cache"))
        assert len(cache_files) == 0


@pytest.mark.asyncio
async def test_cache_entry_expiration():
    """Test cache entry expiration"""
    # Create expired entry
    entry = CacheEntry(
        key="test",
        value="data",
        created_at=datetime.now() - timedelta(seconds=100),
        ttl_seconds=60,
        metadata={}
    )

    assert entry.is_expired() is True

    # Create non-expired entry
    entry2 = CacheEntry(
        key="test2",
        value="data2",
        created_at=datetime.now(),
        ttl_seconds=60,
        metadata={}
    )

    assert entry2.is_expired() is False


# ==================== Cache Manager Tests ====================

def test_cache_key_generation():
    """Test deterministic cache key generation"""
    key1 = CacheKey(
        namespace="test",
        phase=AgentPhase.DISCOVERY,
        model="gpt-4",
        requirement_hash="abc123",
        additional_params={"temp": 0.7}
    )

    key2 = CacheKey(
        namespace="test",
        phase=AgentPhase.DISCOVERY,
        model="gpt-4",
        requirement_hash="abc123",
        additional_params={"temp": 0.7}
    )

    # Same inputs should generate same key
    assert key1.build() == key2.build()

    # Different inputs should generate different key
    key3 = CacheKey(
        namespace="test",
        phase=AgentPhase.ARCHITECTURE,  # Different phase
        model="gpt-4",
        requirement_hash="abc123"
    )

    assert key1.build() != key3.build()


def test_cache_key_hash_requirement():
    """Test requirement hashing"""
    req1 = "Build a todo app"
    req2 = "Build a todo app"
    req3 = "Build a different app"

    hash1 = CacheKey.hash_requirement(req1)
    hash2 = CacheKey.hash_requirement(req2)
    hash3 = CacheKey.hash_requirement(req3)

    assert hash1 == hash2
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_cache_manager_basic():
    """Test basic cache manager operations"""
    backend = InMemoryCacheBackend()
    manager = CacheManager(backend=backend)

    cache_key = CacheKey(namespace="test", requirement_hash="123")

    # Set value
    await manager.set(cache_key, "test_value")

    # Get value
    value = await manager.get(cache_key)
    assert value == "test_value"

    # Invalidate
    invalidated = await manager.invalidate(cache_key)
    assert invalidated is True

    # Get after invalidation
    value = await manager.get(cache_key)
    assert value is None


@pytest.mark.asyncio
async def test_cache_manager_get_or_compute():
    """Test get_or_compute functionality"""
    backend = InMemoryCacheBackend()
    manager = CacheManager(backend=backend)

    call_count = 0

    async def expensive_computation(**kwargs):
        nonlocal call_count
        call_count += 1
        return "computed_value"

    cache_key = CacheKey(namespace="test", requirement_hash="123")

    # First call - should compute
    value1 = await manager.get_or_compute(cache_key, expensive_computation)
    assert value1 == "computed_value"
    assert call_count == 1

    # Second call - should use cache
    value2 = await manager.get_or_compute(cache_key, expensive_computation)
    assert value2 == "computed_value"
    assert call_count == 1  # Not incremented (cached)


@pytest.mark.asyncio
async def test_cache_manager_metrics():
    """Test cache manager metrics"""
    backend = InMemoryCacheBackend()
    manager = CacheManager(backend=backend, enable_metrics=True)

    cache_key = CacheKey(namespace="test", requirement_hash="123")

    # Generate hits and misses
    await manager.set(cache_key, "value")
    await manager.get(cache_key)  # Hit
    await manager.get(CacheKey(namespace="test", requirement_hash="456"))  # Miss

    metrics = manager.get_metrics()

    assert metrics["manager_metrics"]["cache_hits"] == 1
    assert metrics["manager_metrics"]["cache_misses"] == 1
    assert "50.0%" in metrics["manager_metrics"]["hit_rate"]


@pytest.mark.asyncio
async def test_cache_manager_ttl_override():
    """Test TTL override per namespace"""
    backend = InMemoryCacheBackend()
    manager = CacheManager(backend=backend, default_ttl=100)

    # Set custom TTL for namespace
    manager.set_ttl_override("custom_namespace", 500)

    cache_key = CacheKey(namespace="custom_namespace", requirement_hash="123")
    await manager.set(cache_key, "value")

    # Check that entry has correct TTL
    entry = await backend.get(cache_key.build())
    assert entry.ttl_seconds == 500


# ==================== LLM Cache Tests ====================

class MockLLMPlugin:
    """Mock LLM plugin for testing"""

    def __init__(self):
        self.name = "mock-llm"
        self.model = "mock-model"
        self.temperature = 0.7
        self.max_tokens = 1000
        self._initialized = False
        self.call_count = 0

    async def initialize(self):
        self._initialized = True

    async def close(self):
        pass

    async def health_check(self):
        return True

    @property
    def is_initialized(self):
        return self._initialized

    async def ainvoke(self, messages, **kwargs):
        self.call_count += 1
        return LLMResponse(
            content="Mock response",
            model=self.model,
            usage={"total_tokens": 50}
        )

    async def stream(self, messages, **kwargs):
        async def _gen():
            yield "Mock"
            yield " stream"
        return _gen()


@pytest.mark.asyncio
async def test_llm_cache_wrapper_basic():
    """Test basic LLM caching"""
    backend = InMemoryCacheBackend()
    cache_manager = CacheManager(backend=backend)
    mock_llm = MockLLMPlugin()

    cached_llm = LLMCacheWrapper(
        llm_plugin=mock_llm,
        cache_manager=cache_manager,
        enable_cache=True
    )

    messages = [LLMMessage(role="user", content="test")]

    # First call - should hit LLM
    response1 = await cached_llm.ainvoke(messages, phase=AgentPhase.DISCOVERY)
    assert response1.content == "Mock response"
    assert mock_llm.call_count == 1

    # Second call - should use cache
    response2 = await cached_llm.ainvoke(messages, phase=AgentPhase.DISCOVERY)
    assert response2.content == "Mock response"
    assert mock_llm.call_count == 1  # Not incremented


@pytest.mark.asyncio
async def test_llm_cache_bypass():
    """Test cache bypass"""
    backend = InMemoryCacheBackend()
    cache_manager = CacheManager(backend=backend)
    mock_llm = MockLLMPlugin()

    cached_llm = LLMCacheWrapper(
        llm_plugin=mock_llm,
        cache_manager=cache_manager,
        enable_cache=True
    )

    messages = [LLMMessage(role="user", content="test")]

    # First call
    await cached_llm.ainvoke(messages)
    assert mock_llm.call_count == 1

    # Second call with bypass_cache=True
    await cached_llm.ainvoke(messages, bypass_cache=True)
    assert mock_llm.call_count == 2  # LLM called again


@pytest.mark.asyncio
async def test_llm_cache_different_params():
    """Test that different parameters create different cache keys"""
    backend = InMemoryCacheBackend()
    cache_manager = CacheManager(backend=backend)
    mock_llm = MockLLMPlugin()

    cached_llm = LLMCacheWrapper(
        llm_plugin=mock_llm,
        cache_manager=cache_manager
    )

    messages = [LLMMessage(role="user", content="test")]

    # Call with temperature 0.7
    await cached_llm.ainvoke(messages, temperature=0.7)
    assert mock_llm.call_count == 1

    # Call with temperature 0.3 - different key, should call LLM
    await cached_llm.ainvoke(messages, temperature=0.3)
    assert mock_llm.call_count == 2


@pytest.mark.asyncio
async def test_llm_cache_stats():
    """Test LLM cache statistics"""
    backend = InMemoryCacheBackend()
    cache_manager = CacheManager(backend=backend, enable_metrics=True)
    mock_llm = MockLLMPlugin()

    cached_llm = LLMCacheWrapper(
        llm_plugin=mock_llm,
        cache_manager=cache_manager
    )

    messages = [LLMMessage(role="user", content="test")]

    # Generate some cache hits
    await cached_llm.ainvoke(messages)  # Miss
    await cached_llm.ainvoke(messages)  # Hit

    stats = cached_llm.get_cache_stats()

    assert stats["enabled"] is True
    assert stats["model"] == "mock-model"
    assert "50.0%" in stats["hit_rate"]


@pytest.mark.asyncio
async def test_cache_metrics_tracking():
    """Test CacheMetrics tracking"""
    metrics = CacheMetrics()

    metrics.add_hit("namespace1")
    metrics.add_hit("namespace1")
    metrics.add_miss("namespace1")
    metrics.add_miss("namespace2")

    assert metrics.total_requests == 4
    assert metrics.cache_hits == 2
    assert metrics.cache_misses == 2
    assert metrics.hit_rate_percent == 50.0

    # Check namespace-specific metrics
    assert metrics.namespaces["namespace1"]["hits"] == 2
    assert metrics.namespaces["namespace1"]["misses"] == 1
    assert metrics.namespaces["namespace2"]["misses"] == 1
