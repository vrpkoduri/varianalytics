"""Tests for Phase 3F: Quick Intelligence Dimensions.

Tests all 4 intelligence dimensions:
1. Materiality Context
2. Risk Classification
3. Cumulative Projection
4. Variance Persistence
"""

import pytest

from shared.intelligence.materiality import compute_materiality_context
from shared.intelligence.risk import classify_risk
from shared.intelligence.projection import compute_cumulative_projection
from shared.intelligence.persistence import compute_persistence


# ======================================================================
# Materiality Context
# ======================================================================


class TestMaterialityContext:
    """Test materiality context computation."""

    def test_small_vs_revenue_large_vs_ebitda(self):
        """$200K is small % of revenue but large % of EBITDA."""
        result = compute_materiality_context(
            200_000,
            {"revenue": 60_000_000, "ebitda": 2_500_000},
        )
        assert result["pct_of_revenue"] < 0.01  # < 1% of revenue
        assert result["pct_of_ebitda"] > 0.05   # > 5% of EBITDA
        assert result["most_material_to"] == "ebitda"

    def test_note_format(self):
        """Note string contains dollar amount and percentages."""
        result = compute_materiality_context(
            200_000,
            {"revenue": 60_000_000, "ebitda": 2_500_000},
        )
        assert "$200,000" in result["note"]
        assert "%" in result["note"]
        assert "Revenue" in result["note"] or "Ebitda" in result["note"]

    def test_zero_total_safe(self):
        """Handles zero totals without division error."""
        result = compute_materiality_context(100_000, {"revenue": 0, "ebitda": 0})
        assert result["most_material_to"] is None
        assert result["note"] == ""

    def test_identifies_most_impactful(self):
        """Correctly identifies the metric with highest impact %."""
        result = compute_materiality_context(
            500_000,
            {"revenue": 100_000_000, "ebitda": 5_000_000, "gross_profit": 20_000_000},
        )
        assert result["most_material_to"] == "ebitda"

    def test_single_metric(self):
        """Works with just one total."""
        result = compute_materiality_context(100_000, {"revenue": 10_000_000})
        assert "pct_of_revenue" in result
        assert "%" in result["note"]

    def test_negative_variance(self):
        """Works with negative variance (uses absolute value)."""
        result = compute_materiality_context(-200_000, {"revenue": 60_000_000})
        assert result["pct_of_revenue"] > 0


# ======================================================================
# Risk Classification
# ======================================================================


class TestRiskClassification:
    """Test risk classification from decomposition."""

    def test_fx_dominant_uncontrollable(self):
        """FX > 40% → uncontrollable."""
        result = classify_risk(
            {"method": "vol_price_mix_fx", "components": {"volume": 20, "price": 10, "fx": 70}},
            "Revenue",
        )
        assert result["classification"] == "uncontrollable"
        assert result["primary_driver"] == "fx"
        assert "FX" in result["note"]
        assert "uncontrollable" in result["note"]

    def test_volume_partially_controllable(self):
        """Volume > 40% → partially controllable."""
        result = classify_risk(
            {"method": "vol_price_mix_fx", "components": {"volume": 60, "price": 20, "fx": 10, "mix": 10}},
            "Revenue",
        )
        assert result["classification"] == "partially_controllable"
        assert result["primary_driver"] == "volume"

    def test_price_controllable(self):
        """Price > 40% → controllable."""
        result = classify_risk(
            {"method": "vol_price_mix_fx", "components": {"volume": 10, "price": 70, "fx": 10, "mix": 10}},
            "Revenue",
        )
        assert result["classification"] == "controllable"
        assert result["primary_driver"] == "price"

    def test_mixed_drivers(self):
        """No dominant component → mixed."""
        result = classify_risk(
            {"method": "vol_price_mix_fx", "components": {"volume": 30, "price": 25, "fx": 25, "mix": 20}},
            "Revenue",
        )
        assert result["classification"] == "mixed_drivers"
        assert "Mixed" in result["note"]

    def test_no_decomposition(self):
        """Graceful with no decomposition data."""
        result = classify_risk(None, "Revenue")
        assert result["classification"] == "unknown"
        assert result["note"] == ""

    def test_empty_components(self):
        """Graceful with empty components dict."""
        result = classify_risk({"method": "fallback", "components": {}}, "Revenue")
        assert result["classification"] == "unknown"

    def test_note_includes_percentage(self):
        """Note shows the dominant driver percentage."""
        result = classify_risk(
            {"components": {"fx": 130, "volume": 50, "price": 20}},
            "Revenue",
        )
        assert "%" in result["note"]

    def test_rate_controllable(self):
        """Rate-driven costs are controllable."""
        result = classify_risk(
            {"components": {"rate": 80, "volume": 15, "mix": 5}},
            "COGS",
        )
        assert result["classification"] == "controllable"
        assert result["primary_driver"] == "rate"


# ======================================================================
# Cumulative Projection
# ======================================================================


class TestCumulativeProjection:
    """Test cumulative full-year projection."""

    def test_6_months_elapsed(self):
        """6 months → project remaining 6 months."""
        result = compute_cumulative_projection(
            200_000, "2026-06",
            [
                {"period_id": "2026-01", "variance_amount": 180_000},
                {"period_id": "2026-02", "variance_amount": 190_000},
                {"period_id": "2026-03", "variance_amount": 195_000},
                {"period_id": "2026-04", "variance_amount": 200_000},
                {"period_id": "2026-05", "variance_amount": 210_000},
            ],
        )
        assert result["months_elapsed"] == 6
        assert result["months_remaining"] == 6
        assert result["ytd_cumulative"] > 0
        assert result["fy_projection"] > result["ytd_cumulative"]

    def test_full_year_no_remaining(self):
        """12 months elapsed → no projection needed."""
        result = compute_cumulative_projection(
            100_000, "2026-12",
            [{"period_id": f"2026-{i:02d}", "variance_amount": 100_000} for i in range(1, 12)],
        )
        assert result["months_remaining"] == 0
        assert "actual" in result["note"].lower()

    def test_single_month(self):
        """First month extrapolation."""
        result = compute_cumulative_projection(
            300_000, "2026-01", [],
        )
        assert result["months_elapsed"] == 1
        assert result["months_remaining"] == 11
        assert result["fy_projection"] == result["run_rate_monthly"] * 12

    def test_note_format(self):
        """Note includes projection amount and months remaining."""
        result = compute_cumulative_projection(
            200_000, "2026-06",
            [{"period_id": f"2026-0{i}", "variance_amount": 200_000} for i in range(1, 6)],
        )
        assert "remaining" in result["note"]
        assert "$" in result["note"]

    def test_handles_empty_history(self):
        """Works with no prior period data."""
        result = compute_cumulative_projection(100_000, "2026-03", [])
        assert result["ytd_cumulative"] == 100_000
        assert result["fy_projection"] > 0


# ======================================================================
# Variance Persistence
# ======================================================================


class TestVariancePersistence:
    """Test variance persistence analysis."""

    def test_decaying(self):
        """Absolute variance_pct decreasing → decaying."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": -10.2},
            {"period_id": "2026-02", "variance_pct": -9.8},
            {"period_id": "2026-03", "variance_pct": -9.5},
            {"period_id": "2026-04", "variance_pct": -9.1},
            {"period_id": "2026-05", "variance_pct": -8.7},
        ])
        assert result["trend"] == "decaying"
        assert result["change_rate"] < 0

    def test_stable(self):
        """Flat variance_pct → stable."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": -5.0},
            {"period_id": "2026-02", "variance_pct": -5.1},
            {"period_id": "2026-03", "variance_pct": -4.9},
            {"period_id": "2026-04", "variance_pct": -5.0},
            {"period_id": "2026-05", "variance_pct": -5.1},
        ])
        assert result["trend"] == "stable"

    def test_widening(self):
        """Absolute variance_pct increasing → widening."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": -3.0},
            {"period_id": "2026-02", "variance_pct": -4.5},
            {"period_id": "2026-03", "variance_pct": -6.0},
            {"period_id": "2026-04", "variance_pct": -7.5},
            {"period_id": "2026-05", "variance_pct": -9.0},
        ])
        assert result["trend"] == "widening"
        assert result["change_rate"] > 0

    def test_new(self):
        """< 3 months of history → new."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": -5.0},
            {"period_id": "2026-02", "variance_pct": -4.5},
        ])
        assert result["trend"] == "new"

    def test_empty_history(self):
        """Empty history returns new with empty note."""
        result = compute_persistence([])
        assert result["trend"] == "new"
        assert result["note"] == ""

    def test_note_includes_percentages(self):
        """Note includes start and current percentages."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": -10.2},
            {"period_id": "2026-02", "variance_pct": -9.8},
            {"period_id": "2026-03", "variance_pct": -9.5},
            {"period_id": "2026-04", "variance_pct": -8.7},
        ])
        assert "%" in result["note"]
        assert "pp/month" in result["note"]

    def test_positive_variance_decaying(self):
        """Positive variance that's improving also shows decaying."""
        result = compute_persistence([
            {"period_id": "2026-01", "variance_pct": 8.0},
            {"period_id": "2026-02", "variance_pct": 6.5},
            {"period_id": "2026-03", "variance_pct": 5.0},
            {"period_id": "2026-04", "variance_pct": 3.5},
        ])
        assert result["trend"] == "decaying"
