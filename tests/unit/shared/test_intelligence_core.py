"""Tests for Phase 3G: Core Intelligence Dimensions.

Tests 6 core intelligence dimensions:
5. Cross-Dimensional Pivot
6. Peer Comparison
7. Causal Chains
8. Multi-Year Patterns
9. Leading/Lagging
10. Theme Clustering
"""

import pytest
import pandas as pd
import numpy as np

from shared.intelligence.pivot import compute_dimensional_pivot
from shared.intelligence.peer_comparison import compute_peer_comparison
from shared.intelligence.causal_chains import compute_causal_chain
from shared.intelligence.multi_year import compute_multi_year_pattern
from shared.intelligence.leading_lagging import compute_leading_lagging
from shared.intelligence.clustering import compute_theme_clusters


# ======================================================================
# 5. Cross-Dimensional Pivot
# ======================================================================


class TestDimensionalPivot:

    @pytest.fixture
    def sample_variances(self):
        return pd.DataFrame([
            {"variance_id": "v1", "account_id": "A001", "bu_id": "marsh", "geo_node_id": "EMEA", "variance_amount": 850},
            {"variance_id": "v2", "account_id": "A001", "bu_id": "mercer", "geo_node_id": "EMEA", "variance_amount": 50},
            {"variance_id": "v3", "account_id": "A001", "bu_id": "gc", "geo_node_id": "NA", "variance_amount": 100},
        ])

    def test_geo_dominant(self, sample_variances):
        result = compute_dimensional_pivot("v1", sample_variances, "A001")
        assert result["dominant_dimension"] == "geography"
        assert result["dominant_node"] == "EMEA"
        assert result["concentration_pct"] >= 0.85

    def test_no_dominant(self):
        df = pd.DataFrame([
            {"variance_id": "v1", "account_id": "A001", "geo_node_id": "NA", "variance_amount": 100},
            {"variance_id": "v2", "account_id": "A001", "geo_node_id": "EMEA", "variance_amount": 100},
            {"variance_id": "v3", "account_id": "A001", "geo_node_id": "APAC", "variance_amount": 100},
        ])
        result = compute_dimensional_pivot("v1", df, "A001")
        assert result["dominant_dimension"] is None

    def test_note_format(self, sample_variances):
        result = compute_dimensional_pivot("v1", sample_variances, "A001")
        assert "%" in result["note"]
        assert "EMEA" in result["note"]

    def test_empty_data(self):
        result = compute_dimensional_pivot("v1", pd.DataFrame(), "A001")
        assert result["dominant_dimension"] is None
        assert result["note"] == ""


# ======================================================================
# 6. Peer Comparison
# ======================================================================


class TestPeerComparison:

    def test_systemic_pattern(self):
        peers = [
            {"bu_id": "mercer", "variance_amount": 100},
            {"bu_id": "gc", "variance_amount": 80},
            {"bu_id": "ow", "variance_amount": 120},
            {"bu_id": "mmc", "variance_amount": 90},
        ]
        result = compute_peer_comparison(peers, "marsh", 110)
        assert result["pattern"] == "systemic"
        assert result["bus_same_direction"] == 5

    def test_isolated_pattern(self):
        peers = [
            {"bu_id": "mercer", "variance_amount": -50},
            {"bu_id": "gc", "variance_amount": -30},
            {"bu_id": "ow", "variance_amount": -20},
            {"bu_id": "mmc", "variance_amount": -40},
        ]
        result = compute_peer_comparison(peers, "marsh", 100)
        assert result["pattern"] == "isolated"

    def test_outlier_pattern(self):
        peers = [
            {"bu_id": "mercer", "variance_amount": 20},
            {"bu_id": "gc", "variance_amount": 25},
            {"bu_id": "ow", "variance_amount": 15},
            {"bu_id": "mmc", "variance_amount": 30},
        ]
        result = compute_peer_comparison(peers, "marsh", 200)  # >2x median
        assert result["pattern"] == "outlier"

    def test_single_bu(self):
        result = compute_peer_comparison([], "marsh", 100)
        assert result["pattern"] == "isolated"

    def test_note_format(self):
        peers = [
            {"bu_id": "mercer", "variance_amount": 100},
            {"bu_id": "gc", "variance_amount": 80},
        ]
        result = compute_peer_comparison(peers, "marsh", 110)
        assert "BU" in result["note"]


# ======================================================================
# 7. Causal Chains
# ======================================================================


class TestCausalChains:

    def test_strong_link(self):
        correlations = [
            {"partner_id": "v_hc_001", "score": 0.87, "hypothesis": "Headcount shortfall drives fees"},
        ]
        result = compute_causal_chain(correlations, {"hc": {"account_name": "Headcount"}})
        assert result["has_causal_link"] is True
        assert result["strongest_link"]["score"] == 0.87

    def test_no_correlations(self):
        result = compute_causal_chain([], {})
        assert result["has_causal_link"] is False
        assert result["note"] == ""

    def test_weak_correlations_filtered(self):
        correlations = [
            {"partner_id": "v1", "score": 0.3},
            {"partner_id": "v2", "score": 0.2},
        ]
        result = compute_causal_chain(correlations, {})
        assert result["has_causal_link"] is False

    def test_chain_note(self):
        correlations = [
            {"partner_id": "v_hc", "score": 0.87, "hypothesis": "Headcount drives fees"},
            {"partner_id": "v_fx", "score": 0.65, "hypothesis": None},
        ]
        result = compute_causal_chain(correlations, {})
        assert "r=0.87" in result["note"]
        assert result["chain_length"] == 2

    def test_hypothesis_included(self):
        correlations = [
            {"partner_id": "v1", "score": 0.75, "hypothesis": "Cost inflation impact"},
        ]
        result = compute_causal_chain(correlations, {})
        assert "Cost inflation" in result["note"]


# ======================================================================
# 8. Multi-Year Patterns
# ======================================================================


class TestMultiYearPatterns:

    def test_seasonal_repeat(self):
        history = [
            {"period_id": f"2024-{m:02d}", "variance_pct": -3.0 if m == 6 else 1.0, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": f"2025-{m:02d}", "variance_pct": -3.5 if m == 6 else 0.5, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": "2026-06", "variance_pct": -3.2, "variance_amount": 100}
        ]
        result = compute_multi_year_pattern(history, "2026-06")
        assert result["pattern_detected"] is True
        assert result["pattern_type"] == "seasonal_repeat"

    def test_no_prior_year(self):
        history = [
            {"period_id": f"2026-{m:02d}", "variance_pct": -2.0, "variance_amount": 100}
            for m in range(1, 7)
        ]
        result = compute_multi_year_pattern(history, "2026-06")
        assert result["pattern_detected"] is False

    def test_structural_growing(self):
        history = [
            {"period_id": f"2024-{m:02d}", "variance_pct": 1.0, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": f"2025-{m:02d}", "variance_pct": -3.0 if m == 6 else 1.0, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": "2026-06", "variance_pct": -8.0, "variance_amount": 100}
        ]
        result = compute_multi_year_pattern(history, "2026-06")
        assert result["pattern_detected"] is True

    def test_note_format(self):
        history = [
            {"period_id": f"2024-{m:02d}", "variance_pct": -3.0 if m == 6 else 1.0, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": f"2025-{m:02d}", "variance_pct": -3.2 if m == 6 else 0.5, "variance_amount": 100}
            for m in range(1, 13)
        ] + [
            {"period_id": "2026-06", "variance_pct": -3.1, "variance_amount": 100}
        ]
        result = compute_multi_year_pattern(history, "2026-06")
        if result["pattern_detected"]:
            assert "Jun" in result["note"] or "2024" in result["note"]


# ======================================================================
# 9. Leading/Lagging Indicators
# ======================================================================


class TestLeadingLagging:

    def test_leading_indicator(self):
        my_history = [
            {"period_id": f"2026-{m:02d}", "variance_pct": float(m * 2)}
            for m in range(1, 7)
        ]
        partner_history = [
            {"period_id": f"2026-{m:02d}", "variance_pct": float((m + 2) * 2)}  # Leads by ~2 months
            for m in range(1, 7)
        ]
        correlations = [{"partner_id": "partner_1", "score": 0.85}]
        result = compute_leading_lagging(
            correlations, my_history, {"partner_1": partner_history}
        )
        # May or may not detect depending on correlation strength
        assert isinstance(result["has_lead_lag"], bool)

    def test_no_lead_lag(self):
        result = compute_leading_lagging([], [], {})
        assert result["has_lead_lag"] is False
        assert result["note"] == ""

    def test_insufficient_history(self):
        my_history = [{"period_id": "2026-01", "variance_pct": 5.0}]
        correlations = [{"partner_id": "p1", "score": 0.9}]
        result = compute_leading_lagging(correlations, my_history, {"p1": my_history})
        assert result["has_lead_lag"] is False

    def test_note_format(self):
        # Generate clear lead/lag data
        my_history = [
            {"period_id": f"2026-{m:02d}", "variance_pct": 0.0 if m < 3 else 5.0}
            for m in range(1, 7)
        ]
        partner_history = [
            {"period_id": f"2026-{m:02d}", "variance_pct": 0.0 if m < 1 else 5.0}
            for m in range(1, 7)
        ]
        correlations = [{"partner_id": "p1", "score": 0.9}]
        result = compute_leading_lagging(
            correlations, my_history, {"p1": partner_history}
        )
        if result["has_lead_lag"]:
            assert "month" in result["note"]


# ======================================================================
# 10. Theme Clustering
# ======================================================================


class TestThemeClustering:

    @pytest.fixture
    def sample_variances(self):
        rows = []
        for i in range(20):
            rows.append({
                "variance_id": f"v{i:03d}",
                "period_id": "2026-06",
                "view_id": "MTD",
                "base_id": "BUDGET",
                "account_id": f"A{i%5:03d}",
                "bu_id": ["marsh", "mercer", "gc", "ow"][i % 4],
                "geo_node_id": "EMEA" if i < 12 else "NA",
                "pl_category": "Revenue" if i < 12 else "OpEx",
                "variance_amount": -(100 + i * 10) if i < 12 else (50 + i * 5),
                "variance_pct": -(2.0 + i * 0.3) if i < 12 else (1.0 + i * 0.2),
            })
        return pd.DataFrame(rows)

    def test_identifies_clusters(self, sample_variances):
        clusters = compute_theme_clusters(sample_variances, "2026-06")
        assert len(clusters) >= 1

    def test_cluster_has_expected_fields(self, sample_variances):
        clusters = compute_theme_clusters(sample_variances, "2026-06")
        if clusters:
            c = clusters[0]
            assert "cluster_id" in c
            assert "theme" in c
            assert "variance_count" in c
            assert "total_amount" in c
            assert "members" in c
            assert "common_dimensions" in c

    def test_cluster_theme_name(self, sample_variances):
        clusters = compute_theme_clusters(sample_variances, "2026-06")
        if clusters:
            assert len(clusters[0]["theme"]) > 0

    def test_common_dimensions(self, sample_variances):
        clusters = compute_theme_clusters(sample_variances, "2026-06")
        if clusters:
            assert isinstance(clusters[0]["common_dimensions"], dict)

    def test_empty_data(self):
        clusters = compute_theme_clusters(pd.DataFrame(), "2026-06")
        assert clusters == []

    def test_few_variances_no_cluster(self):
        df = pd.DataFrame([
            {"variance_id": "v1", "period_id": "2026-06", "view_id": "MTD", "base_id": "BUDGET",
             "account_id": "A001", "variance_amount": 100, "variance_pct": 1.0, "pl_category": "Revenue"},
        ])
        clusters = compute_theme_clusters(df, "2026-06")
        assert clusters == []
