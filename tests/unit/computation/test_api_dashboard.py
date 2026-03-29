"""Tests for the Computation Service dashboard API endpoints.

Uses FastAPI TestClient with a real DataService backed by parquet data.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.computation.main import app
from shared.data.service import DataService


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient with DataService wired into app state."""
    DataService.reset_instance()
    app.state.data_service = DataService(data_dir="data/output")
    return TestClient(app)


@pytest.fixture(scope="module")
def latest_period(client: TestClient) -> str:
    """Return a period_id that has variance data."""
    ds: DataService = app.state.data_service
    vm = ds._table("fact_variance_material")
    if vm.empty:
        periods = ds.get_periods()
        return periods[-1]["period_id"]
    return vm["period_id"].max()


# ------------------------------------------------------------------
# GET /api/v1/dashboard/summary
# ------------------------------------------------------------------


@pytest.mark.unit
class TestSummaryEndpoint:
    def test_summary_endpoint_returns_cards(self, client: TestClient, latest_period: str) -> None:
        resp = client.get("/api/v1/dashboard/summary", params={"period_id": latest_period})
        assert resp.status_code == 200
        data = resp.json()
        assert "cards" in data
        assert len(data["cards"]) == 7
        assert data["period_id"] == latest_period
        assert data["view_id"] == "MTD"
        assert data["base_id"] == "BUDGET"

    def test_summary_endpoint_filter_by_bu(self, client: TestClient, latest_period: str) -> None:
        resp_all = client.get("/api/v1/dashboard/summary", params={"period_id": latest_period})
        resp_bu = client.get(
            "/api/v1/dashboard/summary",
            params={"period_id": latest_period, "bu_id": "marsh"},
        )
        assert resp_all.status_code == 200
        assert resp_bu.status_code == 200
        all_cards = resp_all.json()["cards"]
        bu_cards = resp_bu.json()["cards"]
        assert len(bu_cards) == 7
        # BU-filtered revenue should be smaller
        all_rev = next(c for c in all_cards if c["metric_name"] == "Total Revenue")
        bu_rev = next(c for c in bu_cards if c["metric_name"] == "Total Revenue")
        assert abs(bu_rev["actual"]) < abs(all_rev["actual"])

    def test_summary_endpoint_missing_period(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/summary", params={"period_id": "9999-12"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cards"] == []


# ------------------------------------------------------------------
# GET /api/v1/dashboard/waterfall
# ------------------------------------------------------------------


@pytest.mark.unit
class TestWaterfallEndpoint:
    def test_waterfall_endpoint_returns_steps(self, client: TestClient, latest_period: str) -> None:
        resp = client.get("/api/v1/dashboard/waterfall", params={"period_id": latest_period})
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        steps = data["steps"]
        assert len(steps) >= 3
        assert steps[0]["name"] == "Budget"
        assert steps[0]["is_total"] is True
        assert steps[-1]["name"] == "Actual"
        assert steps[-1]["is_total"] is True


# ------------------------------------------------------------------
# GET /api/v1/dashboard/heatmap
# ------------------------------------------------------------------


@pytest.mark.unit
class TestHeatmapEndpoint:
    def test_heatmap_endpoint_returns_grid(self, client: TestClient, latest_period: str) -> None:
        resp = client.get("/api/v1/dashboard/heatmap", params={"period_id": latest_period})
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert "columns" in data
        assert "cells" in data
        assert len(data["columns"]) == 5  # 5 BUs
        assert len(data["cells"]) == len(data["rows"])


# ------------------------------------------------------------------
# GET /api/v1/dashboard/trends
# ------------------------------------------------------------------


@pytest.mark.unit
class TestTrendsEndpoint:
    def test_trends_endpoint_returns_data(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/trends", params={"periods": 6})
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["account_id"] == "acct_gross_revenue"
        assert data["periods"] == 6
        assert len(data["data"]) <= 6
        assert len(data["data"]) > 0
