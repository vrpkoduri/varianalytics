"""Tests for dimension columns in trend detection flags.

Verifies that trend flags carry individual dimension columns (bu_id, geo_node_id,
segment_node_id, lob_node_id, costcenter_node_id) and latest_period_id
extracted from the dimension group key.
"""

import pandas as pd
import pytest

from services.computation.detection.trend import (
    _empty_trend_df,
    _make_consecutive_flag,
    detect_trends,
)
from shared.config.thresholds import ThresholdConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def threshold_config():
    return ThresholdConfig()


@pytest.fixture
def variance_df_with_trend():
    """DataFrame with 4 consecutive negative MTD/BUDGET variances for one key.

    This should trigger Rule 1 (consecutive direction) with min_consecutive=3.
    """
    rows = []
    base = {
        "bu_id": "mercer",
        "geo_node_id": "emea",
        "segment_node_id": "institutional",
        "lob_node_id": "investments",
        "costcenter_node_id": "cc_ops",
        "view_id": "MTD",
        "base_id": "BUDGET",
        "pl_category": "Revenue",
        "is_calculated": False,
        "fiscal_year": 2026,
    }
    for i, period in enumerate(["2026-03", "2026-04", "2026-05", "2026-06"]):
        rows.append({
            **base,
            "account_id": "acct_consulting",
            "period_id": period,
            "variance_amount": -5000.0 * (i + 1),  # -5K, -10K, -15K, -20K
            "variance_pct": -2.0 * (i + 1),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestTrendSchema:
    """Verify fact_trend_flags schema includes dimension columns."""

    def test_empty_df_has_dimension_columns(self):
        df = _empty_trend_df()
        for col in ["bu_id", "geo_node_id", "segment_node_id",
                     "lob_node_id", "costcenter_node_id", "latest_period_id"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_empty_df_column_count(self):
        df = _empty_trend_df()
        assert len(df.columns) == 15  # 9 original + 5 dimension + 1 latest_period_id


# ---------------------------------------------------------------------------
# Flag Builder Tests
# ---------------------------------------------------------------------------


class TestMakeConsecutiveFlagDimensions:
    """Verify _make_consecutive_flag() includes dimension values."""

    def test_flag_carries_dimension_values(self):
        dim_values = {
            "account_id": "acct_consulting",
            "bu_id": "mercer",
            "geo_node_id": "emea",
            "segment_node_id": "institutional",
            "lob_node_id": "investments",
            "costcenter_node_id": "cc_ops",
        }
        flag = _make_consecutive_flag(
            account_id="acct_consulting",
            dimension_key="acct_consulting|mercer|cc_ops|emea|institutional|investments",
            periods=["2026-03", "2026-04", "2026-05"],
            amounts=[-5000.0, -10000.0, -15000.0],
            sign=-1,
            dim_values=dim_values,
        )
        assert flag["bu_id"] == "mercer"
        assert flag["geo_node_id"] == "emea"
        assert flag["segment_node_id"] == "institutional"
        assert flag["lob_node_id"] == "investments"
        assert flag["costcenter_node_id"] == "cc_ops"
        assert flag["latest_period_id"] == "2026-05"

    def test_flag_without_dim_values_has_none(self):
        flag = _make_consecutive_flag(
            account_id="acct_consulting",
            dimension_key="acct_consulting|mercer",
            periods=["2026-03", "2026-04", "2026-05"],
            amounts=[-5000.0, -10000.0, -15000.0],
            sign=-1,
        )
        assert flag["bu_id"] is None
        assert flag["geo_node_id"] is None
        assert flag["latest_period_id"] == "2026-05"


# ---------------------------------------------------------------------------
# Integration: detect_trends() produces flags with dimensions
# ---------------------------------------------------------------------------


class TestDetectTrendsDimensions:
    """Verify detect_trends() produces flags with dimension columns."""

    def test_trend_flags_have_dimension_columns(
        self, variance_df_with_trend, threshold_config
    ):
        result = detect_trends(variance_df_with_trend, threshold_config)
        if not result.empty:
            for col in ["bu_id", "geo_node_id", "segment_node_id",
                         "lob_node_id", "costcenter_node_id", "latest_period_id"]:
                assert col in result.columns, f"Missing column: {col}"

    def test_trend_flags_dimension_values_match_input(
        self, variance_df_with_trend, threshold_config
    ):
        result = detect_trends(variance_df_with_trend, threshold_config)
        if not result.empty:
            assert (result["bu_id"] == "mercer").all()
            assert (result["geo_node_id"] == "emea").all()
            assert (result["segment_node_id"] == "institutional").all()

    def test_trend_flags_latest_period_id(
        self, variance_df_with_trend, threshold_config
    ):
        result = detect_trends(variance_df_with_trend, threshold_config)
        if not result.empty:
            # Latest period should be 2026-06 (last in the consecutive streak)
            assert (result["latest_period_id"] == "2026-06").all()
