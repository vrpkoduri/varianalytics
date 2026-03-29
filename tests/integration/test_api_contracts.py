"""API response schema contract tests.

Verifies that API endpoints return the exact JSON structure
the frontend expects. Catches breaking schema changes early.
"""

import pytest
from fastapi.testclient import TestClient

from services.computation.main import app as computation_app
from services.gateway.main import app as gateway_app
from shared.data.service import DataService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _latest_period() -> str:
    """Return a period_id that has variance data."""
    DataService.reset_instance()
    ds = DataService(data_dir="data/output")
    vm = ds._table("fact_variance_material")
    if vm.empty:
        periods = ds.get_periods()
        return periods[-1]["period_id"]
    return vm["period_id"].max()


# ---------------------------------------------------------------------------
# Computation Service contract tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDashboardSummaryContract:

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(computation_app, raise_server_exceptions=False) as c:
            self.client = c
            yield c

    def test_dashboard_summary_response_schema(self):
        """GET /api/v1/dashboard/summary returns cards with all required fields."""
        period = _latest_period()
        response = self.client.get(
            "/api/v1/dashboard/summary",
            params={"period_id": period},
        )
        assert response.status_code == 200
        body = response.json()

        assert "cards" in body
        assert isinstance(body["cards"], list)
        assert len(body["cards"]) > 0

        for card in body["cards"]:
            assert isinstance(card["metric_name"], str)
            assert isinstance(card["actual"], (int, float))
            assert isinstance(card["comparator"], (int, float))
            assert isinstance(card["variance_amount"], (int, float))
            assert card["variance_pct"] is None or isinstance(card["variance_pct"], (int, float))
            assert isinstance(card["is_favorable"], bool)
            assert isinstance(card["is_material"], bool)


@pytest.mark.integration
class TestVarianceListContract:

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(computation_app, raise_server_exceptions=False) as c:
            self.client = c
            yield c

    def test_variance_list_response_schema(self):
        """GET /api/v1/variances/ returns paginated items with required fields."""
        period = _latest_period()
        response = self.client.get(
            "/api/v1/variances/",
            params={"period_id": period},
        )
        assert response.status_code == 200
        body = response.json()

        assert "items" in body
        assert isinstance(body["items"], list)
        assert isinstance(body["total_count"], int)
        assert isinstance(body["page"], int)
        assert isinstance(body["page_size"], int)

        if body["items"]:
            item = body["items"][0]
            assert "variance_id" in item
            assert "account_id" in item
            assert isinstance(item["variance_amount"], (int, float))
            assert item["variance_pct"] is None or isinstance(item["variance_pct"], (int, float))


@pytest.mark.integration
class TestPLStatementContract:

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(computation_app, raise_server_exceptions=False) as c:
            self.client = c
            yield c

    def test_pl_statement_response_schema(self):
        """GET /api/v1/pl/statement returns rows with required structure."""
        period = _latest_period()
        response = self.client.get(
            "/api/v1/pl/statement",
            params={"period_id": period},
        )
        assert response.status_code == 200
        body = response.json()

        assert "rows" in body
        assert isinstance(body["rows"], list)
        assert len(body["rows"]) > 0

        def _check_row(row: dict) -> None:
            assert "account_id" in row
            assert "account_name" in row
            assert isinstance(row["actual"], (int, float))
            assert isinstance(row["comparator"], (int, float))
            assert isinstance(row["variance_amount"], (int, float))
            if row.get("children"):
                for child in row["children"]:
                    _check_row(child)

        for row in body["rows"]:
            _check_row(row)


@pytest.mark.integration
class TestReviewQueueContract:

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(gateway_app, raise_server_exceptions=False) as c:
            self.client = c
            yield c

    def test_review_queue_response_schema(self):
        """GET /api/v1/review/queue returns items with required fields."""
        response = self.client.get("/api/v1/review/queue")
        assert response.status_code == 200
        body = response.json()

        assert "items" in body
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)
        assert isinstance(body["page"], int)

        for item in body["items"]:
            assert "variance_id" in item
            assert "account_name" in item
            assert "current_status" in item
            assert isinstance(item["variance_amount"], (int, float))
