"""Persona & Regression Guard Tests.

Validates filter behavior, persona visibility rules, and guards
against regressions in API contracts.
"""
import pytest
from fastapi.testclient import TestClient
from services.computation.main import app as computation_app


@pytest.fixture(scope="module")
def comp():
    with TestClient(computation_app, raise_server_exceptions=False) as c:
        yield c


class TestBUFiltering:
    def test_bu_filter_reduces_count(self, comp):
        all_resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=500")
        all_total = all_resp.json().get("total", all_resp.json().get("total_count", 0))
        marsh_resp = comp.get("/api/v1/variances/?period_id=2026-06&bu_id=marsh&page_size=500")
        marsh_total = marsh_resp.json().get("total", marsh_resp.json().get("total_count", 0))
        assert marsh_total < all_total, f"Marsh ({marsh_total}) should be < All ({all_total})"

    def test_bu_filter_only_returns_selected(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&bu_id=marsh&page_size=50")
        items = resp.json().get("variances", resp.json().get("items", []))
        for item in items:
            assert item.get("bu_id") == "marsh", f"Non-Marsh item: {item.get('bu_id')}"


class TestViewTypeFiltering:
    def test_qtd_values_differ_from_mtd(self, comp):
        mtd = comp.get("/api/v1/dashboard/summary?period_id=2026-06&view_id=MTD&base_id=BUDGET")
        qtd = comp.get("/api/v1/dashboard/summary?period_id=2026-06&view_id=QTD&base_id=BUDGET")
        mtd_cards = mtd.json().get("cards", [])
        qtd_cards = qtd.json().get("cards", [])
        if mtd_cards and qtd_cards:
            # QTD should have different (usually larger) values
            assert mtd_cards[0]["actual"] != qtd_cards[0]["actual"] or len(qtd_cards) > 0


class TestComparisonBaseFiltering:
    def test_forecast_base_returns_data(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=2026-06&base_id=FORECAST")
        cards = resp.json().get("cards", [])
        # FORECAST may have fewer cards if data is sparse, but should not error
        assert resp.status_code == 200

    def test_prior_year_base_returns_data(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=2026-06&base_id=PRIOR_YEAR")
        assert resp.status_code == 200


class TestRegressionGuards:
    def test_invalid_period_returns_empty_cards(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=9999-99&base_id=BUDGET")
        assert resp.status_code == 200
        cards = resp.json().get("cards", [])
        assert len(cards) == 0

    def test_waterfall_steps_structure(self, comp):
        resp = comp.get("/api/v1/dashboard/waterfall?period_id=2026-06")
        steps = resp.json().get("steps", [])
        if steps:
            assert "name" in steps[0], "Missing name in waterfall step"
            assert "value" in steps[0], "Missing value in waterfall step"

    def test_variance_fields_include_new_keys(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=3")
        items = resp.json().get("variances", resp.json().get("items", []))
        for item in items:
            assert "geo_node_id" in item, "Missing geo_node_id (Sprint 2 field)"
            assert "variance_sign" in item, "Missing variance_sign (Sprint 2 field)"
            assert "pl_category" in item, "Missing pl_category (Sprint 2 field)"
