"""Redis cache layer for frequently accessed data.

Caches dimension hierarchies, current period variances, and query results.
Gracefully degrades to no-cache mode when Redis is unavailable.

Phase 3E: Full implementation replacing TODO stubs.

Usage::

    cache = CacheClient("redis://localhost:6379/0")
    await cache.connect()
    await cache.set("summary:2026-06:MTD:BUDGET", data, ttl_seconds=300)
    result = await cache.get("summary:2026-06:MTD:BUDGET")
    await cache.invalidate_pattern("*:2026-06:*")  # Clear all period caches
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheClient:
    """Redis-backed cache for the variance agent.

    Falls back to no-op when Redis is unavailable — the application
    works correctly but without caching.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
        self._redis: Any = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Whether Redis is connected and available."""
        return self._connected

    async def connect(self) -> None:
        """Establish Redis connection. Graceful on failure."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info("Redis cache connected: %s", self.redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed (%s) — running without cache", exc)
            self._redis = None
            self._connected = False

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None on miss or if Redis unavailable."""
        if not self._connected or not self._redis:
            return None
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a cached value with TTL. No-op if Redis unavailable."""
        if not self._connected or not self._redis:
            return
        try:
            serialized = json.dumps(value, default=str)
            await self._redis.set(key, serialized, ex=ttl_seconds)
        except Exception as exc:
            logger.debug("Cache set failed for %s: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Delete a cached key. No-op if Redis unavailable."""
        if not self._connected or not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception:
            pass

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern (e.g. '*:2026-06:*').

        Returns number of keys deleted. 0 if Redis unavailable.
        """
        if not self._connected or not self._redis:
            return 0
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info("Cache invalidated %d keys matching '%s'", deleted, pattern)
                return deleted
            return 0
        except Exception as exc:
            logger.debug("Cache invalidation failed for '%s': %s", pattern, exc)
            return 0

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            self._connected = False
            logger.info("Redis cache disconnected")
