"""
Cache Backends

Different storage backends for caching:
- InMemoryCache: Fast, volatile
- FileCache: Persistent, disk-based
"""

import hashlib
import json
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from caas_framework.utils.logger import get_logger


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime
    ttl_seconds: int
    metadata: Dict[str, Any]

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl_seconds <= 0:
            return False  # No expiration

        expiration = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiration

    def time_to_expiry(self) -> Optional[float]:
        """Get seconds until expiry (None if no expiration)"""
        if self.ttl_seconds <= 0:
            return None

        expiration = self.created_at + timedelta(seconds=self.ttl_seconds)
        delta = expiration - datetime.now()
        return max(0, delta.total_seconds())


class CacheBackend(ABC):
    """Abstract cache backend interface"""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key"""

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set cache entry"""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cache entry, returns True if deleted"""

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""


class InMemoryCacheBackend(CacheBackend):
    """
    In-memory cache backend.

    Fast but volatile - data lost on restart.
    Good for development and short-lived sessions.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries (LRU eviction)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []  # For LRU tracking
        self.max_size = max_size
        self.logger = get_logger()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key"""
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check expiration
        if entry.is_expired():
            await self.delete(key)
            self._misses += 1
            return None

        # Update access order (LRU)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        self._hits += 1
        return entry

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set cache entry"""
        # Evict if at max size
        if len(self._cache) >= self.max_size and key not in self._cache:
            await self._evict_lru()

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        self._cache[key] = entry

        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._access_order.clear()
        self.logger.info("🗑️ Cache cleared")

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        entry = await self.get(key)
        return entry is not None

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self._access_order:
            lru_key = self._access_order[0]
            await self.delete(lru_key)
            self._evictions += 1
            self.logger.debug(f"⚠️ Evicted LRU entry: {lru_key}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "backend": "in_memory",
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "evictions": self._evictions,
        }


class FileCacheBackend(CacheBackend):
    """
    File-based persistent cache backend.

    Stores cache entries as files on disk.
    Survives restarts but slower than in-memory.
    """

    def __init__(
        self, cache_dir: str = ".cache", max_size_mb: int = 100, use_pickle: bool = True
    ):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum cache size in MB
            use_pickle: Use pickle for serialization (faster but binary)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.use_pickle = use_pickle
        self.logger = get_logger()

        # Metrics
        self._hits = 0
        self._misses = 0

    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Hash key to create safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key"""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            self._misses += 1
            return None

        try:
            # Load entry
            if self.use_pickle:
                with open(file_path, "rb") as f:
                    entry = pickle.load(f)
            else:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    entry = CacheEntry(
                        key=data["key"],
                        value=data["value"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        ttl_seconds=data["ttl_seconds"],
                        metadata=data["metadata"],
                    )

            # Check expiration
            if entry.is_expired():
                await self.delete(key)
                self._misses += 1
                return None

            self._hits += 1
            return entry

        except Exception as e:
            self.logger.error(f"Failed to load cache entry {key}: {e}")
            self._misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set cache entry"""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        file_path = self._get_file_path(key)

        try:
            # Save entry
            if self.use_pickle:
                with open(file_path, "wb") as f:
                    pickle.dump(entry, f)
            else:
                with open(file_path, "w") as f:
                    data = {
                        "key": entry.key,
                        "value": entry.value,
                        "created_at": entry.created_at.isoformat(),
                        "ttl_seconds": entry.ttl_seconds,
                        "metadata": entry.metadata,
                    }
                    json.dump(data, f, indent=2)

            # Check cache size and cleanup if needed
            await self._cleanup_if_needed()

        except Exception as e:
            self.logger.error(f"Failed to save cache entry {key}: {e}")

    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        file_path = self._get_file_path(key)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        for file_path in self.cache_dir.glob("*.cache"):
            file_path.unlink()
        self.logger.info("🗑️ Cache cleared")

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        entry = await self.get(key)
        return entry is not None

    async def _cleanup_if_needed(self) -> None:
        """Cleanup old entries if cache size exceeds limit"""
        # Calculate total size
        total_size_mb = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.cache")
        ) / (1024 * 1024)

        if total_size_mb > self.max_size_mb:
            # Delete oldest files until under limit
            files = sorted(
                self.cache_dir.glob("*.cache"), key=lambda f: f.stat().st_mtime
            )

            for file_path in files:
                file_path.unlink()
                total_size_mb -= file_path.stat().st_size / (1024 * 1024)

                if total_size_mb <= self.max_size_mb:
                    break

            self.logger.info(f"🧹 Cache cleanup: reduced to {total_size_mb:.1f}MB")

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        # Calculate cache size
        cache_size_mb = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.cache")
        ) / (1024 * 1024)

        file_count = len(list(self.cache_dir.glob("*.cache")))

        return {
            "backend": "file",
            "cache_dir": str(self.cache_dir),
            "size_mb": f"{cache_size_mb:.2f}",
            "max_size_mb": self.max_size_mb,
            "file_count": file_count,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }
