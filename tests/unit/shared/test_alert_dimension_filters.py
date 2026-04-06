"""Tests for dimension filtering on netting and trend alerts in DataService.

Verifies that the new dimension columns (geo_node_id, segment_node_id, etc.)
are used for filtering instead of being silently ignored.
"""

import pandas as pd
import pytest

from shared.data.service import DataService


@pytest.fixture
def ds_with_alerts(tmp_path):
    """Create a DataService with mock netting and trend data that has dimension columns."""
    # Mock fact_netting_flags with dimension columns
    netting = pd.DataFrame([
        {
            "netting_id": "n1", "parent_node_id": "acct_revenue",
            "parent_dimension": "account", "check_type": "gross_offset",
            "net_variance": 500, "gross_variance": 160000, "netting_ratio": 320,
            "child_details": [{"account_id": "acct_a", "variance_amount": 80000}, {"account_id": "acct_b", "variance_amount": -79500}],
            "period_id": "2026-06", "bu_id": "marsh", "geo_node_id": "americas",
            "segment_node_id": "commercial", "lob_node_id": "property",
            "costcenter_node_id": "cc_sales", "created_at": "2026-06-01",
        },
        {
            "netting_id": "n2", "parent_node_id": "acct_opex",
            "parent_dimension": "account", "check_type": "gross_offset",
            "net_variance": 200, "gross_variance": 90000, "netting_ratio": 450,
            "child_details": [{"account_id": "acct_c", "variance_amount": 45000}, {"account_id": "acct_d", "variance_amount": -44800}],
            "period_id": "2026-06", "bu_id": "mercer", "geo_node_id": "emea",
            "segment_node_id": "institutional", "lob_node_id": "investments",
            "costcenter_node_id": "cc_ops", "created_at": "2026-06-01",
        },
    ])

    # Mock fact_trend_flags with dimension columns
    trends = pd.DataFrame([
        {
            "trend_id": "t1", "account_id": "acct_consulting",
            "dimension_key": "acct_consulting|marsh|cc_sales|americas|commercial|property",
            "rule_type": "consecutive_direction", "consecutive_periods": 4,
            "cumulative_amount": -50000, "direction": "decreasing",
            "period_details": [{"period_id": "2026-03"}, {"period_id": "2026-04"}, {"period_id": "2026-05"}, {"period_id": "2026-06"}],
            "bu_id": "marsh", "geo_node_id": "americas", "segment_node_id": "commercial",
            "lob_node_id": "property", "costcenter_node_id": "cc_sales",
            "latest_period_id": "2026-06", "created_at": "2026-06-01",
        },
        {
            "trend_id": "t2", "account_id": "acct_advisory",
            "dimension_key": "acct_advisory|mercer|cc_ops|emea|institutional|investments",
            "rule_type": "consecutive_direction", "consecutive_periods": 3,
            "cumulative_amount": 30000, "direction": "increasing",
            "period_details": [{"period_id": "2026-04"}, {"period_id": "2026-05"}, {"period_id": "2026-06"}],
            "bu_id": "mercer", "geo_node_id": "emea", "segment_node_id": "institutional",
            "lob_node_id": "investments", "costcenter_node_id": "cc_ops",
            "latest_period_id": "2026-06", "created_at": "2026-06-01",
        },
    ])

    # Create minimal DataService with injected tables
    ds = DataService.__new__(DataService)
    ds._tables = {
        "fact_netting_flags": netting,
        "fact_trend_flags": trends,
        "fact_variance_material": pd.DataFrame(),
        "dim_account": pd.DataFrame(),
        "dim_hierarchy": pd.DataFrame(),
    }
    ds._account_lookup = {
        "acct_consulting": {"account_name": "Consulting Fees"},
        "acct_advisory": {"account_name": "Advisory Fees"},
    }
    ds._hierarchy_cache = {}
    return ds


class TestNettingAlertDimensionFilters:
    """Test that netting alerts filter by dimension columns."""

    def test_filter_by_bu_id(self, ds_with_alerts):
        alerts = ds_with_alerts.get_netting_alerts("2026-06", bu_id="marsh")
        assert len(alerts) == 1  # Only marsh netting alert

    def test_filter_by_geo_node_id(self, ds_with_alerts):
        alerts = ds_with_alerts.get_netting_alerts("2026-06", geo_node_id="americas")
        assert len(alerts) == 1  # Only americas

    def test_no_filter_returns_all(self, ds_with_alerts):
        alerts = ds_with_alerts.get_netting_alerts("2026-06")
        assert len(alerts) == 2


class TestTrendAlertDimensionFilters:
    """Test that trend alerts filter by dimension columns."""

    def test_filter_by_bu_id(self, ds_with_alerts):
        alerts = ds_with_alerts.get_trend_alerts(bu_id="mercer")
        assert len(alerts) == 1
        assert alerts[0]["description"].startswith("Advisory Fees")

    def test_filter_by_geo_node_id(self, ds_with_alerts):
        alerts = ds_with_alerts.get_trend_alerts(geo_node_id="emea")
        assert len(alerts) == 1

    def test_filter_by_period(self, ds_with_alerts):
        # Both trends touch 2026-06, so both should show
        alerts = ds_with_alerts.get_trend_alerts(period_id="2026-06")
        assert len(alerts) == 2

    def test_filter_by_old_period(self, ds_with_alerts):
        # Only t1 (marsh) has periods starting from 2026-03
        # latest_period_id >= "2026-03" means both qualify
        alerts = ds_with_alerts.get_trend_alerts(period_id="2026-03")
        assert len(alerts) == 2

    def test_no_filter_returns_all(self, ds_with_alerts):
        alerts = ds_with_alerts.get_trend_alerts()
        assert len(alerts) == 2
