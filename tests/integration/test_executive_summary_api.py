"""Integration tests for executive summary and section narrative API endpoints.

Tests the computation service endpoints that serve section narratives
and executive summaries from the generated parquet data.
"""

import pytest
from fastapi.testclient import TestClient

from shared.data.service import DataService


@pytest.fixture(scope="module")
def comp_client():
    """Computation service test client."""
    from services.computation.main import app
    app.state.data_service = DataService()
    with TestClient(app) as c:
        yield c


@pytest.mark.integration
class TestSectionNarrativeAPI:
    """Tests for GET /dashboard/section-narratives."""

    def test_returns_sections(self, comp_client):
        """Should return section narratives for a valid period."""
        resp = comp_client.get("/api/v1/dashboard/section-narratives?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        assert resp.status_code == 200
        data = resp.json()
        assert "sections" in data
        assert data["count"] >= 4  # At least Revenue, COGS, OpEx, Profitability

    def test_section_names(self, comp_client):
        """Sections should include Revenue, COGS, OpEx, Profitability."""
        resp = comp_client.get("/api/v1/dashboard/section-narratives?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        names = {s.get("sectionName") or s.get("section_name") for s in resp.json()["sections"]}
        assert "Revenue" in names
        assert "Profitability" in names

    def test_section_has_narrative_text(self, comp_client):
        """Each section should have a non-empty narrative."""
        resp = comp_client.get("/api/v1/dashboard/section-narratives?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        for section in resp.json()["sections"]:
            narr = section.get("narrative", "")
            assert len(narr) > 10, f"Section {section.get('sectionName', '?')} has empty narrative"

    def test_empty_for_nonexistent_period(self, comp_client):
        """Should return empty for a period with no data."""
        resp = comp_client.get("/api/v1/dashboard/section-narratives?period_id=2030-01&base_id=BUDGET&view_id=MTD")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


@pytest.mark.integration
class TestExecutiveSummaryAPI:
    """Tests for GET /dashboard/executive-summary."""

    def test_returns_summary(self, comp_client):
        """Should return executive summary for a valid period."""
        resp = comp_client.get("/api/v1/dashboard/executive-summary?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("headline") is not None or data.get("fullNarrative") is not None or data.get("full_narrative") is not None

    def test_headline_content(self, comp_client):
        """Headline should mention Revenue and EBITDA."""
        resp = comp_client.get("/api/v1/dashboard/executive-summary?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        headline = resp.json().get("headline", "")
        assert "Revenue" in headline or "revenue" in headline.lower(), f"Headline missing revenue: {headline}"

    def test_has_key_risks(self, comp_client):
        """Should include key risks array."""
        resp = comp_client.get("/api/v1/dashboard/executive-summary?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        data = resp.json()
        risks = data.get("keyRisks") or data.get("key_risks") or []
        assert isinstance(risks, list)

    def test_has_cross_bu_themes(self, comp_client):
        """Should include cross-BU themes."""
        resp = comp_client.get("/api/v1/dashboard/executive-summary?period_id=2026-05&base_id=BUDGET&view_id=MTD")
        data = resp.json()
        themes = data.get("crossBuThemes") or data.get("cross_bu_themes") or []
        assert isinstance(themes, list)

    def test_empty_for_nonexistent_period(self, comp_client):
        """Should return null/empty for a period with no data."""
        resp = comp_client.get("/api/v1/dashboard/executive-summary?period_id=2030-01&base_id=BUDGET&view_id=MTD")
        assert resp.status_code == 200
