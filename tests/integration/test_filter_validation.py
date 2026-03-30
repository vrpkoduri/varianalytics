"""Integration tests validating all filter combinations work end-to-end."""
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

class TestWaterfallFilters:
    def test_waterfall_accepts_view_id(self, comp):
        resp = comp.get("/api/v1/dashboard/waterfall?period_id=2026-06&view_id=QTD")
        assert resp.status_code == 200
        assert "steps" in resp.json()

    def test_waterfall_with_bu_id(self, comp):
        resp = comp.get("/api/v1/dashboard/waterfall?period_id=2026-06&bu_id=marsh")
        assert resp.status_code == 200

class TestHeatmapFilters:
    def test_heatmap_accepts_bu_id(self, comp):
        resp = comp.get("/api/v1/dashboard/heatmap?period_id=2026-06&bu_id=marsh")
        assert resp.status_code == 200

    def test_heatmap_accepts_view_id(self, comp):
        resp = comp.get("/api/v1/dashboard/heatmap?period_id=2026-06&view_id=QTD")
        assert resp.status_code == 200

class TestTrendsFilters:
    def test_trends_accepts_bu_id(self, comp):
        resp = comp.get("/api/v1/dashboard/trends?bu_id=marsh&view_id=MTD")
        assert resp.status_code == 200

    def test_trends_accepts_view_id(self, comp):
        resp = comp.get("/api/v1/dashboard/trends?view_id=QTD")
        assert resp.status_code == 200

class TestCrossFilterCombinations:
    def test_summary_bu_plus_view(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=2026-06&bu_id=marsh&view_id=QTD&base_id=BUDGET")
        assert resp.status_code == 200
        cards = resp.json().get("cards", [])
        assert len(cards) > 0

    def test_variances_all_filters(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&bu_id=marsh&view_id=MTD&base_id=BUDGET&page_size=5")
        assert resp.status_code == 200
