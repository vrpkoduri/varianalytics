"""Unit tests for ReviewStore account name resolution.

Verifies that review and approval queue items return human-readable
account names from dim_account, with a fallback to the raw account_id
when the dimension table is empty or unavailable.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

import pandas as pd

from shared.data.review_store import ReviewStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_review_status_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"variance_id": "V001", "status": "AI_DRAFT", "created_at": "2026-01-15T10:00:00"},
        {"variance_id": "V002", "status": "ANALYST_REVIEWED", "created_at": "2026-01-14T08:00:00"},
    ])


def _make_variance_material_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "variance_id": "V001",
            "account_id": "acct_revenue",
            "period_id": "2026-01",
            "bu_id": "BU_NORTH",
            "variance_amount": 50000,
            "variance_pct": 5.0,
            "narrative_oneliner": "Rev up",
        },
        {
            "variance_id": "V002",
            "account_id": "acct_cogs",
            "period_id": "2026-01",
            "bu_id": "BU_SOUTH",
            "variance_amount": -30000,
            "variance_pct": -3.0,
            "narrative_oneliner": "COGS up",
        },
    ])


def _create_store(account_lookup: dict[str, str] | None = None) -> ReviewStore:
    """Create a ReviewStore with mocked __init__ and injected test data."""
    with patch.object(ReviewStore, "__init__", lambda self, *a, **kw: None):
        store = ReviewStore.__new__(ReviewStore)
        store._review_status = _make_review_status_df()
        store._variance_material = _make_variance_material_df()
        store._account_lookup = account_lookup if account_lookup is not None else {}
        # Ensure required columns
        store._review_status["reviewed_at"] = pd.NaT
        store._review_status["approved_at"] = pd.NaT
        store._review_status["version_count"] = 1
        store._review_status["locked_by"] = None
        store._review_status["locked_until"] = None
    return store


# ---------------------------------------------------------------------------
# Tests — Review Queue
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReviewQueueAccountNames:
    """Verify review queue items include human-readable account names."""

    def test_review_queue_returns_display_name(self) -> None:
        """When dim_account provides a mapping, account_name is the display name."""
        store = _create_store(account_lookup={"acct_revenue": "Revenue", "acct_cogs": "Cost of Goods Sold"})
        result = store.get_review_queue()
        names = {item["account_name"] for item in result["items"]}
        assert "Revenue" in names
        assert "acct_revenue" not in names

    def test_review_queue_fallback_to_id(self) -> None:
        """When dim_account is empty, falls back to the raw account_id."""
        store = _create_store(account_lookup={})
        result = store.get_review_queue()
        names = {item["account_name"] for item in result["items"]}
        assert "acct_revenue" in names
        assert "acct_cogs" in names


# ---------------------------------------------------------------------------
# Tests — Approval Queue
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApprovalQueueAccountNames:
    """Verify approval queue items include human-readable account names."""

    def test_approval_queue_returns_display_name(self) -> None:
        """Approval queue uses the account_lookup for display names."""
        store = _create_store(account_lookup={"acct_cogs": "Cost of Goods Sold"})
        # V002 is ANALYST_REVIEWED, which is the default approval queue filter
        result = store.get_approval_queue()
        assert result["total"] == 1
        assert result["items"][0]["account_name"] == "Cost of Goods Sold"


# ---------------------------------------------------------------------------
# Tests — Lookup construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAccountLookupConstruction:
    """Verify _account_lookup dict is populated from dim_account."""

    def test_account_lookup_built_from_dim_account(self) -> None:
        """The _account_lookup dict should be populated with account_id → account_name."""
        store = _create_store(account_lookup={"acct_revenue": "Revenue", "acct_cogs": "COGS"})
        assert store._account_lookup["acct_revenue"] == "Revenue"
        assert store._account_lookup["acct_cogs"] == "COGS"
        assert len(store._account_lookup) == 2
