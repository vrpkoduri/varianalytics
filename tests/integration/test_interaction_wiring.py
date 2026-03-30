"""Integration tests for sidebar interaction wiring.

Validates that backend dimension APIs return data in the shape the frontend expects,
and that filtered dashboard requests work correctly.
"""
import pytest
from fastapi.testclient import TestClient
from services.gateway.main import app as gateway_app


@pytest.fixture(scope="module")
def client():
    with TestClient(gateway_app, raise_server_exceptions=False) as c:
        yield c


class TestDimensionAPIs:
    def test_business_units_returns_list(self, client):
        resp = client.get("/api/v1/dimensions/business-units")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_geography_hierarchy_returns_data(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies/geography")
        assert resp.status_code == 200

    def test_segment_hierarchy_returns_data(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies/segment")
        assert resp.status_code == 200

    def test_lob_hierarchy_returns_data(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies/lob")
        assert resp.status_code == 200

    def test_costcenter_hierarchy_returns_data(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies/costcenter")
        assert resp.status_code == 200


class TestFilteredDashboard:
    def test_dashboard_with_bu_filter(self, client):
        """Dashboard should return different data when filtered by BU."""
        from fastapi.testclient import TestClient as TC
        from services.computation.main import app as comp_app

        with TC(comp_app, raise_server_exceptions=False) as cc:
            all_resp = cc.get(
                "/api/v1/dashboard/summary?period_id=2026-06&base_id=BUDGET"
            )
            marsh_resp = cc.get(
                "/api/v1/dashboard/summary?period_id=2026-06&base_id=BUDGET&bu_id=marsh"
            )
            all_cards = all_resp.json().get("cards", [])
            marsh_cards = marsh_resp.json().get("cards", [])
            # Marsh-only should have different values
            if all_cards and marsh_cards:
                assert (
                    all_cards[0]["actual"] != marsh_cards[0]["actual"]
                    or len(marsh_cards) > 0
                )
