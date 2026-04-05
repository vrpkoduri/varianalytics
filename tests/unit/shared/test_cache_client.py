"""Tests for Phase 3E: Redis CacheClient.

Tests the cache client with and without Redis connection.
When Redis is unavailable, all operations gracefully return None/0.
"""

import pytest
import pytest_asyncio

from shared.data.cache import CacheClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_no_redis():
    """CacheClient pointed at non-existent Redis (graceful mode)."""
    return CacheClient(redis_url="redis://nonexistent:9999/0")


@pytest_asyncio.fixture
async def cache_with_redis():
    """CacheClient connected to running Redis (if available)."""
    client = CacheClient(redis_url="redis://localhost:6379/0")
    await client.connect()
    yield client
    await client.close()


# ---------------------------------------------------------------------------
# Tests: Graceful Degradation (no Redis)
# ---------------------------------------------------------------------------


class TestCacheWithoutRedis:
    """Test cache operations when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_connect_graceful_on_failure(self, cache_no_redis):
        """connect() doesn't raise when Redis is down."""
        await cache_no_redis.connect()
        assert cache_no_redis.is_connected is False

    @pytest.mark.asyncio
    async def test_get_returns_none(self, cache_no_redis):
        """get() returns None when not connected."""
        result = await cache_no_redis.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_noop(self, cache_no_redis):
        """set() does nothing when not connected."""
        await cache_no_redis.set("key", {"data": 123})  # No error

    @pytest.mark.asyncio
    async def test_delete_noop(self, cache_no_redis):
        """delete() does nothing when not connected."""
        await cache_no_redis.delete("key")  # No error

    @pytest.mark.asyncio
    async def test_invalidate_pattern_returns_zero(self, cache_no_redis):
        """invalidate_pattern() returns 0 when not connected."""
        result = await cache_no_redis.invalidate_pattern("*")
        assert result == 0

    @pytest.mark.asyncio
    async def test_close_noop(self, cache_no_redis):
        """close() does nothing when not connected."""
        await cache_no_redis.close()  # No error


# ---------------------------------------------------------------------------
# Tests: With Redis (if running)
# ---------------------------------------------------------------------------


class TestCacheWithRedis:
    """Test cache operations with a real Redis connection.

    These tests require Redis running at localhost:6379.
    They are skipped if Redis is unavailable.
    """

    @pytest.mark.asyncio
    async def test_connect_success(self, cache_with_redis):
        """connect() establishes connection when Redis is up."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")
        assert cache_with_redis.is_connected is True

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_with_redis):
        """set + get roundtrip works."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")

        await cache_with_redis.set("test:phase3e", {"hello": "world"}, ttl_seconds=10)
        result = await cache_with_redis.get("test:phase3e")
        assert result == {"hello": "world"}

        # Cleanup
        await cache_with_redis.delete("test:phase3e")

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache_with_redis):
        """get() returns None for non-existent key."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")

        result = await cache_with_redis.get("test:nonexistent_key_12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, cache_with_redis):
        """delete() removes a key."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")

        await cache_with_redis.set("test:to_delete", {"temp": True}, ttl_seconds=10)
        await cache_with_redis.delete("test:to_delete")
        result = await cache_with_redis.get("test:to_delete")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_with_redis):
        """invalidate_pattern() deletes matching keys."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")

        # Set multiple keys
        await cache_with_redis.set("test:pattern:a", "1", ttl_seconds=10)
        await cache_with_redis.set("test:pattern:b", "2", ttl_seconds=10)
        await cache_with_redis.set("test:other:c", "3", ttl_seconds=10)

        # Invalidate pattern
        deleted = await cache_with_redis.invalidate_pattern("test:pattern:*")
        assert deleted >= 2

        # Verify
        assert await cache_with_redis.get("test:pattern:a") is None
        assert await cache_with_redis.get("test:pattern:b") is None

        # Cleanup
        await cache_with_redis.delete("test:other:c")

    @pytest.mark.asyncio
    async def test_complex_json_roundtrip(self, cache_with_redis):
        """Cache handles complex nested JSON."""
        if not cache_with_redis.is_connected:
            pytest.skip("Redis not available")

        complex_data = {
            "summary": [{"name": "Revenue", "amount": 1234.56}],
            "nested": {"a": {"b": [1, 2, 3]}},
            "count": 42,
        }
        await cache_with_redis.set("test:complex", complex_data, ttl_seconds=10)
        result = await cache_with_redis.get("test:complex")
        assert result["count"] == 42
        assert result["summary"][0]["amount"] == 1234.56

        await cache_with_redis.delete("test:complex")
