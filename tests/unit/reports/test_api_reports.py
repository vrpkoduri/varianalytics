"""Tests for report API endpoints."""
import pytest
from fastapi.testclient import TestClient
from services.reports.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestReportAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_templates_list(self, client):
        resp = client.get("/api/v1/reports/templates")
        assert resp.status_code == 200
