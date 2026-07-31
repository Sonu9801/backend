"""
Simple TTL cache for hot-path user lookups.

Avoids hitting the database on every authenticated request.
Default TTL is 5 minutes — stale data is acceptable for this window
since user role/status changes are rare.

Drop-in replaceable with Redis if needed.
"""
import threading
from datetime import datetime, timedelta
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl_seconds: int = 300):
        self._store: dict[str, tuple[Any, datetime]] = {}  # key -> (value, expires_at)
        self._default_ttl = default_ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None if expired or missing."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if datetime.utcnow() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a value with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        with self._lock:
            self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> bool:
        """Remove a key from cache. Returns True if it existed."""
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = datetime.utcnow()
        expired = []
        with self._lock:
            for key, (_, expires_at) in self._store.items():
                if now > expires_at:
                    expired.append(key)
            for key in expired:
                del self._store[key]
        return len(expired)


# Global cache for user objects (keyed by user_id or email)
user_cache = TTLCache(default_ttl_seconds=300)  # 5 minutes
