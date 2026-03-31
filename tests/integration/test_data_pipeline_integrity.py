"""Data Pipeline Integrity Tests.

Validates mathematical correctness from engine output through API responses.
Uses pytest.approx for floating-point tolerance.
"""
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from services.computation.main import app as computation_app


@pytest.fixture(scope="module")
def comp():
    with TestClient(computation_app, raise_server_exceptions=False) as c:
        yield c

@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet("data/output/fact_variance_material.parquet")

@pytest.fixture(scope="module")
def mtd_budget(vm):
    return vm[(vm["view_id"] == "MTD") & (vm["base_id"] == "BUDGET") & (vm["period_id"] == "2026-06")]


class TestCalculatedRowBalance:
    def test_gross_profit_equals_revenue_minus_cor(self, mtd_budget):
        grev = mtd_budget[mtd_budget["account_id"] == "acct_gross_revenue"]["actual_amount"].sum()
        tcor = mtd_budget[mtd_budget["account_id"] == "acct_total_cor"]["actual_amount"].sum()
        gp = mtd_budget[mtd_budget["account_id"] == "acct_gross_profit"]["actual_amount"].sum()
        assert gp == pytest.approx(grev - tcor, abs=1.0), f"GP {gp} != GRev {grev} - COR {tcor}"

    def test_operating_income_equals_gp_minus_opex(self, mtd_budget):
        gp = mtd_budget[mtd_budget["account_id"] == "acct_gross_profit"]["actual_amount"].sum()
        topex = mtd_budget[mtd_budget["account_id"] == "acct_total_opex"]["actual_amount"].sum()
        oi = mtd_budget[mtd_budget["account_id"] == "acct_operating_income"]["actual_amount"].sum()
        assert oi == pytest.approx(gp - topex, abs=1.0)

    def test_net_income_equals_pbt_minus_tax(self, mtd_budget):
        pbt = mtd_budget[mtd_budget["account_id"] == "acct_pbt"]["actual_amount"].sum()
        tax = mtd_budget[mtd_budget["account_id"] == "acct_tax"]["actual_amount"].sum()
        ni = mtd_budget[mtd_budget["account_id"] == "acct_net_income"]["actual_amount"].sum()
        assert ni == pytest.approx(pbt - tax, abs=1.0)

    def test_ebitda_calculation(self, mtd_budget):
        gp = mtd_budget[mtd_budget["account_id"] == "acct_gross_profit"]["actual_amount"].sum()
        topex = mtd_budget[mtd_budget["account_id"] == "acct_total_opex"]["actual_amount"].sum()
        da = mtd_budget[mtd_budget["account_id"] == "acct_da"]["actual_amount"].sum()
        ebitda = mtd_budget[mtd_budget["account_id"] == "acct_ebitda"]["actual_amount"].sum()
        assert ebitda == pytest.approx(gp - topex + da, abs=1.0)


class TestBUVarianceConsistency:
    def test_bu_variance_sum_equals_total(self, comp):
        all_resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=500")
        all_total = all_resp.json().get("total", all_resp.json().get("total_count", 0))
        bu_sum = 0
        for bu in ["marsh", "mercer", "guy_carpenter", "oliver_wyman", "mmc_corporate"]:
            bu_resp = comp.get(f"/api/v1/variances/?period_id=2026-06&bu_id={bu}&page_size=500")
            bu_total = bu_resp.json().get("total", bu_resp.json().get("total_count", 0))
            bu_sum += bu_total
        assert bu_sum == all_total, f"BU sum {bu_sum} != total {all_total}"


class TestAPIDataQuality:
    def test_all_kpi_values_numeric(self, comp):
        resp = comp.get("/api/v1/dashboard/summary?period_id=2026-06&base_id=BUDGET")
        for card in resp.json().get("cards", []):
            assert isinstance(card.get("actual"), (int, float)), f"Non-numeric actual: {card}"
            assert isinstance(card.get("comparator"), (int, float)), f"Non-numeric comparator: {card}"

    def test_no_nan_in_required_fields(self, vm):
        assert vm["actual_amount"].isna().sum() == 0, "NaN in actual_amount"
        assert vm["account_id"].isna().sum() == 0, "NaN in account_id"
        assert vm["bu_id"].isna().sum() == 0, "NaN in bu_id"

    def test_every_variance_has_account_and_bu(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=10")
        items = resp.json().get("variances", resp.json().get("items", []))
        for item in items:
            assert item.get("account_id") or item.get("account_name"), f"Missing account: {item}"
            assert item.get("bu_id"), f"Missing bu_id: {item}"

    def test_variance_has_geo_and_sign(self, comp):
        resp = comp.get("/api/v1/variances/?period_id=2026-06&page_size=5")
        items = resp.json().get("variances", resp.json().get("items", []))
        for item in items:
            assert "geo_node_id" in item, f"Missing geo_node_id"
            assert "variance_sign" in item, f"Missing variance_sign"

    def test_heatmap_values_reasonable(self, comp):
        resp = comp.get("/api/v1/dashboard/heatmap?period_id=2026-06")
        data = resp.json()
        cells = data.get("cells", [])
        for row in cells:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict):
                        pct = cell.get("pct")
                        if pct is not None:
                            assert -200 <= pct <= 200, f"Unreasonable heatmap %: {pct}"

    def test_trends_returns_data(self, comp):
        resp = comp.get("/api/v1/dashboard/trends?periods=12")
        assert resp.status_code == 200
        data = resp.json().get("data", [])
        assert len(data) >= 1, f"Expected >=1 trend points, got {len(data)}"
