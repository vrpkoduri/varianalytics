"""Unit tests for gateway dimension endpoints."""

import pytest
from fastapi.testclient import TestClient

from shared.data.service import DataService


@pytest.fixture(scope="module")
def client():
    """Create test client with DataService initialized."""
    from services.gateway.main import app

    # Initialize DataService on app state
    app.state.data_service = DataService()

    with TestClient(app) as c:
        yield c


@pytest.mark.unit
class TestDimensionEndpoints:
    """Test dimension lookup endpoints."""

    def test_list_business_units_returns_5(self, client):
        """GET /api/v1/dimensions/business-units returns 5 BUs."""
        resp = client.get("/api/v1/dimensions/business-units")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        bu_ids = {bu["bu_id"] for bu in data}
        assert "marsh" in bu_ids

    def test_list_accounts_returns_38(self, client):
        """GET /api/v1/dimensions/accounts returns 38 accounts."""
        resp = client.get("/api/v1/dimensions/accounts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 38

    def test_list_periods_returns_36(self, client):
        """GET /api/v1/dimensions/periods returns 36 periods."""
        resp = client.get("/api/v1/dimensions/periods")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 36
        # Verify structure
        assert "period_id" in data[0]
        assert "fiscal_year" in data[0]

    def test_get_hierarchy_geography(self, client):
        """GET /api/v1/dimensions/hierarchies/geography returns tree."""
        resp = client.get("/api/v1/dimensions/hierarchies/geography")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension_name"] == "geography"
        assert isinstance(data["roots"], list)
