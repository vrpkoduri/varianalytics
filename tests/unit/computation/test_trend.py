"""Unit tests for trend detection — 2 MVP rules.

Tests consecutive-direction detection and cumulative YTD breach logic
using small hand-crafted DataFrames.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from services.computation.detection.trend import (
    _check_consecutive_direction,
    _check_cumulative_ytd_breach,
    detect_trends,
)
from shared.config.thresholds import ThresholdConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def threshold_config() -> ThresholdConfig:
    """Load the standard threshold config from the project YAML."""
    return ThresholdConfig()


def _make_trend_series(
    amounts: list[float],
    periods: list[str] | None = None,
    fiscal_year: int = 2026,
    comparator_amount: float = 100_000,
) -> pd.DataFrame:
    """Build a minimal sorted variance DataFrame for a single dimension key.

    Args:
        amounts: List of variance_amount values, one per period.
        periods: Period IDs (auto-generated if None).
        fiscal_year: Fiscal year for all rows.
        comparator_amount: Budget amount for computing variance_pct.
    """
    if periods is None:
        periods = [f"{fiscal_year}-{m:02d}" for m in range(1, len(amounts) + 1)]

    rows = []
    for p, amt in zip(periods, amounts):
        pct = (amt / comparator_amount * 100) if comparator_amount != 0 else np.nan
        rows.append({
            "period_id": p,
            "account_id": "acct_advisory_fees",
            "bu_id": "BU1",
            "costcenter_node_id": "CC1",
            "geo_node_id": "GEO1",
            "segment_node_id": "SEG1",
            "lob_node_id": "LOB1",
            "fiscal_year": fiscal_year,
            "base_id": "BUDGET",
            "view_id": "MTD",
            "variance_amount": amt,
            "variance_pct": pct,
            "pl_category": "Revenue",
            "actual_amount": comparator_amount + amt,
            "comparator_amount": comparator_amount,
        })
    return pd.DataFrame(rows).sort_values("period_id").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tests — Rule 1: Consecutive Direction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConsecutiveDirection:
    """Rule 1: Consecutive same-sign periods trigger a trend flag."""

    def test_consecutive_direction_3_periods(self) -> None:
        """3 consecutive positive variances should produce a trend flag.

        Default min_consecutive=3. Three positive amounts in a row.
        """
        series = _make_trend_series([1000, 2000, 3000])
        flags = _check_consecutive_direction(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            min_consecutive=3,
        )
        assert len(flags) >= 1, "3 consecutive same-sign periods should flag"
        assert flags[0]["rule_type"] == "consecutive_direction"
        assert flags[0]["consecutive_periods"] == 3
        assert flags[0]["direction"] == "increasing"

    def test_consecutive_direction_2_periods_no_flag(self) -> None:
        """Only 2 consecutive same-sign periods should NOT produce a flag.

        With min_consecutive=3, a streak of length 2 is insufficient.
        """
        series = _make_trend_series([1000, 2000])
        flags = _check_consecutive_direction(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            min_consecutive=3,
        )
        assert len(flags) == 0, "Only 2 periods should not trigger trend flag"

    def test_consecutive_direction_negative_streak(self) -> None:
        """3 consecutive negative variances should flag as decreasing."""
        series = _make_trend_series([-500, -1000, -1500])
        flags = _check_consecutive_direction(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            min_consecutive=3,
        )
        assert len(flags) >= 1
        assert flags[0]["direction"] == "decreasing"

    def test_sign_change_breaks_streak(self) -> None:
        """A sign change in the middle resets the consecutive count.

        Sequence: +, +, -, +, + -> no streak of 3.
        """
        series = _make_trend_series([1000, 2000, -500, 1000, 2000])
        flags = _check_consecutive_direction(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            min_consecutive=3,
        )
        assert len(flags) == 0, "Sign change breaks streak, no 3-consecutive run"


# ---------------------------------------------------------------------------
# Tests — Rule 2: Cumulative YTD Breach
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCumulativeYTDBreach:
    """Rule 2: Individual periods below threshold but cumulative YTD exceeds."""

    def test_cumulative_ytd_breach(self, threshold_config: ThresholdConfig) -> None:
        """Individual MTD variances all below $50K threshold but cumulative
        YTD sum exceeds it.

        6 months at $10K each = $60K cumulative (above $50K threshold).
        Each individual period: $10K / 10% -> abs breach False (10K < 50K),
        pct breach True ONLY if pct >= 3%. With 10%, pct breach is True.
        So to test cumulative-only, we need individual periods that are
        NOT material: use amounts below threshold and pct below threshold.

        6 months at $10K / 1% each: not individually material.
        Cumulative: $60K / ~1% -> abs breach True ($60K >= $50K).
        """
        series = _make_trend_series(
            amounts=[10_000] * 6,
            comparator_amount=1_000_000,  # 1% variance per period
        )
        flags = _check_cumulative_ytd_breach(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            threshold_config=threshold_config,
            pl_category="Revenue",
        )
        assert len(flags) >= 1, "Cumulative YTD should breach when sum > threshold"
        assert flags[0]["rule_type"] == "cumulative_ytd_breach"
        assert flags[0]["cumulative_amount"] == pytest.approx(60_000)

    def test_no_cumulative_breach_when_individually_material(
        self, threshold_config: ThresholdConfig
    ) -> None:
        """If any individual period is material, cumulative check does not flag.

        One period at $60K (material) and two at $10K.
        Since at least one period is individually material, this is not a
        cumulative-only breach and should NOT be flagged by rule 2.
        """
        series = _make_trend_series(
            amounts=[60_000, 10_000, 10_000],
            comparator_amount=100_000,  # 60% for first period -> material
        )
        flags = _check_cumulative_ytd_breach(
            series=series,
            account_id="acct_advisory_fees",
            dimension_key="acct_advisory_fees|BU1|CC1|GEO1|SEG1|LOB1",
            threshold_config=threshold_config,
            pl_category="Revenue",
        )
        assert len(flags) == 0, "Should not flag when individual period is material"


@pytest.mark.unit
class TestDetectTrendsIntegration:
    """Test the top-level detect_trends function end-to-end."""

    def test_detect_trends_returns_dataframe(
        self, threshold_config: ThresholdConfig
    ) -> None:
        """detect_trends should return a DataFrame with expected schema columns."""
        series = _make_trend_series([1000, 2000, 3000])
        result = detect_trends(series, threshold_config)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            expected_cols = {
                "trend_id", "account_id", "dimension_key", "rule_type",
                "consecutive_periods", "cumulative_amount", "direction",
                "period_details", "created_at",
            }
            assert expected_cols.issubset(set(result.columns))
