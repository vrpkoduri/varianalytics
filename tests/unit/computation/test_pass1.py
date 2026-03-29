"""Unit tests for Pass 1 — Raw Variance Computation.

Tests the core variance calculation logic including MTD leaf variances,
account rollup, calculated row resolution (Gross Profit, EBITDA),
variance percentage edge cases, QTD/YTD aggregation, and topological
sort ordering.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from services.computation.engine.pass1_variance import (
    _build_account_metadata,
    _compute_mtd_leaf_variances,
    _compute_qtd_ytd,
    _resolve_calculated_rows,
    _rollup_accounts,
    _topological_sort_calcs,
    compute_raw_variances,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_dim_account() -> pd.DataFrame:
    """Minimal dim_account with revenue children, a rollup parent, and two
    calculated rows (gross_revenue and gross_profit).
    """
    return pd.DataFrame([
        {
            "account_id": "acct_revenue",
            "account_name": "Revenue",
            "parent_id": None,
            "is_leaf": False,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
        },
        {
            "account_id": "acct_advisory_fees",
            "account_name": "Advisory Fees",
            "parent_id": "acct_revenue",
            "is_leaf": True,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
        },
        {
            "account_id": "acct_consulting_fees",
            "account_name": "Consulting Fees",
            "parent_id": "acct_revenue",
            "is_leaf": True,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
        },
        {
            "account_id": "acct_gross_revenue",
            "account_name": "Gross Revenue",
            "parent_id": None,
            "is_leaf": True,
            "is_calculated": True,
            "calc_formula": "SUM(acct_revenue.children)",
            "calc_dependencies": json.dumps(["acct_revenue"]),
            "pl_category": None,
            "variance_sign": None,
        },
        {
            "account_id": "acct_cor",
            "account_name": "Cost of Revenue",
            "parent_id": None,
            "is_leaf": False,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "COGS",
            "variance_sign": "inverse",
        },
        {
            "account_id": "acct_direct_comp",
            "account_name": "Direct Compensation",
            "parent_id": "acct_cor",
            "is_leaf": True,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "COGS",
            "variance_sign": "inverse",
        },
        {
            "account_id": "acct_total_cor",
            "account_name": "Total Cost of Revenue",
            "parent_id": None,
            "is_leaf": True,
            "is_calculated": True,
            "calc_formula": "SUM(acct_cor.children)",
            "calc_dependencies": json.dumps(["acct_cor"]),
            "pl_category": None,
            "variance_sign": None,
        },
        {
            "account_id": "acct_gross_profit",
            "account_name": "GROSS PROFIT",
            "parent_id": None,
            "is_leaf": True,
            "is_calculated": True,
            "calc_formula": "acct_gross_revenue - acct_total_cor",
            "calc_dependencies": json.dumps(["acct_gross_revenue", "acct_total_cor"]),
            "pl_category": None,
            "variance_sign": None,
        },
        {
            "account_id": "acct_opex",
            "account_name": "Operating Expenses",
            "parent_id": None,
            "is_leaf": False,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "OpEx",
            "variance_sign": "inverse",
        },
        {
            "account_id": "acct_comp_benefits",
            "account_name": "Compensation & Benefits",
            "parent_id": "acct_opex",
            "is_leaf": True,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "OpEx",
            "variance_sign": "inverse",
        },
        {
            "account_id": "acct_da",
            "account_name": "Depreciation & Amortization",
            "parent_id": "acct_opex",
            "is_leaf": True,
            "is_calculated": False,
            "calc_formula": None,
            "calc_dependencies": None,
            "pl_category": "OpEx",
            "variance_sign": "inverse",
        },
        {
            "account_id": "acct_total_opex",
            "account_name": "Total Operating Expenses",
            "parent_id": None,
            "is_leaf": True,
            "is_calculated": True,
            "calc_formula": "SUM(acct_opex.children)",
            "calc_dependencies": json.dumps(["acct_opex"]),
            "pl_category": None,
            "variance_sign": None,
        },
        {
            "account_id": "acct_ebitda",
            "account_name": "EBITDA",
            "parent_id": None,
            "is_leaf": True,
            "is_calculated": True,
            "calc_formula": "acct_gross_profit - acct_total_opex + acct_da",
            "calc_dependencies": json.dumps(["acct_gross_profit", "acct_total_opex", "acct_da"]),
            "pl_category": None,
            "variance_sign": None,
        },
    ])


@pytest.fixture
def simple_fact_financials() -> pd.DataFrame:
    """Simple fact_financials with two leaf revenue accounts and one COGS
    leaf account for a single period, BU, and cost center.
    """
    base_row = {
        "period_id": "2026-01",
        "bu_id": "BU1",
        "costcenter_node_id": "CC1",
        "geo_node_id": "GEO1",
        "segment_node_id": "SEG1",
        "lob_node_id": "LOB1",
        "fiscal_year": 2026,
    }
    return pd.DataFrame([
        {
            **base_row,
            "account_id": "acct_advisory_fees",
            "actual_amount": 120_000,
            "budget_amount": 100_000,
            "forecast_amount": 110_000,
            "prior_year_amount": 95_000,
        },
        {
            **base_row,
            "account_id": "acct_consulting_fees",
            "actual_amount": 80_000,
            "budget_amount": 90_000,
            "forecast_amount": 85_000,
            "prior_year_amount": 70_000,
        },
        {
            **base_row,
            "account_id": "acct_direct_comp",
            "actual_amount": 50_000,
            "budget_amount": 45_000,
            "forecast_amount": 48_000,
            "prior_year_amount": 40_000,
        },
        {
            **base_row,
            "account_id": "acct_comp_benefits",
            "actual_amount": 30_000,
            "budget_amount": 35_000,
            "forecast_amount": 32_000,
            "prior_year_amount": 28_000,
        },
        {
            **base_row,
            "account_id": "acct_da",
            "actual_amount": 10_000,
            "budget_amount": 12_000,
            "forecast_amount": 11_000,
            "prior_year_amount": 9_000,
        },
    ])


@pytest.fixture
def acct_meta(simple_dim_account: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Build account metadata from the simple dim_account."""
    return _build_account_metadata(simple_dim_account)


@pytest.fixture
def dim_period_3_months() -> pd.DataFrame:
    """Three months in Q1 2026 for QTD/YTD testing."""
    return pd.DataFrame([
        {"period_id": "2026-01", "fiscal_year": 2026, "fiscal_quarter": 1},
        {"period_id": "2026-02", "fiscal_year": 2026, "fiscal_quarter": 1},
        {"period_id": "2026-03", "fiscal_year": 2026, "fiscal_quarter": 1},
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMTDVarianceCalculation:
    """Test basic MTD variance computation: actual - comparator."""

    def test_mtd_variance_calculation(
        self,
        simple_fact_financials: pd.DataFrame,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """Actual - budget = variance for a simple case.

        Advisory Fees: actual=120K, budget=100K -> variance=+20K
        Consulting Fees: actual=80K, budget=90K -> variance=-10K
        """
        mtd = _compute_mtd_leaf_variances(simple_fact_financials, acct_meta)
        budget_rows = mtd[mtd["base_id"] == "BUDGET"]

        advisory = budget_rows[budget_rows["account_id"] == "acct_advisory_fees"]
        assert len(advisory) == 1
        assert advisory.iloc[0]["variance_amount"] == pytest.approx(20_000)
        assert advisory.iloc[0]["actual_amount"] == pytest.approx(120_000)
        assert advisory.iloc[0]["comparator_amount"] == pytest.approx(100_000)

        consulting = budget_rows[budget_rows["account_id"] == "acct_consulting_fees"]
        assert len(consulting) == 1
        assert consulting.iloc[0]["variance_amount"] == pytest.approx(-10_000)

    def test_mtd_computes_all_three_bases(
        self,
        simple_fact_financials: pd.DataFrame,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """MTD leaf variances are computed for BUDGET, FORECAST, and PRIOR_YEAR."""
        mtd = _compute_mtd_leaf_variances(simple_fact_financials, acct_meta)
        bases = set(mtd["base_id"].unique())
        assert bases == {"BUDGET", "FORECAST", "PRIOR_YEAR"}


@pytest.mark.unit
class TestAccountRollup:
    """Test that rollup parents sum their children correctly."""

    def test_account_rollup_sums_children(
        self,
        simple_fact_financials: pd.DataFrame,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """Parent revenue = sum of child revenue accounts.

        Advisory: actual=120K, budget=100K, var=+20K
        Consulting: actual=80K, budget=90K, var=-10K
        Parent (acct_revenue): actual=200K, budget=190K, var=+10K
        """
        mtd = _compute_mtd_leaf_variances(simple_fact_financials, acct_meta)
        rolled = _rollup_accounts(mtd, acct_meta)

        budget_rows = rolled[rolled["base_id"] == "BUDGET"]
        parent = budget_rows[budget_rows["account_id"] == "acct_revenue"]
        assert len(parent) >= 1

        parent_row = parent.iloc[0]
        assert parent_row["actual_amount"] == pytest.approx(200_000)
        assert parent_row["comparator_amount"] == pytest.approx(190_000)
        assert parent_row["variance_amount"] == pytest.approx(10_000)


@pytest.mark.unit
class TestCalculatedRows:
    """Test calculated row resolution for Gross Profit and EBITDA."""

    def test_calculated_row_gross_profit(
        self,
        simple_fact_financials: pd.DataFrame,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """Gross Profit = Gross Revenue - Total COR.

        Gross Revenue (sum of revenue children): variance = 20K - 10K = 10K
        Total COR (sum of COR children): direct_comp variance = 5K
        Gross Profit variance = 10K - 5K = 5K
        """
        mtd = _compute_mtd_leaf_variances(simple_fact_financials, acct_meta)
        rolled = _rollup_accounts(mtd, acct_meta)
        calced = _resolve_calculated_rows(rolled, acct_meta)

        budget_rows = calced[calced["base_id"] == "BUDGET"]
        gp = budget_rows[budget_rows["account_id"] == "acct_gross_profit"]
        assert len(gp) >= 1

        # Gross Revenue variance = 20K + (-10K) = 10K
        # Total COR variance = 5K (direct_comp only child)
        # GP = 10K - 5K = 5K
        gp_row = gp.iloc[0]
        assert gp_row["variance_amount"] == pytest.approx(5_000)
        assert bool(gp_row["is_calculated"]) is True

    def test_calculated_row_ebitda(
        self,
        simple_fact_financials: pd.DataFrame,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """EBITDA = Gross Profit - Total OpEx + D&A.

        Gross Profit variance = 5K (from test above)
        Total OpEx variance = comp_benefits(-5K) + da(-2K) = -7K
        D&A variance = -2K
        EBITDA = 5K - (-7K) + (-2K) = 5K + 7K - 2K = 10K
        """
        mtd = _compute_mtd_leaf_variances(simple_fact_financials, acct_meta)
        rolled = _rollup_accounts(mtd, acct_meta)
        calced = _resolve_calculated_rows(rolled, acct_meta)

        budget_rows = calced[calced["base_id"] == "BUDGET"]
        ebitda = budget_rows[budget_rows["account_id"] == "acct_ebitda"]
        assert len(ebitda) >= 1

        ebitda_row = ebitda.iloc[0]
        # GP = 5K, total_opex = -7K, da = -2K
        # EBITDA = 5K - (-7K) + (-2K) = 10K
        assert ebitda_row["variance_amount"] == pytest.approx(10_000)
        assert bool(ebitda_row["is_calculated"]) is True


@pytest.mark.unit
class TestVariancePercentage:
    """Test variance_pct edge cases."""

    def test_variance_pct_null_when_comparator_zero(self) -> None:
        """When budget=0 the variance_pct should be NaN.

        This tests the np.where logic in compute_raw_variances that sets
        variance_pct to NaN when comparator_amount is zero.
        """
        df = pd.DataFrame({
            "variance_amount": [1000.0, 5000.0, -3000.0],
            "comparator_amount": [0.0, 10000.0, 0.0],
        })
        result = np.where(
            df["comparator_amount"] != 0,
            (df["variance_amount"] / df["comparator_amount"]) * 100,
            np.nan,
        )
        assert np.isnan(result[0]), "Comparator=0 should produce NaN pct"
        assert result[1] == pytest.approx(50.0)
        assert np.isnan(result[2]), "Comparator=0 should produce NaN pct"


@pytest.mark.unit
class TestQTDYTDAggregation:
    """Test QTD and YTD computation from MTD rows."""

    def _make_mtd_rows(self) -> pd.DataFrame:
        """Helper to create 3 months of MTD data for one account."""
        base = {
            "bu_id": "BU1",
            "costcenter_node_id": "CC1",
            "account_id": "acct_advisory_fees",
            "geo_node_id": "GEO1",
            "segment_node_id": "SEG1",
            "lob_node_id": "LOB1",
            "fiscal_year": 2026,
            "base_id": "BUDGET",
            "is_calculated": False,
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "view_id": "MTD",
        }
        return pd.DataFrame([
            {**base, "period_id": "2026-01", "actual_amount": 100, "comparator_amount": 90, "variance_amount": 10},
            {**base, "period_id": "2026-02", "actual_amount": 120, "comparator_amount": 100, "variance_amount": 20},
            {**base, "period_id": "2026-03", "actual_amount": 130, "comparator_amount": 110, "variance_amount": 20},
        ])

    def test_qtd_sums_mtd_within_quarter(
        self,
        dim_period_3_months: pd.DataFrame,
    ) -> None:
        """QTD = sum of MTD for same quarter.

        3 months in Q1: variance = 10 + 20 + 20 = 50.
        """
        mtd = self._make_mtd_rows()
        all_views = _compute_qtd_ytd(mtd, dim_period_3_months)

        qtd = all_views[all_views["view_id"] == "QTD"]
        assert len(qtd) >= 1
        qtd_var = qtd.iloc[0]["variance_amount"]
        assert qtd_var == pytest.approx(50)

    def test_ytd_sums_mtd_within_year(
        self,
        dim_period_3_months: pd.DataFrame,
    ) -> None:
        """YTD = sum of all MTD in year.

        All 3 months are in 2026: variance = 10 + 20 + 20 = 50.
        """
        mtd = self._make_mtd_rows()
        all_views = _compute_qtd_ytd(mtd, dim_period_3_months)

        ytd = all_views[all_views["view_id"] == "YTD"]
        assert len(ytd) >= 1
        ytd_var = ytd.iloc[0]["variance_amount"]
        assert ytd_var == pytest.approx(50)


@pytest.mark.unit
class TestTopologicalSort:
    """Test topological sort of calculated accounts."""

    def test_topological_sort_order(
        self,
        acct_meta: dict[str, dict[str, Any]],
    ) -> None:
        """Calculated row dependency ordering is correct.

        Expected order:
        1. acct_gross_revenue (depends on acct_revenue, which is not calculated)
        2. acct_total_cor (depends on acct_cor, which is not calculated)
        3. acct_total_opex (depends on acct_opex, which is not calculated)
        4. acct_gross_profit (depends on acct_gross_revenue, acct_total_cor)
        5. acct_ebitda (depends on acct_gross_profit, acct_total_opex, acct_da)

        acct_gross_profit MUST come after acct_gross_revenue and acct_total_cor.
        acct_ebitda MUST come after acct_gross_profit and acct_total_opex.
        """
        order = _topological_sort_calcs(acct_meta)

        assert "acct_gross_profit" in order
        assert "acct_ebitda" in order
        assert "acct_gross_revenue" in order
        assert "acct_total_cor" in order
        assert "acct_total_opex" in order

        gp_idx = order.index("acct_gross_profit")
        gr_idx = order.index("acct_gross_revenue")
        tc_idx = order.index("acct_total_cor")
        to_idx = order.index("acct_total_opex")
        ebitda_idx = order.index("acct_ebitda")

        assert gr_idx < gp_idx, "Gross Revenue must be resolved before Gross Profit"
        assert tc_idx < gp_idx, "Total COR must be resolved before Gross Profit"
        assert gp_idx < ebitda_idx, "Gross Profit must be resolved before EBITDA"
        assert to_idx < ebitda_idx, "Total OpEx must be resolved before EBITDA"
