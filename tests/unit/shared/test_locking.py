"""Tests for soft edit locking on review store."""

import pytest
from shared.data.review_store import ReviewStore


@pytest.fixture
def store() -> ReviewStore:
    return ReviewStore()


@pytest.fixture
def first_variance_id(store: ReviewStore) -> str:
    queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=1)
    if not queue["items"]:
        pytest.skip("No AI_DRAFT items")
    return queue["items"][0]["variance_id"]


class TestSoftLocking:
    def test_lock_acquired_successfully(self, store, first_variance_id):
        result = store.acquire_lock(first_variance_id, "analyst-001")
        assert result["locked"] is True
        assert result["locked_by"] == "analyst-001"

    def test_lock_prevents_other_user_edit(self, store, first_variance_id):
        store.acquire_lock(first_variance_id, "analyst-001")
        result = store.acquire_lock(first_variance_id, "analyst-002")
        assert result["locked"] is False
        assert result["locked_by"] == "analyst-001"

    def test_same_user_can_relock(self, store, first_variance_id):
        store.acquire_lock(first_variance_id, "analyst-001")
        result = store.acquire_lock(first_variance_id, "analyst-001")
        assert result["locked"] is True

    def test_lock_released_by_owner(self, store, first_variance_id):
        store.acquire_lock(first_variance_id, "analyst-001")
        released = store.release_lock(first_variance_id, "analyst-001")
        assert released is True
        status = store.get_lock_status(first_variance_id)
        assert status["locked"] is False

    def test_lock_status_check(self, store, first_variance_id):
        status = store.get_lock_status(first_variance_id)
        assert "locked" in status


class TestReviewActionWithUser:
    def test_submit_action_with_user_id(self, store, first_variance_id):
        result = store.submit_review_action(
            first_variance_id, "edit",
            edited_narrative="Test edit",
            user_id="analyst-001",
        )
        assert result["new_status"] == "ANALYST_REVIEWED"

    def test_version_count_increments(self, store, first_variance_id):
        store.submit_review_action(first_variance_id, "edit", edited_narrative="v1", user_id="a1")
        mask = store._review_status["variance_id"] == first_variance_id
        vc = store._review_status.loc[mask, "version_count"].iloc[0] if "version_count" in store._review_status.columns else 0
        assert int(vc) >= 1

    def test_change_reason_accepted(self, store, first_variance_id):
        # Should not raise
        result = store.submit_review_action(
            first_variance_id, "edit",
            edited_narrative="Corrected amount",
            user_id="analyst-001",
            change_reason="factual_correction",
        )
        assert result["new_status"] == "ANALYST_REVIEWED"
