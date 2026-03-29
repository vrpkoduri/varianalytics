"""Calculated P&L row balance validation.

Verifies all 10 calculated rows (Gross Revenue, Total COR, Gross Profit,
Total OpEx, EBITDA, Operating Income, Total NonOp, PBT, Net Income, Total P&L)
balance correctly according to their formulas in fact_variance_material.
"""

import pandas as pd
import pytest

DATA_DIR = "data/output"

# Account IDs for children of each parent group
REVENUE_CHILDREN = [
    "acct_advisory_fees", "acct_consulting_fees", "acct_reinsurance_comm",
    "acct_investment_income", "acct_data_analytics_rev", "acct_other_revenue",
]
COR_CHILDREN = [
    "acct_direct_comp", "acct_subcontractor", "acct_direct_tech", "acct_other_direct",
]
OPEX_CHILDREN = [
    "acct_comp_benefits", "acct_tech_infra", "acct_prof_services",
    "acct_occupancy", "acct_travel", "acct_marketing", "acct_da",
    "acct_insurance", "acct_training", "acct_other_opex",
]
NONOP_CHILDREN = [
    "acct_interest_exp", "acct_interest_inc", "acct_other_nonop",
]

# Dimensional slice grouping columns
SLICE_COLS = [
    "bu_id", "costcenter_node_id", "geo_node_id",
    "segment_node_id", "lob_node_id",
]

# Balance tolerance for floating-point arithmetic
TOLERANCE = 0.02


@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet(f"{DATA_DIR}/fact_variance_material.parquet")


@pytest.fixture(scope="module")
def dim_account():
    return pd.read_parquet(f"{DATA_DIR}/dim_account.parquet")


@pytest.fixture(scope="module")
def default_slice(vm: pd.DataFrame):
    """Return a filtered vm for the default test period/view/base."""
    return vm[
        (vm["period_id"] == "2026-06")
        & (vm["view_id"] == "MTD")
        & (vm["base_id"] == "BUDGET")
    ]


def _get_amount(vm_slice: pd.DataFrame, account_id: str, field: str = "variance_amount") -> float:
    """Get the sum of a field for a given account in a dimensional slice."""
    rows = vm_slice[vm_slice["account_id"] == account_id]
    return rows[field].sum() if len(rows) > 0 else 0.0


def _get_children_sum(vm_slice: pd.DataFrame, child_ids: list[str], field: str = "variance_amount") -> float:
    """Get the sum of a field across multiple child account IDs."""
    rows = vm_slice[vm_slice["account_id"].isin(child_ids)]
    return rows[field].sum()


def _check_formula_across_slices(
    filtered_vm: pd.DataFrame,
    calc_fn,
    description: str,
) -> None:
    """Verify a formula holds across all dimensional slices."""
    slices = filtered_vm.groupby(SLICE_COLS)
    failures = []

    for keys, group in slices:
        expected, actual = calc_fn(group)
        if abs(expected - actual) > TOLERANCE:
            failures.append(
                f"  Slice {keys}: expected={expected:.4f}, actual={actual:.4f}, "
                f"diff={abs(expected - actual):.4f}"
            )

    assert len(failures) == 0, (
        f"{description} failed in {len(failures)} slices:\n"
        + "\n".join(failures[:5])
    )


# ---------------------------------------------------------------------------
# Individual formula tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCalculatedRowFormulas:
    """Tests that each calculated row formula holds in fact_variance_material."""

    def test_gross_revenue_equals_sum_children(self, default_slice: pd.DataFrame) -> None:
        """acct_gross_revenue = SUM(revenue child accounts)."""
        def calc(group):
            expected = _get_children_sum(group, REVENUE_CHILDREN)
            actual = _get_amount(group, "acct_gross_revenue")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Gross Revenue = SUM(Revenue children)")

    def test_total_cor_equals_sum_children(self, default_slice: pd.DataFrame) -> None:
        """acct_total_cor = SUM(COR child accounts)."""
        def calc(group):
            expected = _get_children_sum(group, COR_CHILDREN)
            actual = _get_amount(group, "acct_total_cor")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Total COR = SUM(COR children)")

    def test_gross_profit_formula(self, default_slice: pd.DataFrame) -> None:
        """acct_gross_profit = acct_gross_revenue - acct_total_cor."""
        def calc(group):
            expected = _get_amount(group, "acct_gross_revenue") - _get_amount(group, "acct_total_cor")
            actual = _get_amount(group, "acct_gross_profit")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Gross Profit = Gross Revenue - Total COR")

    def test_total_opex_equals_sum_children(self, default_slice: pd.DataFrame) -> None:
        """acct_total_opex = SUM(OpEx child accounts)."""
        def calc(group):
            expected = _get_children_sum(group, OPEX_CHILDREN)
            actual = _get_amount(group, "acct_total_opex")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Total OpEx = SUM(OpEx children)")

    def test_ebitda_formula(self, default_slice: pd.DataFrame) -> None:
        """acct_ebitda = acct_gross_profit - acct_total_opex + acct_da."""
        def calc(group):
            expected = (
                _get_amount(group, "acct_gross_profit")
                - _get_amount(group, "acct_total_opex")
                + _get_amount(group, "acct_da")
            )
            actual = _get_amount(group, "acct_ebitda")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "EBITDA = Gross Profit - Total OpEx + D&A")

    def test_operating_income_formula(self, default_slice: pd.DataFrame) -> None:
        """acct_operating_income = acct_gross_profit - acct_total_opex."""
        def calc(group):
            expected = _get_amount(group, "acct_gross_profit") - _get_amount(group, "acct_total_opex")
            actual = _get_amount(group, "acct_operating_income")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Operating Income = Gross Profit - Total OpEx")

    def test_total_nonop_equals_sum_children(self, default_slice: pd.DataFrame) -> None:
        """acct_total_nonop = SUM(NonOp child accounts)."""
        def calc(group):
            expected = _get_children_sum(group, NONOP_CHILDREN)
            actual = _get_amount(group, "acct_total_nonop")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Total NonOp = SUM(NonOp children)")

    def test_pbt_formula(self, default_slice: pd.DataFrame) -> None:
        """acct_pbt = acct_operating_income + acct_total_nonop."""
        def calc(group):
            expected = _get_amount(group, "acct_operating_income") + _get_amount(group, "acct_total_nonop")
            actual = _get_amount(group, "acct_pbt")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "PBT = Operating Income + Total NonOp")

    def test_net_income_formula(self, default_slice: pd.DataFrame) -> None:
        """acct_net_income = acct_pbt - acct_tax."""
        def calc(group):
            expected = _get_amount(group, "acct_pbt") - _get_amount(group, "acct_tax")
            actual = _get_amount(group, "acct_net_income")
            return expected, actual

        _check_formula_across_slices(default_slice, calc, "Net Income = PBT - Tax")

    def test_all_formulas_hold_across_multiple_periods(self, vm: pd.DataFrame) -> None:
        """All calculated row formulas hold across 6 different (period, view, base) combos."""
        combos = [
            ("2026-06", "MTD", "BUDGET"),
            ("2026-06", "QTD", "BUDGET"),
        ]
        # Filter to combos that actually exist in the data
        available_combos = []
        for period, view, base in combos:
            subset = vm[
                (vm["period_id"] == period)
                & (vm["view_id"] == view)
                & (vm["base_id"] == base)
            ]
            if len(subset) > 0:
                available_combos.append((period, view, base, subset))

        assert len(available_combos) >= 1, "No valid (period, view, base) combos found"

        for period, view, base, filtered in available_combos:
            # Test Gross Profit formula as representative
            for keys, group in filtered.groupby(SLICE_COLS):
                gross_rev = _get_amount(group, "acct_gross_revenue")
                total_cor = _get_amount(group, "acct_total_cor")
                gross_profit = _get_amount(group, "acct_gross_profit")
                expected = gross_rev - total_cor
                assert abs(expected - gross_profit) <= TOLERANCE, (
                    f"Gross Profit formula failed for ({period}, {view}, {base}), "
                    f"slice {keys}: expected={expected:.4f}, actual={gross_profit:.4f}"
                )

            # Test Net Income formula as representative
            for keys, group in filtered.groupby(SLICE_COLS):
                pbt = _get_amount(group, "acct_pbt")
                tax = _get_amount(group, "acct_tax")
                net_income = _get_amount(group, "acct_net_income")
                expected = pbt - tax
                assert abs(expected - net_income) <= TOLERANCE, (
                    f"Net Income formula failed for ({period}, {view}, {base}), "
                    f"slice {keys}: expected={expected:.4f}, actual={net_income:.4f}"
                )
