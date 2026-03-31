"""Integration tests for report scheduling + distribution API."""
import pytest
from fastapi.testclient import TestClient

from services.reports.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestSchedulingAPI:
    def test_list_schedules_empty(self, client):
        resp = client.get("/api/v1/scheduling/schedules")
        assert resp.status_code == 200

    def test_create_schedule(self, client):
        resp = client.post("/api/v1/scheduling/schedules", json={
            "name": "Test Schedule",
            "frequency": "weekly",
            "report_format": "PDF",
            "period_key_pattern": "2026-06",
            "comparison_base": "BUDGET",
            "view": "MTD",
            "enabled": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "schedule_id" in data
        assert data["name"] == "Test Schedule"

    def test_create_and_list_schedule(self, client):
        resp = client.post("/api/v1/scheduling/schedules", json={
            "name": "Listed Schedule",
            "frequency": "daily",
            "report_format": "XLSX",
        })
        assert resp.status_code == 200
        listing = client.get("/api/v1/scheduling/schedules")
        assert listing.status_code == 200
        names = [s["name"] for s in listing.json()]
        assert "Listed Schedule" in names

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/v1/scheduling/schedules/nonexistent-id")
        assert resp.status_code == 404


class TestDistributionAPI:
    def test_list_recipients_empty(self, client):
        resp = client.get("/api/v1/distribution/recipients")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_distribution_list(self, client):
        resp = client.post("/api/v1/distribution/recipients", json={
            "name": "Finance Team",
            "description": "Monthly report recipients",
            "channels": [
                {"channel_type": "email", "target": "finance@example.com"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Finance Team"
        assert len(data["channels"]) == 1

    def test_send_report_invalid_job(self, client):
        resp = client.post("/api/v1/distribution/send", json={
            "job_id": "nonexistent-job",
            "ad_hoc_channels": [],
        })
        assert resp.status_code == 400
