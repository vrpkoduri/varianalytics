"""Tests for the Computation Service variances API endpoints.

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
# GET /api/v1/variances/
# ------------------------------------------------------------------


@pytest.mark.unit
class TestVarianceList:
    def test_variance_list_returns_paginated(self, client: TestClient, latest_period: str) -> None:
        resp = client.get(
            "/api/v1/variances/",
            params={"period_id": latest_period, "page": 1, "page_size": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5
        assert data["total_count"] > 0

    def test_variance_list_filter_by_category(self, client: TestClient, latest_period: str) -> None:
        resp = client.get(
            "/api/v1/variances/",
            params={"period_id": latest_period, "pl_category": "Revenue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["pl_category"] == "Revenue"


# ------------------------------------------------------------------
# GET /api/v1/variances/{variance_id}
# ------------------------------------------------------------------


@pytest.mark.unit
class TestVarianceDetail:
    def test_variance_detail_returns_enriched(self, client: TestClient, latest_period: str) -> None:
        # First get a valid variance_id
        list_resp = client.get(
            "/api/v1/variances/",
            params={"period_id": latest_period, "page_size": 1},
        )
        items = list_resp.json()["items"]
        assert len(items) > 0
        vid = items[0]["variance_id"]

        resp = client.get(f"/api/v1/variances/{vid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["variance_id"] == vid
        assert "account_id" in data
        assert "account_name" in data
        assert "actual_amount" in data
        assert "comparator_amount" in data
        assert "variance_amount" in data
        assert "narratives" in data
        assert "decomposition" in data
        assert "correlations" in data

    def test_variance_detail_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/variances/nonexistent-variance-id")
        assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /api/v1/variances/by-account/{account_id}
# ------------------------------------------------------------------


@pytest.mark.unit
class TestVarianceByAccount:
    def test_variance_by_account_returns_data(self, client: TestClient, latest_period: str) -> None:
        resp = client.get(
            "/api/v1/variances/by-account/acct_revenue",
            params={"period_id": latest_period},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_id"] == "acct_revenue"
        assert "account_name" in data
        assert "actual" in data
        assert "comparator" in data
        assert "variance_amount" in data
        assert "child_variances" in data
        assert "decomposition" in data
