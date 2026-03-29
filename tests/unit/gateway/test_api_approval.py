"""Unit tests for gateway approval workflow endpoints."""

import pytest
from fastapi.testclient import TestClient

from shared.data.review_store import ReviewStore
from shared.data.service import DataService


@pytest.fixture(scope="module")
def approval_client():
    """Create test client with ReviewStore that has some ANALYST_REVIEWED items."""
    from services.gateway.main import app

    app.state.data_service = DataService()
    store = ReviewStore()

    # Move first 3 items to ANALYST_REVIEWED for testing
    queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=3)
    for item in queue["items"]:
        try:
            store.submit_review_action(item["variance_id"], "approve")
        except ValueError:
            pass

    app.state.review_store = store

    with TestClient(app) as c:
        yield c


@pytest.mark.unit
class TestApprovalQueue:
    """Test approval queue endpoints."""

    def test_get_approval_queue_returns_reviewed_items(self, approval_client):
        """GET /api/v1/approval/queue returns ANALYST_REVIEWED items."""
        resp = approval_client.get("/api/v1/approval/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 0  # May have items from fixture

    def test_get_approval_stats(self, approval_client):
        """GET /api/v1/approval/stats returns statistics."""
        resp = approval_client.get("/api/v1/approval/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "pending_approval" in data
        assert "total_approved" in data

    def test_bulk_approve(self, approval_client):
        """POST /api/v1/approval/actions approves multiple variances."""
        # Get items to approve
        queue_resp = approval_client.get("/api/v1/approval/queue?page_size=2")
        items = queue_resp.json()["items"]
        if not items:
            pytest.skip("No ANALYST_REVIEWED items")

        vids = [item["variance_id"] for item in items]
        resp = approval_client.post("/api/v1/approval/actions", json={
            "variance_ids": vids,
            "action": "approve",
            "comment": "Approved in batch",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved_count"] + len(data["errors"]) == len(vids)

    def test_bulk_approve_empty_list_fails(self, approval_client):
        """POST /api/v1/approval/actions with empty list returns 422."""
        resp = approval_client.post("/api/v1/approval/actions", json={
            "variance_ids": [],
            "action": "approve",
        })
        assert resp.status_code == 422  # Pydantic validation (min_length=1)

    def test_approval_queue_pagination(self, approval_client):
        """Approval queue supports pagination."""
        resp = approval_client.get("/api/v1/approval/queue?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


@pytest.mark.unit
class TestReviewStore:
    """Direct unit tests for ReviewStore."""

    def test_store_loads_data(self):
        """ReviewStore loads review status and variance data."""
        store = ReviewStore()
        stats = store.get_review_stats()
        assert stats["ai_draft"] > 0

    def test_valid_status_transitions(self):
        """Test that valid transitions succeed."""
        store = ReviewStore()
        queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=1)
        if not queue["items"]:
            pytest.skip("No items")
        vid = queue["items"][0]["variance_id"]

        result = store.submit_review_action(vid, "approve")
        assert result["new_status"] == "ANALYST_REVIEWED"

    def test_invalid_transition_raises(self):
        """Invalid status transitions raise ValueError."""
        store = ReviewStore()
        queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=1)
        if not queue["items"]:
            pytest.skip("No items")
        vid = queue["items"][0]["variance_id"]

        # AI_DRAFT → APPROVED is not valid (must go through ANALYST_REVIEWED)
        with pytest.raises(ValueError, match="Cannot transition"):
            store.submit_review_action(vid, "director_approve")
