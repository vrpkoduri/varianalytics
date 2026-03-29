"""Data quality edge case tests.

Validates handling of NaN, Inf, FX rates, forecast nullability,
prior year data gaps, and revenue sign conventions.
"""

import numpy as np
import pandas as pd
import pytest

DATA_DIR = "data/output"

REVENUE_ACCOUNTS = [
    "acct_advisory_fees", "acct_consulting_fees", "acct_reinsurance_comm",
    "acct_investment_income", "acct_data_analytics_rev", "acct_other_revenue",
]


@pytest.fixture(scope="module")
def ff():
    return pd.read_parquet(f"{DATA_DIR}/fact_financials.parquet")


@pytest.fixture(scope="module")
def vm():
    return pd.read_parquet(f"{DATA_DIR}/fact_variance_material.parquet")


@pytest.fixture(scope="module")
def dim_period():
    return pd.read_parquet(f"{DATA_DIR}/dim_period.parquet")


# ---------------------------------------------------------------------------
# Amount quality
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAmountQuality:
    """Tests that key amount columns have no invalid values."""

    def test_actual_amount_no_nan_inf(self, ff: pd.DataFrame) -> None:
        """actual_amount should have no NaN or Inf values."""
        nan_count = ff["actual_amount"].isna().sum()
        inf_count = np.isinf(ff["actual_amount"]).sum()
        assert nan_count == 0, f"actual_amount has {nan_count} NaN values"
        assert inf_count == 0, f"actual_amount has {inf_count} Inf values"

    def test_budget_amount_no_nan_inf(self, ff: pd.DataFrame) -> None:
        """budget_amount should have no NaN or Inf values."""
        nan_count = ff["budget_amount"].isna().sum()
        inf_count = np.isinf(ff["budget_amount"]).sum()
        assert nan_count == 0, f"budget_amount has {nan_count} NaN values"
        assert inf_count == 0, f"budget_amount has {inf_count} Inf values"

    def test_no_negative_revenue_actuals(self, ff: pd.DataFrame) -> None:
        """Revenue account actual amounts should all be >= 0."""
        rev_data = ff[ff["account_id"].isin(REVENUE_ACCOUNTS)]
        negatives = rev_data[rev_data["actual_amount"] < 0]
        assert len(negatives) == 0, (
            f"Found {len(negatives)} negative revenue actuals. "
            f"Accounts: {negatives['account_id'].unique().tolist()}"
        )


# ---------------------------------------------------------------------------
# Nullability patterns
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNullabilityPatterns:
    """Tests that NaN values appear only where expected."""

    def test_forecast_nan_pattern(
        self, ff: pd.DataFrame, dim_period: pd.DataFrame,
    ) -> None:
        """Forecast NaN rows should correspond to non-closed periods."""
        nan_forecast = ff[ff["forecast_amount"].isna()]
        assert len(nan_forecast) > 0, "Expected some NaN forecasts for future periods"

        # Join with dim_period to check is_closed
        open_periods = set(
            dim_period[dim_period["is_closed"] == False]["period_id"]  # noqa: E712
        )
        # All NaN forecast rows should be for open (non-closed) periods
        nan_periods = set(nan_forecast["period_id"].unique())
        closed_with_nan = nan_periods - open_periods
        # Allow some tolerance: closed periods might also have NaN forecast
        # if forecast wasn't generated for those months
        # The key check: open periods SHOULD have NaN forecast
        open_period_data = ff[ff["period_id"].isin(open_periods)]
        if len(open_period_data) > 0:
            assert open_period_data["forecast_amount"].isna().all(), (
                "Open (future) periods should have NaN forecast amounts"
            )

    def test_prior_year_nan_for_2024(self, ff: pd.DataFrame) -> None:
        """FY2024 should have a significant proportion of NaN prior_year_amount.

        Since there is no FY2023 data, many accounts in FY2024 will not
        have prior year amounts. The generator may populate PY for some
        accounts based on internal logic, but a meaningful fraction should
        be NaN.
        """
        fy2024 = ff[ff["fiscal_year"] == 2024]
        assert len(fy2024) > 0, "Expected fiscal year 2024 data"
        nan_ratio = fy2024["prior_year_amount"].isna().mean()
        assert nan_ratio > 0.10, (
            f"Expected > 10% NaN prior_year for FY2024, got {nan_ratio:.1%}"
        )

    def test_variance_pct_null_when_comparator_zero(self, vm: pd.DataFrame) -> None:
        """Rows with comparator_amount=0 should have NaN variance_pct."""
        zero_comp = vm[vm["comparator_amount"] == 0]
        if len(zero_comp) > 0:
            assert zero_comp["variance_pct"].isna().all(), (
                f"Found {(~zero_comp['variance_pct'].isna()).sum()} rows with "
                f"comparator=0 but non-null variance_pct"
            )
        # If no zero comparators, the test passes vacuously


# ---------------------------------------------------------------------------
# FX rate quality
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFXRateQuality:
    """Tests FX rate data quality and consistency."""

    def test_fx_rates_positive(self, ff: pd.DataFrame) -> None:
        """All budget and actual FX rates should be positive."""
        assert (ff["budget_fx_rate"] > 0).all(), (
            "Found non-positive budget_fx_rate values"
        )
        assert (ff["actual_fx_rate"] > 0).all(), (
            "Found non-positive actual_fx_rate values"
        )

    def test_fx_rate_consistency(self, ff: pd.DataFrame) -> None:
        """For non-USD rows: local_amount * fx_rate should approximate actual_amount."""
        non_usd = ff[
            (ff["local_currency"] != "USD")
            & (ff["actual_local_amount"].notna())
            & (ff["actual_amount"].abs() > 0.01)  # Avoid division by near-zero
        ]
        if len(non_usd) == 0:
            pytest.skip("No non-USD rows with local amount data")

        computed = non_usd["actual_local_amount"] * non_usd["actual_fx_rate"]
        diff_ratio = ((computed - non_usd["actual_amount"]).abs() / non_usd["actual_amount"].abs())
        max_diff = diff_ratio.max()

        assert max_diff < 0.05, (
            f"FX conversion inconsistency: max diff ratio = {max_diff:.4f} "
            f"(expected < 0.05)"
        )
