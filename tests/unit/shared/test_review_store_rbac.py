"""Unit tests for ReviewStore RBAC filtering parameters.

Tests the ReviewStore's allowed_statuses and bu_scope filtering directly
at the DataFrame level, without FastAPI or HTTP. Verifies backward
compatibility when no RBAC params are passed.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

import pandas as pd

from shared.data.review_store import ReviewStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_review_status_df() -> pd.DataFrame:
    """Create a test fact_review_status DataFrame with varied statuses and BUs."""
    return pd.DataFrame([
        {"variance_id": "V001", "status": "AI_DRAFT", "created_at": "2026-01-15T10:00:00"},
        {"variance_id": "V002", "status": "AI_DRAFT", "created_at": "2026-01-15T11:00:00"},
        {"variance_id": "V003", "status": "ANALYST_REVIEWED", "created_at": "2026-01-14T08:00:00"},
        {"variance_id": "V004", "status": "APPROVED", "created_at": "2026-01-13T09:00:00"},
        {"variance_id": "V005", "status": "ESCALATED", "created_at": "2026-01-12T07:00:00"},
        {"variance_id": "V006", "status": "DISMISSED", "created_at": "2026-01-11T06:00:00"},
        {"variance_id": "V007", "status": "ANALYST_REVIEWED", "created_at": "2026-01-10T05:00:00"},
    ])


def _make_variance_material_df() -> pd.DataFrame:
    """Create a test fact_variance_material DataFrame matching the review records."""
    return pd.DataFrame([
        {"variance_id": "V001", "account_id": "acct_rev", "period_id": "2026-01", "bu_id": "BU_NORTH", "variance_amount": 50000, "variance_pct": 5.0, "narrative_oneliner": "Rev up"},
        {"variance_id": "V002", "account_id": "acct_cogs", "period_id": "2026-01", "bu_id": "BU_SOUTH", "variance_amount": -30000, "variance_pct": -3.0, "narrative_oneliner": "COGS up"},
        {"variance_id": "V003", "account_id": "acct_opex", "period_id": "2026-01", "bu_id": "BU_NORTH", "variance_amount": 20000, "variance_pct": 2.5, "narrative_oneliner": "OpEx fav"},
        {"variance_id": "V004", "account_id": "acct_rev2", "period_id": "2026-01", "bu_id": "BU_EAST", "variance_amount": 80000, "variance_pct": 8.0, "narrative_oneliner": "Rev strong"},
        {"variance_id": "V005", "account_id": "acct_cogs2", "period_id": "2026-01", "bu_id": "BU_WEST", "variance_amount": -15000, "variance_pct": -1.5, "narrative_oneliner": "Escalated"},
        {"variance_id": "V006", "account_id": "acct_opex2", "period_id": "2026-01", "bu_id": "BU_SOUTH", "variance_amount": 5000, "variance_pct": 0.5, "narrative_oneliner": "Dismissed"},
        {"variance_id": "V007", "account_id": "acct_rev3", "period_id": "2026-02", "bu_id": "BU_NORTH", "variance_amount": 40000, "variance_pct": 4.0, "narrative_oneliner": "Feb rev"},
    ])


def _create_store() -> ReviewStore:
    """Create a ReviewStore with mocked __init__ and injected test data."""
    with patch.object(ReviewStore, "__init__", lambda self, *a, **kw: None):
        store = ReviewStore.__new__(ReviewStore)
        store._review_status = _make_review_status_df()
        store._variance_material = _make_variance_material_df()
        # Ensure required columns exist (mimicking real __init__)
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
class TestReviewStoreQueueRBAC:
    """Test ReviewStore.get_review_queue with RBAC parameters."""

    def test_get_review_queue_filters_by_allowed_statuses(self):
        """Only rows matching allowed_statuses are returned."""
        store = _create_store()
        result = store.get_review_queue(allowed_statuses=["APPROVED"])
        assert result["total"] == 1
        assert all(
            item["current_status"] == "APPROVED"
            for item in result["items"]
        )

    def test_get_review_queue_filters_by_bu_scope(self):
        """Only rows matching bu_scope are returned."""
        store = _create_store()
        result = store.get_review_queue(bu_scope=["BU_NORTH"])
        # V001 (NORTH), V003 (NORTH), V007 (NORTH) = 3 items
        assert result["total"] == 3
        for item in result["items"]:
            vid = item["variance_id"]
            assert vid in ("V001", "V003", "V007"), f"Unexpected {vid} in BU_NORTH scope"

    def test_get_review_queue_combined_rbac_and_status_filter(self):
        """allowed_statuses + status_filter + bu_scope all combine."""
        store = _create_store()
        result = store.get_review_queue(
            allowed_statuses=["AI_DRAFT", "ANALYST_REVIEWED"],
            bu_scope=["BU_NORTH"],
            status_filter="AI_DRAFT",
        )
        # BU_NORTH + AI_DRAFT = V001 only
        assert result["total"] == 1
        assert result["items"][0]["variance_id"] == "V001"

    def test_get_review_queue_no_rbac_returns_all(self):
        """When no RBAC params are passed, all items are returned (backward compat)."""
        store = _create_store()
        result = store.get_review_queue()
        assert result["total"] == 7  # All 7 records


# ---------------------------------------------------------------------------
# Tests — Approval Queue
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestReviewStoreApprovalRBAC:
    """Test ReviewStore.get_approval_queue with RBAC parameters."""

    def test_get_approval_queue_custom_allowed_statuses(self):
        """Approval queue filters to only the provided allowed_statuses."""
        store = _create_store()
        result = store.get_approval_queue(allowed_statuses=["APPROVED"])
        assert result["total"] == 1
        assert result["items"][0]["variance_id"] == "V004"

    def test_get_approval_queue_bu_scope(self):
        """Approval queue respects bu_scope filter."""
        store = _create_store()
        # Default approval queue shows ANALYST_REVIEWED. V003=NORTH, V007=NORTH
        result = store.get_approval_queue(bu_scope=["BU_NORTH"])
        for item in result["items"]:
            vid = item["variance_id"]
            assert vid in ("V003", "V007"), f"Unexpected {vid} in BU_NORTH approval scope"


# ---------------------------------------------------------------------------
# Tests — Review Stats
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestReviewStoreStatsRBAC:
    """Test ReviewStore.get_review_stats with RBAC parameters."""

    def test_get_review_stats_filtered_by_persona(self):
        """Stats are computed only from persona-allowed statuses."""
        store = _create_store()
        # Simulate CFO: only APPROVED
        stats = store.get_review_stats(allowed_statuses=["APPROVED"])
        assert stats["approved"] == 1
        assert stats["ai_draft"] == 0
        assert stats["analyst_reviewed"] == 0
        assert stats["total_pending"] == 0

    def test_get_review_stats_filtered_by_bu_scope(self):
        """Stats are filtered by BU scope via variance_material join."""
        store = _create_store()
        # BU_SOUTH has V002 (AI_DRAFT) and V006 (DISMISSED)
        stats = store.get_review_stats(bu_scope=["BU_SOUTH"])
        assert stats["ai_draft"] == 1
        assert stats["dismissed"] == 1
        assert stats["approved"] == 0
