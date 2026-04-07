"""Tests for Pass 4 cross-period correlation analysis.

Validates:
- Persistent variance detection across consecutive months
- Lead-lag pattern detection (account A → account B across periods)
- Year-over-year echo detection (same month, prior year)
- Cross-period analysis skipped gracefully when no prior data
- correlation_type column present in all outputs
- Proper scoring and ranking of cross-period pairs
"""

from __future__ import annotations

import pandas as pd
import pytest

from services.computation.engine.pass4_correlation import (
    _find_lead_lag_patterns,
    _find_persistent_variances,
    _find_yoy_echoes,
    _get_prior_period,
    _get_yoy_period,
    find_correlations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_variance_row(
    variance_id: str,
    account_id: str,
    bu_id: str,
    period_id: str,
    amount: float,
    pct: float = 5.0,
    **kwargs,
) -> dict:
    """Build a single material variance row."""
    row = {
        "variance_id": variance_id,
        "account_id": account_id,
        "bu_id": bu_id,
        "costcenter_node_id": kwargs.get("costcenter_node_id", "cc_1"),
        "geo_node_id": kwargs.get("geo_node_id", "geo_us"),
        "segment_node_id": kwargs.get("segment_node_id", "seg_1"),
        "lob_node_id": kwargs.get("lob_node_id", "lob_1"),
        "period_id": period_id,
        "view_id": "MTD",
        "base_id": "BUDGET",
        "variance_amount": amount,
        "variance_pct": pct,
    }
    row.update(kwargs)
    return row


# ---------------------------------------------------------------------------
# Period helper tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPeriodHelpers:
    """Test period calculation helpers."""

    def test_prior_period_normal(self):
        assert _get_prior_period("2026-06") == "2026-05"

    def test_prior_period_january_wraps(self):
        assert _get_prior_period("2026-01") == "2025-12"

    def test_yoy_period(self):
        assert _get_yoy_period("2026-06") == "2025-06"

    def test_yoy_period_january(self):
        assert _get_yoy_period("2026-01") == "2025-01"

    def test_prior_period_invalid(self):
        assert _get_prior_period("bad") is None

    def test_yoy_period_invalid(self):
        assert _get_yoy_period("bad") is None


# ---------------------------------------------------------------------------
# Persistent variance tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPersistentVariances:
    """Test detection of variances persisting across consecutive months."""

    def test_3_month_streak_detected(self):
        """Account unfavorable for 3 consecutive months → persistent."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_revenue", "BU_EAST", "2026-06", -50_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-apr", "acct_revenue", "BU_EAST", "2026-04", -40_000),
            _make_variance_row("v-may", "acct_revenue", "BU_EAST", "2026-05", -45_000),
        ])

        result = _find_persistent_variances(current, prior, "2026-06")
        assert len(result["pairs"]) == 1
        pair = result["pairs"][0]
        assert pair["correlation_type"] == "persistent"
        assert pair["directional_match"] is True
        assert "3" in pair["hypothesis"]  # 3 consecutive months

    def test_broken_streak_not_detected(self):
        """Streak broken by opposite sign → not persistent."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_revenue", "BU_EAST", "2026-06", -50_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-apr", "acct_revenue", "BU_EAST", "2026-04", 30_000),   # positive!
            _make_variance_row("v-may", "acct_revenue", "BU_EAST", "2026-05", -45_000),
        ])

        result = _find_persistent_variances(current, prior, "2026-06")
        # Only 1 consecutive (May), need 2+ → no persistent pair
        assert len(result["pairs"]) == 0

    def test_single_prior_month_not_enough(self):
        """Only 1 prior month with same sign → need 2+, so no detection."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_revenue", "BU_EAST", "2026-06", -50_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-may", "acct_revenue", "BU_EAST", "2026-05", -45_000),
        ])

        result = _find_persistent_variances(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_different_bu_not_matched(self):
        """Same account but different BU → separate, not persistent."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_revenue", "BU_EAST", "2026-06", -50_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-apr", "acct_revenue", "BU_WEST", "2026-04", -40_000),
            _make_variance_row("v-may", "acct_revenue", "BU_WEST", "2026-05", -45_000),
        ])

        result = _find_persistent_variances(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_empty_prior_no_crash(self):
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_revenue", "BU_EAST", "2026-06", -50_000),
        ])
        result = _find_persistent_variances(current, pd.DataFrame(), "2026-06")
        assert len(result["pairs"]) == 0

    def test_long_streak_scores_higher(self):
        """6-month streak should score higher than 3-month streak."""
        current = pd.DataFrame([
            _make_variance_row("v-curr-a", "acct_a", "BU_EAST", "2026-06", -50_000),
            _make_variance_row("v-curr-b", "acct_b", "BU_EAST", "2026-06", -50_000),
        ])
        prior_rows = []
        # acct_a: 5 prior months (6-month streak total)
        for i, m in enumerate(["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]):
            prior_rows.append(_make_variance_row(f"v-a-{i}", "acct_a", "BU_EAST", m, -40_000))
        # acct_b: 2 prior months (3-month streak total)
        for i, m in enumerate(["2026-04", "2026-05"]):
            prior_rows.append(_make_variance_row(f"v-b-{i}", "acct_b", "BU_EAST", m, -40_000))
        prior = pd.DataFrame(prior_rows)

        result = _find_persistent_variances(current, prior, "2026-06")
        assert len(result["pairs"]) == 2
        # First pair should be the longer streak (higher score)
        assert result["pairs"][0]["correlation_score"] > result["pairs"][1]["correlation_score"]


# ---------------------------------------------------------------------------
# Lead-lag tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLeadLagPatterns:
    """Test detection of causal lead-lag across periods."""

    def test_cross_account_lead_lag_detected(self):
        """Headcount up in May → Salary up in Jun within same BU."""
        current = pd.DataFrame([
            _make_variance_row("v-salary", "acct_salary", "BU_NORTH", "2026-06", 95_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-hc", "acct_headcount", "BU_NORTH", "2026-05", 120_000),
        ])

        result = _find_lead_lag_patterns(current, prior, "2026-06")
        assert len(result["pairs"]) == 1
        assert result["pairs"][0]["correlation_type"] == "lead_lag"

    def test_same_account_excluded(self):
        """Same account across periods = persistence, not lead-lag."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_salary", "BU_NORTH", "2026-06", 95_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-prev", "acct_salary", "BU_NORTH", "2026-05", 100_000),
        ])

        result = _find_lead_lag_patterns(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_different_bu_excluded(self):
        """Different BUs → no lead-lag relationship."""
        current = pd.DataFrame([
            _make_variance_row("v-salary", "acct_salary", "BU_NORTH", "2026-06", 95_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-hc", "acct_headcount", "BU_SOUTH", "2026-05", 120_000),
        ])

        result = _find_lead_lag_patterns(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_only_immediate_prior_period_used(self):
        """Lead-lag only looks at T-1, not older periods."""
        current = pd.DataFrame([
            _make_variance_row("v-salary", "acct_salary", "BU_NORTH", "2026-06", 95_000),
        ])
        # Only April data, no May → no immediate predecessor
        prior = pd.DataFrame([
            _make_variance_row("v-hc", "acct_headcount", "BU_NORTH", "2026-04", 120_000),
        ])

        result = _find_lead_lag_patterns(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_empty_prior_no_crash(self):
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_salary", "BU_NORTH", "2026-06", 95_000),
        ])
        result = _find_lead_lag_patterns(current, pd.DataFrame(), "2026-06")
        assert len(result["pairs"]) == 0


# ---------------------------------------------------------------------------
# Year-over-year echo tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestYoYEchoes:
    """Test detection of year-over-year recurring variances."""

    def test_yoy_echo_same_month_same_direction(self):
        """Same account, same month last year, same direction → YoY echo."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_licensing", "BU_SOUTH", "2026-06", -280_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-py", "acct_licensing", "BU_SOUTH", "2025-06", -310_000),
        ])

        result = _find_yoy_echoes(current, prior, "2026-06")
        assert len(result["pairs"]) == 1
        pair = result["pairs"][0]
        assert pair["correlation_type"] == "yoy_echo"
        assert pair["directional_match"] is True
        assert "2025-06" in pair["hypothesis"]

    def test_yoy_opposite_direction_lower_score(self):
        """Same account YoY but opposite direction → lower score (may not meet threshold)."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_licensing", "BU_SOUTH", "2026-06", 280_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-py", "acct_licensing", "BU_SOUTH", "2025-06", -310_000),
        ])

        result = _find_yoy_echoes(current, prior, "2026-06")
        # May or may not meet threshold, but directional_match should be False if present
        for pair in result["pairs"]:
            assert pair["directional_match"] is False

    def test_wrong_year_month_not_matched(self):
        """Prior data from different month → no YoY echo."""
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_licensing", "BU_SOUTH", "2026-06", -280_000),
        ])
        prior = pd.DataFrame([
            _make_variance_row("v-py", "acct_licensing", "BU_SOUTH", "2025-03", -310_000),
        ])

        result = _find_yoy_echoes(current, prior, "2026-06")
        assert len(result["pairs"]) == 0

    def test_empty_prior_no_crash(self):
        current = pd.DataFrame([
            _make_variance_row("v-curr", "acct_licensing", "BU_SOUTH", "2026-06", -280_000),
        ])
        result = _find_yoy_echoes(current, pd.DataFrame(), "2026-06")
        assert len(result["pairs"]) == 0


# ---------------------------------------------------------------------------
# Integration: find_correlations with cross-period data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindCorrelationsWithCrossPeriod:
    """Full find_correlations with existing_material for cross-period analysis."""

    @pytest.mark.asyncio
    async def test_cross_period_correlations_with_history(self):
        """With existing_material, should find cross-period correlations."""
        # Current period: Jun 2026
        current_rows = [
            _make_variance_row("v-rev-jun", "acct_revenue", "BU_EAST", "2026-06", -80_000),
            _make_variance_row("v-cogs-jun", "acct_cogs", "BU_EAST", "2026-06", -20_000),
        ]

        # Prior periods: 3 months of revenue being unfavorable
        prior_rows = [
            _make_variance_row("v-rev-mar", "acct_revenue", "BU_EAST", "2026-03", -60_000),
            _make_variance_row("v-rev-apr", "acct_revenue", "BU_EAST", "2026-04", -65_000),
            _make_variance_row("v-rev-may", "acct_revenue", "BU_EAST", "2026-05", -72_000),
            # Also add a lead-lag candidate: different account in May
            _make_variance_row("v-hc-may", "acct_headcount", "BU_EAST", "2026-05", 50_000),
        ]

        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(current_rows),
            "existing_material": pd.DataFrame(prior_rows),
        }

        await find_correlations(ctx)
        corr = ctx["correlations"]

        assert not corr.empty
        assert "correlation_type" in corr.columns

        types = set(corr["correlation_type"].unique())
        # Should have within_period (rev+cogs) and persistent (revenue streak)
        assert "within_period" in types or "persistent" in types

    @pytest.mark.asyncio
    async def test_correlation_type_column_always_present(self):
        """correlation_type column should be present even without cross-period data."""
        rows = [
            _make_variance_row("v-1", "acct_1", "BU_A", "2026-06", -50_000),
            _make_variance_row("v-2", "acct_1", "BU_A", "2026-06", -45_000),
        ]
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(rows),
        }

        await find_correlations(ctx)
        corr = ctx["correlations"]

        if not corr.empty:
            assert "correlation_type" in corr.columns
            assert (corr["correlation_type"] == "within_period").all()

    @pytest.mark.asyncio
    async def test_no_existing_material_skips_cross_period(self):
        """Without existing_material, only within-period correlations."""
        rows = [
            _make_variance_row(f"v-{i}", f"acct_{i % 3}", "BU_A", "2026-06", -(i + 1) * 10_000)
            for i in range(6)
        ]
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(rows),
        }

        await find_correlations(ctx)
        corr = ctx["correlations"]

        if not corr.empty:
            # All should be within_period
            assert (corr["correlation_type"] == "within_period").all()

    @pytest.mark.asyncio
    async def test_yoy_echo_found_in_full_pipeline(self):
        """YoY echo detected when prior year same month exists."""
        current_rows = [
            _make_variance_row("v-curr", "acct_travel", "BU_WEST", "2026-06", -58_000),
        ]
        prior_rows = [
            # Same month last year
            _make_variance_row("v-py", "acct_travel", "BU_WEST", "2025-06", -45_000),
        ]

        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(current_rows),
            "existing_material": pd.DataFrame(prior_rows),
        }

        await find_correlations(ctx)
        corr = ctx["correlations"]

        yoy = corr[corr["correlation_type"] == "yoy_echo"] if not corr.empty else pd.DataFrame()
        assert len(yoy) == 1
        assert bool(yoy.iloc[0]["directional_match"]) is True

    @pytest.mark.asyncio
    async def test_accumulation_scenario_3_periods(self):
        """Simulate running 3 periods sequentially with accumulation."""
        # Period 1: Apr 2026 — no history
        ctx1 = {
            "period_id": "2026-04",
            "material_variances": pd.DataFrame([
                _make_variance_row("v-apr", "acct_rev", "BU_A", "2026-04", -30_000),
            ]),
        }
        await find_correlations(ctx1)
        corr1 = ctx1["correlations"]
        # No cross-period possible
        if not corr1.empty:
            assert (corr1["correlation_type"] == "within_period").all()

        # Period 2: May 2026 — has Apr as history
        ctx2 = {
            "period_id": "2026-05",
            "material_variances": pd.DataFrame([
                _make_variance_row("v-may", "acct_rev", "BU_A", "2026-05", -35_000),
            ]),
            "existing_material": pd.DataFrame([
                _make_variance_row("v-apr", "acct_rev", "BU_A", "2026-04", -30_000),
            ]),
        }
        await find_correlations(ctx2)
        # Only 1 prior month with same sign → not enough for persistent (need 2+)

        # Period 3: Jun 2026 — has Apr+May as history → persistent detected!
        ctx3 = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame([
                _make_variance_row("v-jun", "acct_rev", "BU_A", "2026-06", -40_000),
            ]),
            "existing_material": pd.DataFrame([
                _make_variance_row("v-apr", "acct_rev", "BU_A", "2026-04", -30_000),
                _make_variance_row("v-may", "acct_rev", "BU_A", "2026-05", -35_000),
            ]),
        }
        await find_correlations(ctx3)
        corr3 = ctx3["correlations"]

        persistent = corr3[corr3["correlation_type"] == "persistent"] if not corr3.empty else pd.DataFrame()
        assert len(persistent) == 1, "Should detect 3-month persistent pattern"
        assert "3" in persistent.iloc[0]["hypothesis"]
