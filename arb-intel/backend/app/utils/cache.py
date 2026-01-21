"""In-memory caching utilities."""

from datetime import datetime, timedelta
from typing import Any, TypeVar, Generic
from dataclasses import dataclass, field

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Single cache entry with timestamp."""
    value: T
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self, max_age_seconds: float) -> bool:
        """Check if entry is expired."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > max_age_seconds


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl_seconds: float = 10.0):
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str, max_age_seconds: float | None = None) -> Any | None:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        ttl = max_age_seconds if max_age_seconds is not None else self._default_ttl

        if entry.is_expired(ttl):
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = CacheEntry(value=value)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self, max_age_seconds: float | None = None) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        ttl = max_age_seconds if max_age_seconds is not None else self._default_ttl
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired(ttl)
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def size(self) -> int:
        """Return number of entries in cache."""
        return len(self._cache)


# Global cache instance
market_cache = InMemoryCache(default_ttl_seconds=10.0)
