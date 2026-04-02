"""Integration tests for fiscal-year-scoped review queue.

Validates that the review queue can be filtered by fiscal year,
and that period_id is correctly populated in review status data.
"""

import pytest
from shared.data.review_store import ReviewStore


@pytest.fixture(scope="module")
def store() -> ReviewStore:
    """ReviewStore loaded with current data."""
    return ReviewStore()


@pytest.mark.integration
class TestFYScopedReview:
    """Tests for fiscal year filtering in review queue."""

    def test_review_queue_returns_all_without_fy(self, store):
        """Without fiscal_year filter, returns all items."""
        result = store.get_review_queue(page_size=10)
        assert result["total"] > 0

    def test_review_queue_filters_by_fy_2026(self, store):
        """With fiscal_year=2026, returns only 2026 items."""
        result = store.get_review_queue(fiscal_year=2026, page_size=10)
        total_all = store.get_review_queue(page_size=1)["total"]

        # 2026 should be a subset of all
        assert result["total"] > 0, "Should have 2026 items"
        assert result["total"] < total_all, "2026 should be fewer than all years"

        # Verify all returned items have 2026 period
        for item in result["items"]:
            period = item.get("period_id", "")
            if period:
                assert period.startswith("2026"), f"Expected 2026 period, got {period}"

    def test_review_queue_filters_by_fy_2025(self, store):
        """With fiscal_year=2025, returns only 2025 items."""
        result = store.get_review_queue(fiscal_year=2025, page_size=10)
        assert result["total"] > 0, "Should have 2025 items"

        for item in result["items"]:
            period = item.get("period_id", "")
            if period:
                assert period.startswith("2025"), f"Expected 2025 period, got {period}"

    def test_review_queue_empty_for_invalid_fy(self, store):
        """With a future fiscal year, returns empty."""
        result = store.get_review_queue(fiscal_year=2030, page_size=10)
        assert result["total"] == 0

    def test_review_status_parquet_has_period(self):
        """fact_review_status.parquet should contain period_id column."""
        import pandas as pd
        rs = pd.read_parquet("data/output/fact_review_status.parquet")
        assert "period_id" in rs.columns, "period_id column missing from review status"
        assert rs["period_id"].notna().sum() > 0, "period_id should be populated"

    def test_review_status_parquet_has_fiscal_year(self):
        """fact_review_status.parquet should contain fiscal_year column."""
        import pandas as pd
        rs = pd.read_parquet("data/output/fact_review_status.parquet")
        assert "fiscal_year" in rs.columns, "fiscal_year column missing from review status"
        assert set(rs["fiscal_year"].dropna().unique()) == {2025, 2026}, \
            f"Expected FY 2025+2026, got {rs['fiscal_year'].dropna().unique()}"
