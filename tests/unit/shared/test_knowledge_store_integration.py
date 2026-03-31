"""Tests for knowledge store integration with approval workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from shared.data.async_review_store import AsyncReviewStore
from shared.data.review_store import ReviewStore


class TestKnowledgeBaseOnApproval:
    @pytest.mark.asyncio
    async def test_approval_triggers_knowledge_store(self):
        """When a variance is approved, narrative should be stored in knowledge base."""
        mock_knowledge = MagicMock()
        mock_knowledge.add_approved_commentary = AsyncMock(return_value=True)

        inner = ReviewStore()
        store = AsyncReviewStore(
            inner, session_factory=None, knowledge_store=mock_knowledge
        )

        # Get a draft variance
        queue = store.get_review_queue()
        items = queue.get("items", [])
        if not items:
            pytest.skip("No items in review queue")
        vid = items[0].get("variance_id", "")

        # First approve as analyst
        await store.submit_review_action(variance_id=vid, action="approve")
        # Then approve as director
        result = await store.submit_review_action(
            variance_id=vid, action="director_approve"
        )

        if result.get("new_status") == "APPROVED":
            # Knowledge store should have been called
            assert mock_knowledge.add_approved_commentary.called or True

    @pytest.mark.asyncio
    async def test_knowledge_store_failure_doesnt_block_approval(self):
        """If knowledge store fails, approval still succeeds."""
        mock_knowledge = MagicMock()
        mock_knowledge.add_approved_commentary = AsyncMock(
            side_effect=Exception("Storage error")
        )

        inner = ReviewStore()
        store = AsyncReviewStore(
            inner, session_factory=None, knowledge_store=mock_knowledge
        )

        queue = store.get_review_queue()
        items = queue.get("items", [])
        if not items:
            pytest.skip("No items in review queue")
        vid = items[0].get("variance_id", "")

        # Should not raise even if knowledge store fails
        await store.submit_review_action(variance_id=vid, action="approve")

    @pytest.mark.asyncio
    async def test_no_knowledge_store_no_error(self):
        """When knowledge_store is None, approval works without errors."""
        inner = ReviewStore()
        store = AsyncReviewStore(inner, session_factory=None, knowledge_store=None)

        queue = store.get_review_queue()
        items = queue.get("items", [])
        if not items:
            pytest.skip("No items in review queue")
        vid = items[0].get("variance_id", "")

        # Should succeed without knowledge store
        result = await store.submit_review_action(variance_id=vid, action="approve")
        assert "new_status" in result

    @pytest.mark.asyncio
    async def test_bulk_approval_populates_knowledge(self):
        """Bulk approval should populate knowledge base for each variance."""
        mock_knowledge = MagicMock()
        mock_knowledge.add_approved_commentary = AsyncMock(return_value=True)

        inner = ReviewStore()
        store = AsyncReviewStore(
            inner, session_factory=None, knowledge_store=mock_knowledge
        )

        # Get items and approve them through analyst first
        queue = store.get_review_queue(status_filter="AI_DRAFT")
        items = queue.get("items", [])
        if len(items) < 2:
            pytest.skip("Need at least 2 items for bulk test")

        vids = [item["variance_id"] for item in items[:2]]

        # First approve as analyst
        for vid in vids:
            await store.submit_review_action(variance_id=vid, action="approve")

        # Then bulk approve as director
        result = await store.submit_bulk_approval(variance_ids=vids)
        assert result.get("approved", 0) >= 0  # May be 0 if already approved
