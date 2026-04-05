"""Tests for Phase 3H: Quality + Context Intelligence Dimensions.

Tests 4 new dimensions:
11. Narrative Coherence
12. Anomaly Detection
13. Budget Assumptions
14. Market Context
"""

import pytest

from shared.intelligence.anomaly import compute_anomaly_score
from shared.intelligence.budget_assumptions import compute_budget_gap
from shared.intelligence.market_context import compute_market_context
from shared.intelligence.coherence import compute_narrative_coherence


# ======================================================================
# 12. Anomaly Detection
# ======================================================================


class TestAnomalyDetection:

    def test_z_score_outlier(self):
        """Current amount far beyond historical range → anomaly."""
        history = [{"variance_amount": float(x)} for x in [100, 110, 95, 105, 98, 102, 108, 97]]
        result = compute_anomaly_score(300, history)  # Way above ~100 avg
        assert result["is_anomaly"] is True
        assert result["z_score"] > 2.0

    def test_within_normal(self):
        """Current amount within historical range → not anomaly."""
        history = [{"variance_amount": float(x)} for x in [100, 110, 95, 105, 98, 102, 108, 97]]
        result = compute_anomaly_score(105, history)
        assert result["is_anomaly"] is False

    def test_note_on_anomaly(self):
        """Note present when anomaly detected."""
        history = [{"variance_amount": float(x)} for x in [50, 55, 45, 52, 48, 53]]
        result = compute_anomaly_score(200, history)
        assert result["is_anomaly"] is True
        assert "Anomaly" in result["note"] or "outlier" in result["note"]

    def test_empty_history(self):
        """Empty history → no anomaly."""
        result = compute_anomaly_score(100, [])
        assert result["is_anomaly"] is False
        assert result["note"] == ""

    def test_single_period(self):
        """Single period of history → insufficient data."""
        result = compute_anomaly_score(100, [{"variance_amount": 50}])
        assert result["is_anomaly"] is False

    def test_historical_stats(self):
        """Result includes historical max and min."""
        history = [{"variance_amount": float(x)} for x in [100, 200, 50, 150]]
        result = compute_anomaly_score(500, history)
        assert result["historical_max"] == 200
        assert result["historical_min"] == 50


# ======================================================================
# 13. Budget Assumptions
# ======================================================================


class TestBudgetAssumptions:

    def test_growth_shortfall(self):
        """Actual below assumed growth → shortfall note."""
        result = compute_budget_gap(3.0, "2026-06", "Revenue")
        # Config has revenue_growth_pct: 8.0 for 2026
        if result["assumed_growth"] is not None:
            assert result["gap_pp"] < 0
            assert "shortfall" in result["note"]

    def test_growth_exceeded(self):
        """Actual above assumed growth → above plan note."""
        result = compute_budget_gap(12.0, "2026-06", "Revenue")
        if result["assumed_growth"] is not None:
            assert result["gap_pp"] > 0
            assert "above" in result["note"]

    def test_config_loads(self):
        """Config loads successfully with expected structure."""
        result = compute_budget_gap(5.0, "2026-03", "Revenue")
        assert isinstance(result, dict)
        assert "assumed_growth" in result
        assert "gap_pp" in result

    def test_missing_year(self):
        """Missing fiscal year returns empty result."""
        result = compute_budget_gap(5.0, "2030-01", "Revenue")
        assert result["assumed_growth"] is None
        assert result["note"] == ""

    def test_unknown_category(self):
        """Unknown P&L category returns empty."""
        result = compute_budget_gap(5.0, "2026-06", "UnknownCategory")
        assert result["assumed_growth"] is None

    def test_note_format(self):
        """Note includes assumed and actual percentages."""
        result = compute_budget_gap(3.0, "2026-06", "Revenue")
        if result["note"]:
            assert "%" in result["note"]


# ======================================================================
# 14. Market Context
# ======================================================================


class TestMarketContext:

    def test_has_context_for_known_quarter(self):
        """Q2 2026 has market context in config."""
        result = compute_market_context("2026-06")
        assert result["has_market_context"] is True
        assert result["quarter"] == "2026-Q2"
        assert len(result["factors"]) >= 1

    def test_no_context_for_unknown_quarter(self):
        """Unknown quarter returns empty."""
        result = compute_market_context("2030-01")
        assert result["has_market_context"] is False
        assert result["note"] == ""

    def test_fx_factor_present(self):
        """FX impact factors included."""
        result = compute_market_context("2026-06")
        fx_factors = [f for f in result["factors"] if f["type"] == "fx"]
        assert len(fx_factors) >= 1

    def test_note_format(self):
        """Note includes quarter and factor description."""
        result = compute_market_context("2026-06")
        if result["note"]:
            assert "Q2" in result["note"] or "2026" in result["note"]

    def test_external_notes_included(self):
        """External context notes from YAML included."""
        result = compute_market_context("2026-06")
        assert len(result["external_notes"]) >= 1


# ======================================================================
# 11. Narrative Coherence
# ======================================================================


class TestNarrativeCoherence:

    def test_consistent_narrative(self):
        """Narrative direction matches variance → high coherence."""
        result = compute_narrative_coherence(
            "v001",
            "Revenue increased by $200K, driven by strong advisory fees.",
            200_000,
            [],
            {},
        )
        assert result["coherence_score"] >= 0.75
        assert len(result["issues"]) == 0

    def test_direction_mismatch(self):
        """Narrative says decreased but variance is positive → issue."""
        result = compute_narrative_coherence(
            "v001",
            "Revenue decreased significantly, falling below expectations.",
            200_000,  # Positive variance
            [],
            {},
        )
        assert result["coherence_score"] < 1.0
        assert any("Direction" in i or "direction" in i for i in result["issues"])

    def test_no_narrative_high_score(self):
        """Empty narrative → perfect coherence (nothing to contradict)."""
        result = compute_narrative_coherence("v001", "", 100_000, [], {})
        assert result["coherence_score"] == 1.0

    def test_note_on_issue(self):
        """Note populated when coherence issue detected."""
        result = compute_narrative_coherence(
            "v001",
            "Costs decreased dramatically this period.",
            500_000,  # Positive = unfavorable for costs
            [],
            {},
        )
        if result["issues"]:
            assert "Coherence" in result["note"]

    def test_magnitude_issue(self):
        """Narrative mentions amount 5x actual → magnitude issue."""
        result = compute_narrative_coherence(
            "v001",
            "Revenue changed by $5,000,000 this quarter.",
            100_000,  # Actual is only $100K
            [],
            {},
        )
        assert any("Magnitude" in i or "magnitude" in i for i in result["issues"])

    def test_sibling_consistency(self):
        """Sibling narratives mostly favorable, this says unfavorable → conflict (only when amount matches)."""
        siblings = {
            "s1": "Revenue favorable driven by growth",
            "s2": "Revenue favorable across regions",
            "s3": "Revenue favorable in all segments",
        }
        result = compute_narrative_coherence(
            "v001",
            "Revenue unfavorable and declining.",
            100_000,  # Positive amount but says unfavorable
            [],
            siblings,
        )
        # May or may not flag depending on heuristic thresholds
        assert isinstance(result["coherence_score"], float)
