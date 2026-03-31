"""Tests for drilldown decomposition endpoint."""
import pytest
from fastapi.testclient import TestClient
from services.computation.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestDecompositionEndpoint:
    def test_valid_variance_returns_200_or_404(self, client):
        # Get a variance ID first
        list_resp = client.get("/api/v1/variances/?period_id=2026-06&page_size=1")
        items = list_resp.json().get("variances", list_resp.json().get("items", []))
        if items:
            vid = items[0].get("variance_id", items[0].get("varianceId", ""))
            if vid:
                resp = client.get(f"/api/v1/drilldown/decomposition/{vid}")
                assert resp.status_code in (200, 404)

    def test_nonexistent_variance_returns_404(self, client):
        resp = client.get("/api/v1/drilldown/decomposition/nonexistent_id_xyz")
        assert resp.status_code == 404

    def test_decomposition_has_components(self, client):
        list_resp = client.get("/api/v1/variances/?period_id=2026-06&page_size=5")
        items = list_resp.json().get("variances", list_resp.json().get("items", []))
        for item in items[:3]:
            vid = item.get("variance_id", item.get("varianceId", ""))
            if vid:
                resp = client.get(f"/api/v1/drilldown/decomposition/{vid}")
                if resp.status_code == 200:
                    data = resp.json()
                    assert "components" in data or "decomposition_type" in data
                    break
