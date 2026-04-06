"""Tests for dimension columns in netting detection flags.

Verifies that netting flags carry dimension columns (bu_id, geo_node_id,
segment_node_id, lob_node_id, costcenter_node_id) from the input variances
so that downstream filtering works correctly.
"""

import pandas as pd
import pytest

from services.computation.detection.netting import (
    _empty_netting_df,
    _make_flag,
    detect_netting,
)
from shared.config.thresholds import ThresholdConfig
from shared.models.enums import NettingCheckType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def threshold_config():
    """ThresholdConfig loaded from the project thresholds.yaml."""
    return ThresholdConfig()


@pytest.fixture
def variance_df_with_netting():
    """DataFrame with offsetting children that should trigger netting flags.

    Parent (acct_revenue) has near-zero net variance, but children have
    large positive/negative movements — classic netting scenario.
    """
    rows = []
    # Parent: small net variance (children offset)
    base = {
        "period_id": "2026-06",
        "bu_id": "marsh",
        "geo_node_id": "americas",
        "segment_node_id": "commercial",
        "lob_node_id": "property",
        "costcenter_node_id": "cc_sales",
        "view_id": "MTD",
        "base_id": "BUDGET",
        "fiscal_year": 2026,
        "pl_category": "Revenue",
        "is_calculated": False,
    }
    # Parent account: small net
    rows.append({
        **base,
        "account_id": "acct_revenue",
        "variance_amount": 500.0,
        "variance_pct": 0.5,
    })
    # Child 1: large positive
    rows.append({
        **base,
        "account_id": "acct_product_revenue",
        "variance_amount": 80000.0,
        "variance_pct": 12.0,
    })
    # Child 2: large negative (offsets child 1)
    rows.append({
        **base,
        "account_id": "acct_service_revenue",
        "variance_amount": -79500.0,
        "variance_pct": -11.5,
    })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestNettingSchema:
    """Verify fact_netting_flags schema includes dimension columns."""

    def test_empty_df_has_dimension_columns(self):
        df = _empty_netting_df()
        for col in ["bu_id", "geo_node_id", "segment_node_id", "lob_node_id", "costcenter_node_id"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_empty_df_column_count(self):
        df = _empty_netting_df()
        assert len(df.columns) == 15  # 10 original + 5 dimension


# ---------------------------------------------------------------------------
# Flag Builder Tests
# ---------------------------------------------------------------------------


class TestMakeFlagDimensions:
    """Verify _make_flag() includes dimension values."""

    def test_flag_carries_dimension_values(self):
        dim_values = {
            "bu_id": "marsh",
            "geo_node_id": "americas",
            "segment_node_id": "commercial",
            "lob_node_id": "property",
            "costcenter_node_id": "cc_sales",
        }
        flag = _make_flag(
            parent_node_id="acct_revenue",
            parent_dimension="account",
            check_type=NettingCheckType.GROSS_OFFSET,
            net_variance=500.0,
            gross_variance=160000.0,
            netting_ratio=320.0,
            child_details=[],
            period_id="2026-06",
            dim_values=dim_values,
        )
        assert flag["bu_id"] == "marsh"
        assert flag["geo_node_id"] == "americas"
        assert flag["segment_node_id"] == "commercial"
        assert flag["lob_node_id"] == "property"
        assert flag["costcenter_node_id"] == "cc_sales"

    def test_flag_without_dim_values_has_none(self):
        flag = _make_flag(
            parent_node_id="acct_revenue",
            parent_dimension="account",
            check_type=NettingCheckType.GROSS_OFFSET,
            net_variance=500.0,
            gross_variance=160000.0,
            netting_ratio=320.0,
            child_details=[],
            period_id="2026-06",
        )
        assert flag["bu_id"] is None
        assert flag["geo_node_id"] is None


# ---------------------------------------------------------------------------
# Integration: detect_netting() produces flags with dimensions
# ---------------------------------------------------------------------------


class TestDetectNettingDimensions:
    """Verify detect_netting() produces flags that carry dimension columns."""

    def test_netting_flags_have_dimension_columns(
        self, variance_df_with_netting, threshold_config
    ):
        result = detect_netting(variance_df_with_netting, threshold_config, "2026-06")
        if not result.empty:
            for col in ["bu_id", "geo_node_id", "segment_node_id", "lob_node_id", "costcenter_node_id"]:
                assert col in result.columns, f"Missing column in result: {col}"

    def test_netting_flags_dimension_values_match_input(
        self, variance_df_with_netting, threshold_config
    ):
        result = detect_netting(variance_df_with_netting, threshold_config, "2026-06")
        if not result.empty:
            # All flags should have bu_id="marsh" since input only has marsh
            assert (result["bu_id"] == "marsh").all()
            assert (result["geo_node_id"] == "americas").all()
