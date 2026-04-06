"""Tests for trend period anchoring in DataService.get_trends().

Verifies that when period_id is provided, the trailing window ends at that
period instead of always showing the latest N periods.
"""

import pandas as pd
import pytest

from shared.data.service import DataService


@pytest.fixture
def ds_with_trend_data():
    """Create DataService with 24 months of variance data."""
    rows = []
    for month in range(1, 13):
        for year in [2025, 2026]:
            rows.append({
                "variance_id": f"v_{year}_{month:02d}",
                "period_id": f"{year}-{month:02d}",
                "account_id": "acct_gross_revenue",
                "bu_id": "marsh",
                "view_id": "MTD",
                "base_id": "BUDGET",
                "actual_amount": 100000 + month * 1000 + (year - 2025) * 12000,
                "comparator_amount": 95000 + month * 800 + (year - 2025) * 11000,
                "variance_amount": 5000 + month * 200 + (year - 2025) * 1000,
                "variance_pct": 5.0,
                "geo_node_id": "americas",
                "segment_node_id": "commercial",
                "lob_node_id": "property",
                "costcenter_node_id": "cc_sales",
                "is_material": True,
                "is_calculated": False,
            })

    ds = DataService.__new__(DataService)
    ds._tables = {
        "fact_variance_material": pd.DataFrame(rows),
        "dim_hierarchy": pd.DataFrame(),
    }
    ds._hierarchy_cache = {}
    ds._account_lookup = {}
    return ds


class TestTrendAnchoring:
    """Verify trends anchor to selected period."""

    def test_no_period_shows_latest_12(self, ds_with_trend_data):
        result = ds_with_trend_data.get_trends(periods=12)
        assert len(result) == 12
        # Should end at 2026-12 (latest)
        assert result[-1]["period_id"] == "2026-12"

    def test_anchor_to_2026_03(self, ds_with_trend_data):
        result = ds_with_trend_data.get_trends(period_id="2026-03", periods=12)
        assert len(result) == 12
        # Should end at 2026-03 (anchor)
        assert result[-1]["period_id"] == "2026-03"
        # Should start at 2025-04
        assert result[0]["period_id"] == "2025-04"

    def test_anchor_to_2025_06(self, ds_with_trend_data):
        result = ds_with_trend_data.get_trends(period_id="2025-06", periods=6)
        assert len(result) == 6
        assert result[-1]["period_id"] == "2025-06"
        assert result[0]["period_id"] == "2025-01"

    def test_anchor_with_fewer_periods_than_requested(self, ds_with_trend_data):
        # Only 3 months available before 2025-03
        result = ds_with_trend_data.get_trends(period_id="2025-03", periods=12)
        assert len(result) == 3
        assert result[-1]["period_id"] == "2025-03"
