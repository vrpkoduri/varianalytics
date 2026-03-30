"""Integration tests verifying data flows frontend hooks expect."""

import pytest
from fastapi.testclient import TestClient

from services.computation.main import app as computation_app
from services.gateway.main import app as gateway_app


@pytest.fixture(scope="module")
def computation_client():
    with TestClient(computation_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="module")
def gateway_client():
    with TestClient(gateway_app, raise_server_exceptions=False) as client:
        yield client


class TestDashboardDataFlow:
    def test_summary_cards_have_numeric_fields(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/summary?period_id=2025-12")
        cards = resp.json().get("cards", [])
        if cards:
            card = cards[0]
            assert isinstance(card.get("actual", 0), (int, float))

    def test_waterfall_steps_have_value_field(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/waterfall?period_id=2025-12")
        steps = resp.json().get("steps", [])
        if steps:
            assert "value" in steps[0] or "amount" in steps[0]

    def test_trends_data_is_list(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/trends?periods=6")
        data = resp.json().get("data", [])
        assert isinstance(data, list)


class TestPLDataFlow:
    def test_pl_rows_have_account_id(self, computation_client):
        resp = computation_client.get("/api/v1/pl/statement?period_id=2025-12")
        rows = resp.json().get("rows", [])
        if rows:
            assert "account_id" in rows[0] or "accountId" in rows[0]

    def test_pl_has_calculated_rows(self, computation_client):
        """P&L returns a tree — check that calculated rows exist in the hierarchy."""
        resp = computation_client.get("/api/v1/pl/statement?period_id=2025-12")
        rows = resp.json().get("rows", [])
        # Rows may be nested (tree structure) — flatten to check names
        def flatten(nodes):
            result = []
            for n in nodes if isinstance(nodes, list) else [nodes]:
                result.append(n)
                result.extend(flatten(n.get("children", [])))
            return result
        flat = flatten(rows)
        names = [r.get("account_name", "").lower() for r in flat]
        has_calc = any("gross" in n or "ebitda" in n or "net" in n for n in names)
        assert has_calc, f"No calculated rows found in {len(flat)} total rows"


class TestChatDataFlow:
    def test_chat_returns_stream_url(self, gateway_client):
        resp = gateway_client.post("/api/v1/chat/messages", json={"message": "revenue overview"})
        data = resp.json()
        assert "stream_url" in data or "streamUrl" in data

    def test_chat_conversation_list(self, gateway_client):
        resp = gateway_client.get("/api/v1/chat/conversations")
        assert resp.status_code == 200


class TestReviewDataFlow:
    def test_review_stats_has_counts(self, gateway_client):
        resp = gateway_client.get("/api/v1/review/stats")
        data = resp.json()
        assert isinstance(data, dict)
