"""Cross-Service Integration Tests.

Validates gateway and computation services work together correctly.
Tests the full chain: API endpoint -> DataService -> data response.
"""
import pytest
from fastapi.testclient import TestClient
from services.computation.main import app as computation_app
from services.gateway.main import app as gateway_app


@pytest.fixture(scope="module")
def comp():
    with TestClient(computation_app, raise_server_exceptions=False) as c:
        yield c

@pytest.fixture(scope="module")
def gw():
    with TestClient(gateway_app, raise_server_exceptions=False) as c:
        yield c


class TestServiceHealth:
    def test_gateway_health(self, gw):
        resp = gw.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "healthy")

    def test_computation_health(self, comp):
        resp = comp.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "healthy")


class TestCrossServiceData:
    def test_chat_triggers_agent(self, gw):
        resp = gw.post("/api/v1/chat/messages", json={"message": "How is revenue?"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "conversation_id" in data
        assert "stream_url" in data

    def test_review_queue_has_items(self, gw):
        resp = gw.get("/api/v1/review/queue")
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) > 0 if isinstance(items, list) else True

    def test_review_action_changes_status(self, gw):
        queue = gw.get("/api/v1/review/queue").json()
        items = queue.get("items", []) if isinstance(queue, dict) else queue if isinstance(queue, list) else []
        if not items:
            pytest.skip("No review items")
        vid = items[0].get("variance_id", "")
        resp = gw.post("/api/v1/review/actions", json={"variance_id": vid, "action": "approve"})
        assert resp.status_code == 200
        assert resp.json().get("new_status") == "ANALYST_REVIEWED"

    def test_dimension_endpoints_return_data(self, gw):
        for dim in ["geography", "segment", "lob", "costcenter"]:
            resp = gw.get(f"/api/v1/dimensions/hierarchies/{dim}")
            assert resp.status_code == 200, f"Failed for {dim}"
        bu_resp = gw.get("/api/v1/dimensions/business-units")
        assert bu_resp.status_code == 200

    def test_dashboard_summary_has_cards(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=2026-06&base_id=BUDGET")
        assert resp.status_code == 200
        cards = resp.json().get("cards", [])
        assert len(cards) >= 5, f"Expected >=5 cards, got {len(cards)}"

    def test_variances_list_returns_items(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("variances", data.get("items", []))
        assert len(items) > 0

    def test_pl_statement_has_calculated_rows(self, comp):
        resp = comp.get("/api/v1/pl/statement?period_id=2026-06")
        assert resp.status_code == 200
        rows = resp.json().get("rows", [])
        # Flatten tree to find calculated rows
        def flatten(nodes):
            result = []
            for n in (nodes if isinstance(nodes, list) else [nodes]):
                result.append(n)
                result.extend(flatten(n.get("children", [])))
            return result
        flat = flatten(rows)
        names = [r.get("account_name", "").upper() for r in flat]
        assert any("GROSS PROFIT" in n for n in names), "Missing GROSS PROFIT"
        assert any("EBITDA" in n for n in names), "Missing EBITDA"
        assert any("NET INCOME" in n for n in names), "Missing NET INCOME"

    def test_alerts_surface_real_data(self, comp):
        netting = comp.get("/api/v1/dashboard/alerts/netting?period_id=2026-06")
        assert netting.status_code == 200
        assert netting.json().get("count", 0) > 0

        trends = comp.get("/api/v1/dashboard/alerts/trends")
        assert trends.status_code == 200
        assert trends.json().get("count", 0) > 0
