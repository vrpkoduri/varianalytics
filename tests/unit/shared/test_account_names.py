"""Unit tests for account name resolution and period has_data flag.

Covers the get_trend_alerts canonical account name lookup,
the get_netting_alerts child account name extraction, and
the get_periods has_data flag in DataService.
"""

from __future__ import annotations

import json
from typing import Optional

import pytest
from unittest.mock import patch, MagicMock

import pandas as pd

from shared.data.service import DataService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_service(
    tables: Optional[dict] = None,
    account_lookup: Optional[dict] = None,
) -> DataService:
    """Create a DataService with mocked __init__ and injected test data."""
    with patch.object(DataService, "__init__", lambda self, *a, **kw: None):
        svc = DataService.__new__(DataService)
        svc._tables = tables or {}
        svc._account_lookup = account_lookup or {}
        svc._account_children = {}
        svc._graph_cache = {}
        svc._data_dir = "data/output"
        svc._loader = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# Tests — Trend Alerts Account Names
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTrendAlertsAccountName:
    """Test that get_trend_alerts uses canonical account names from dim_account."""

    def test_trend_alerts_uses_canonical_account_name(self):
        """When dim_account has the account, use its account_name."""
        svc = _create_service(
            tables={
                "fact_trend_flags": pd.DataFrame([
                    {
                        "account_id": "acct_cloud_hosting",
                        "consecutive_periods": 4,
                        "direction": "increasing",
                        "cumulative_amount": 120000,
                    },
                ]),
            },
            account_lookup={
                "acct_cloud_hosting": {"account_name": "Cloud Hosting & Infrastructure"},
            },
        )

        alerts = svc.get_trend_alerts(limit=5)
        assert len(alerts) == 1
        assert "Cloud Hosting & Infrastructure" in alerts[0]["description"]

    def test_trend_alerts_falls_back_to_title_case(self):
        """When dim_account lookup misses, fall back to title-cased account_id."""
        svc = _create_service(
            tables={
                "fact_trend_flags": pd.DataFrame([
                    {
                        "account_id": "acct_travel_expenses",
                        "consecutive_periods": 3,
                        "direction": "decreasing",
                        "cumulative_amount": -45000,
                    },
                ]),
            },
            account_lookup={},  # No match
        )

        alerts = svc.get_trend_alerts(limit=5)
        assert len(alerts) == 1
        # Fallback: acct_travel_expenses -> "Travel Expenses"
        assert "Travel Expenses" in alerts[0]["description"]


# ---------------------------------------------------------------------------
# Tests — Netting Alerts Account Names
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestNettingAlertsAccountName:
    """Test that get_netting_alerts extracts child account names."""

    def test_netting_alerts_uses_child_account_name(self):
        """Netting alerts extract account_name from child_details."""
        child_details = [
            {"account_id": "acct_rev_na", "account_name": "Revenue North America", "variance_amount": 80000},
            {"account_id": "acct_rev_eu", "account_name": "Revenue Europe", "variance_amount": -60000},
        ]
        svc = _create_service(
            tables={
                "fact_netting_flags": pd.DataFrame([
                    {
                        "period_id": "2026-01",
                        "gross_variance": 140000,
                        "net_variance": 20000,
                        "netting_ratio": 0.86,
                        "child_details": json.dumps(child_details),
                    },
                ]),
            },
        )

        alerts = svc.get_netting_alerts(period_id="2026-01", limit=5)
        assert len(alerts) == 1
        assert "Revenue North America" in alerts[0]["left"]
        assert "Revenue Europe" in alerts[0]["right"]


# ---------------------------------------------------------------------------
# Tests — Periods has_data Flag
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPeriodsHasDataFlag:
    """Test the get_periods has_data flag based on fact_variance_material."""

    def test_get_periods_has_data_flag_true(self):
        """Period with rows in fact_variance_material gets has_data=True."""
        svc = _create_service(
            tables={
                "dim_period": pd.DataFrame([
                    {"period_id": "2026-01", "period_label": "Jan 2026"},
                    {"period_id": "2026-02", "period_label": "Feb 2026"},
                ]),
                "fact_variance_material": pd.DataFrame([
                    {"period_id": "2026-01", "variance_id": "V001"},
                ]),
            },
        )

        periods = svc.get_periods()
        jan = next(p for p in periods if p["period_id"] == "2026-01")
        assert jan["has_data"] is True

    def test_get_periods_has_data_flag_false(self):
        """Period without rows in fact_variance_material gets has_data=False."""
        svc = _create_service(
            tables={
                "dim_period": pd.DataFrame([
                    {"period_id": "2026-01", "period_label": "Jan 2026"},
                    {"period_id": "2026-02", "period_label": "Feb 2026"},
                ]),
                "fact_variance_material": pd.DataFrame([
                    {"period_id": "2026-01", "variance_id": "V001"},
                ]),
            },
        )

        periods = svc.get_periods()
        feb = next(p for p in periods if p["period_id"] == "2026-02")
        assert feb["has_data"] is False

    def test_get_periods_empty_table(self):
        """Empty dim_period table returns empty list."""
        svc = _create_service(
            tables={
                "dim_period": pd.DataFrame(),
                "fact_variance_material": pd.DataFrame(),
            },
        )

        periods = svc.get_periods()
        assert periods == []
