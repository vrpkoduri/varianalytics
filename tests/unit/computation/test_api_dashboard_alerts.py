"""Tests for netting/trend alert API endpoints."""
import pytest
from fastapi.testclient import TestClient
from services.computation.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestNettingAlertEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/dashboard/alerts/netting?period_id=2026-06")
        assert resp.status_code == 200

    def test_returns_alerts_array(self, client):
        resp = client.get("/api/v1/dashboard/alerts/netting?period_id=2026-06")
        data = resp.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_returns_count(self, client):
        resp = client.get("/api/v1/dashboard/alerts/netting?period_id=2026-06")
        data = resp.json()
        assert "count" in data


class TestTrendAlertEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/dashboard/alerts/trends")
        assert resp.status_code == 200

    def test_returns_alerts_array(self, client):
        resp = client.get("/api/v1/dashboard/alerts/trends")
        data = resp.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
