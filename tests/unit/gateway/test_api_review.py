"""Unit tests for gateway review workflow endpoints."""

import pytest
from fastapi.testclient import TestClient

from shared.data.review_store import ReviewStore
from shared.data.service import DataService


@pytest.fixture(scope="module")
def client():
    """Create test client with ReviewStore initialized."""
    from services.gateway.main import app

    app.state.data_service = DataService()
    app.state.review_store = ReviewStore()

    with TestClient(app) as c:
        yield c


@pytest.mark.unit
class TestReviewQueue:
    """Test review queue endpoints."""

    def test_get_review_queue_returns_items(self, client):
        """GET /api/v1/review/queue returns paginated items."""
        resp = client.get("/api/v1/review/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0

    def test_get_review_queue_filter_by_status(self, client):
        """GET /api/v1/review/queue?status=AI_DRAFT filters correctly."""
        resp = client.get("/api/v1/review/queue?status=AI_DRAFT")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["current_status"] == "AI_DRAFT"

    def test_get_review_queue_pagination(self, client):
        """Review queue supports pagination."""
        resp = client.get("/api/v1/review/queue?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_get_review_stats(self, client):
        """GET /api/v1/review/stats returns statistics."""
        resp = client.get("/api/v1/review/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_pending" in data
        assert "ai_draft" in data
        assert data["ai_draft"] > 0


@pytest.mark.unit
class TestReviewActions:
    """Test review action endpoints."""

    def test_submit_review_approve(self, client):
        """POST /api/v1/review/actions with approve transitions to ANALYST_REVIEWED."""
        # Get a variance_id from the queue
        queue_resp = client.get("/api/v1/review/queue?status=AI_DRAFT&page_size=1")
        items = queue_resp.json()["items"]
        if not items:
            pytest.skip("No AI_DRAFT items in queue")

        vid = items[0]["variance_id"]
        resp = client.post("/api/v1/review/actions", json={
            "variance_id": vid,
            "action": "approve",
            "comment": "Looks good",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "ANALYST_REVIEWED"

    def test_submit_review_escalate(self, client):
        """POST /api/v1/review/actions with escalate transitions to ESCALATED."""
        queue_resp = client.get("/api/v1/review/queue?status=AI_DRAFT&page_size=1")
        items = queue_resp.json()["items"]
        if not items:
            pytest.skip("No AI_DRAFT items")

        vid = items[0]["variance_id"]
        resp = client.post("/api/v1/review/actions", json={
            "variance_id": vid,
            "action": "escalate",
        })
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "ESCALATED"

    def test_submit_invalid_action_returns_400(self, client):
        """POST /api/v1/review/actions with bad variance_id returns 400."""
        resp = client.post("/api/v1/review/actions", json={
            "variance_id": "nonexistent_id",
            "action": "approve",
        })
        assert resp.status_code == 400

    def test_submit_invalid_transition_returns_400(self, client):
        """Cannot approve an already-approved variance."""
        # Approve one first via the store directly
        store = ReviewStore()
        queue = store.get_review_queue(status_filter="AI_DRAFT", page_size=1)
        if not queue["items"]:
            pytest.skip("No items")
        vid = queue["items"][0]["variance_id"]
        store.submit_review_action(vid, "approve")

        # Try to approve again (ANALYST_REVIEWED → ANALYST_REVIEWED is not valid)
        # Actually ANALYST_REVIEWED can go to APPROVED, AI_DRAFT, or ESCALATED
        # Let's try dismissing an ANALYST_REVIEWED item which is not a valid transition
        resp = client.post("/api/v1/review/actions", json={
            "variance_id": vid,
            "action": "dismiss",
        })
        # dismiss maps to DISMISSED which is not valid from ANALYST_REVIEWED
        assert resp.status_code == 400
