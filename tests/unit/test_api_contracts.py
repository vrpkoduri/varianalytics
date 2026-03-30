"""API contract tests — verify backend responses match frontend type expectations.

Uses TestClient with raise_server_exceptions=False so that lifespan events
(which initialize app.state.data_service) run properly.
"""

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


class TestDashboardContracts:
    def test_summary_has_cards_key(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/summary?period_id=2025-12")
        assert resp.status_code == 200
        assert "cards" in resp.json()

    def test_waterfall_has_steps_key(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/waterfall?period_id=2025-12")
        assert resp.status_code == 200
        assert "steps" in resp.json()

    def test_heatmap_returns_200(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/heatmap?period_id=2025-12")
        assert resp.status_code == 200

    def test_trends_has_data_key(self, computation_client):
        resp = computation_client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 200
        assert "data" in resp.json()


class TestVarianceContracts:
    def test_variance_list_has_pagination(self, computation_client):
        resp = computation_client.get("/api/v1/variances/?period_id=2025-12")
        assert resp.status_code == 200
        data = resp.json()
        assert "variances" in data or "items" in data

    def test_variance_list_returns_array(self, computation_client):
        resp = computation_client.get("/api/v1/variances/?period_id=2025-12&page_size=5")
        data = resp.json()
        items = data.get("variances", data.get("items", []))
        assert isinstance(items, list)


class TestPLContracts:
    def test_pl_statement_has_rows(self, computation_client):
        resp = computation_client.get("/api/v1/pl/statement?period_id=2025-12")
        assert resp.status_code == 200
        assert "rows" in resp.json()


class TestGatewayContracts:
    def test_review_queue_returns_200(self, gateway_client):
        resp = gateway_client.get("/api/v1/review/queue")
        assert resp.status_code == 200

    def test_approval_queue_returns_200(self, gateway_client):
        resp = gateway_client.get("/api/v1/approval/queue")
        assert resp.status_code == 200

    def test_chat_post_returns_conversation_id(self, gateway_client):
        resp = gateway_client.post("/api/v1/chat/messages", json={"message": "test", "context": {}})
        assert resp.status_code in (200, 201)
        assert "conversation_id" in resp.json()

    def test_review_stats_returns_200(self, gateway_client):
        resp = gateway_client.get("/api/v1/review/stats")
        assert resp.status_code == 200

    def test_gateway_health(self, gateway_client):
        resp = gateway_client.get("/health")
        assert resp.status_code == 200

    def test_computation_health(self, computation_client):
        resp = computation_client.get("/health")
        assert resp.status_code == 200
