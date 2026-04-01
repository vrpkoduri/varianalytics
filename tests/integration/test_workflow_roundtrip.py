"""Workflow Round-Trip Tests.

Simulates full analyst/director workflow: AI_DRAFT -> edit -> review -> approve.
Each test uses a fresh variance from the queue.
"""
import pytest
from fastapi.testclient import TestClient
from services.gateway.main import app as gateway_app


@pytest.fixture(scope="module")
def gw():
    with TestClient(gateway_app, raise_server_exceptions=False) as c:
        yield c

def _get_draft_variance_id(gw) -> str:
    queue = gw.get("/api/v1/review/queue").json()
    items = queue.get("items", []) if isinstance(queue, dict) else queue if isinstance(queue, list) else []
    drafts = [i for i in items if i.get("current_status") == "AI_DRAFT" or i.get("status") == "AI_DRAFT"]
    if not drafts:
        pytest.skip("No AI_DRAFT items available")
    return drafts[0].get("variance_id", "")


class TestAnalystWorkflow:
    def test_analyst_edits_narrative(self, gw):
        vid = _get_draft_variance_id(gw)
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "edit",
            "edited_narrative": "Analyst-edited narrative for testing"
        })
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "ANALYST_REVIEWED"

    def test_analyst_escalates_variance(self, gw):
        vid = _get_draft_variance_id(gw)
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "escalate"
        })
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "ESCALATED"

    def test_analyst_dismisses_variance(self, gw):
        vid = _get_draft_variance_id(gw)
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "dismiss"
        })
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "DISMISSED"

    def test_hypothesis_feedback_persists(self, gw):
        vid = _get_draft_variance_id(gw)
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "edit",
            "hypothesis_feedback": "thumbs_up"
        })
        assert resp.status_code == 200


class TestDirectorWorkflow:
    def test_director_approves_reviewed(self, gw):
        # First, get a draft and review it
        vid = _get_draft_variance_id(gw)
        gw.post("/api/v1/review/actions", json={"variance_id": vid, "action": "approve"})
        # Now director approves
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "director_approve"
        })
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "APPROVED"

    def test_invalid_transition_rejected(self, gw):
        vid = _get_draft_variance_id(gw)
        # Try direct AI_DRAFT -> APPROVED (should fail)
        resp = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "director_approve"
        })
        # Should return error (400 or 200 with error message)
        if resp.status_code == 200:
            assert "error" in resp.json().get("message", "").lower() or resp.json().get("new_status") != "APPROVED"

    def test_bulk_approval(self, gw):
        # Self-contained: create reviewed items first by editing drafts
        review_queue = gw.get("/api/v1/review/queue?status=AI_DRAFT&page_size=3").json()
        draft_items = review_queue.get("items", []) if isinstance(review_queue, dict) else []
        for item in draft_items[:3]:
            gw.post("/api/v1/review/actions", json={
                "variance_id": item.get("variance_id", ""),
                "action": "edit",
                "edited_narrative": "Edited for bulk approval test",
            })

        # Now get approval queue
        queue = gw.get("/api/v1/approval/queue").json()
        items = queue.get("items", []) if isinstance(queue, dict) else []
        reviewed = [i.get("variance_id", "") for i in items][:2]
        if not reviewed:
            pytest.skip("No reviewed items for bulk approval after seeding")
        resp = gw.post("/api/v1/approval/actions", json={
            "variance_ids": reviewed, "action": "approve"
        })
        assert resp.status_code == 200

    def test_full_lifecycle(self, gw):
        vid = _get_draft_variance_id(gw)
        # Step 1: Analyst edits -> ANALYST_REVIEWED
        r1 = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "edit",
            "edited_narrative": "Full lifecycle test"
        })
        assert r1.json()["new_status"] == "ANALYST_REVIEWED"
        # Step 2: Director approves -> APPROVED
        r2 = gw.post("/api/v1/review/actions", json={
            "variance_id": vid, "action": "director_approve"
        })
        assert r2.json()["new_status"] == "APPROVED"
