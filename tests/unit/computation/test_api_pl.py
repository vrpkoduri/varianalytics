"""Tests for the Computation Service P&L API endpoints.

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
# GET /api/v1/pl/statement
# ------------------------------------------------------------------


@pytest.mark.unit
class TestPLStatement:
    def test_pl_statement_returns_tree(self, client: TestClient, latest_period: str) -> None:
        resp = client.get("/api/v1/pl/statement", params={"period_id": latest_period})
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert data["period_id"] == latest_period
        rows = data["rows"]
        assert len(rows) == 1
        root = rows[0]
        assert root["account_id"] == "acct_total_pl"
        assert root["depth"] == 0
        assert len(root["children"]) > 0

    def test_pl_statement_has_calculated_rows(self, client: TestClient, latest_period: str) -> None:
        resp = client.get("/api/v1/pl/statement", params={"period_id": latest_period})
        data = resp.json()
        rows = data["rows"]
        root = rows[0]

        def _collect_ids(node: dict) -> list[str]:
            ids = [node["account_id"]]
            for child in node.get("children", []):
                ids.extend(_collect_ids(child))
            return ids

        all_ids = _collect_ids(root)
        for calc_id in ["acct_gross_profit", "acct_ebitda", "acct_net_income"]:
            assert calc_id in all_ids, f"{calc_id} missing from P&L tree"


# ------------------------------------------------------------------
# GET /api/v1/pl/account/{account_id}/detail
# ------------------------------------------------------------------


@pytest.mark.unit
class TestAccountDetail:
    def test_account_detail_returns_data(self, client: TestClient, latest_period: str) -> None:
        resp = client.get(
            "/api/v1/pl/account/acct_revenue/detail",
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
