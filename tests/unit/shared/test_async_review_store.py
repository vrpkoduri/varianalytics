"""Tests for AsyncReviewStore dual-write pattern."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from shared.data.review_store import ReviewStore
from shared.data.async_review_store import AsyncReviewStore


@pytest.fixture
def inner_store():
    """Create a ReviewStore with data loaded."""
    return ReviewStore()


@pytest.fixture
def async_store(inner_store):
    """AsyncReviewStore without database (memory-only mode)."""
    return AsyncReviewStore(inner_store, session_factory=None)


class TestAsyncReviewStoreReads:
    """Verify read methods delegate to inner store."""

    def test_get_review_queue_delegates(self, async_store, inner_store):
        result = async_store.get_review_queue()
        expected = inner_store.get_review_queue()
        assert result == expected

    def test_get_review_stats_delegates(self, async_store, inner_store):
        result = async_store.get_review_stats()
        expected = inner_store.get_review_stats()
        assert result == expected

    def test_get_approval_queue_delegates(self, async_store, inner_store):
        result = async_store.get_approval_queue()
        expected = inner_store.get_approval_queue()
        assert result == expected


class TestAsyncReviewStoreWrites:
    """Verify write methods update in-memory and handle DB gracefully."""

    @pytest.mark.asyncio
    async def test_submit_action_updates_memory(self, async_store):
        """In-memory update works even without DB."""
        # Get a variance ID
        queue = async_store.get_review_queue()
        items = queue.get("items", [])
        if not items:
            pytest.skip("No review items")
        vid = items[0].get("variance_id", "")

        result = await async_store.submit_review_action(
            variance_id=vid,
            action="approve",
        )
        assert result.get("new_status") == "ANALYST_REVIEWED"

    @pytest.mark.asyncio
    async def test_submit_action_without_db_no_error(self, async_store):
        """session_factory=None should not raise."""
        queue = async_store.get_review_queue()
        items = queue.get("items", [])
        if not items:
            pytest.skip("No items")
        vid = items[0].get("variance_id", "")

        # Should not raise even without DB
        result = await async_store.submit_review_action(
            variance_id=vid,
            action="edit",
            edited_narrative="Test narrative",
            hypothesis_feedback="thumbs_up",
        )
        assert "new_status" in result
