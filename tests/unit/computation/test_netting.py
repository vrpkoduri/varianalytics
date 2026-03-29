"""Unit tests for netting detection — 4 MVP checks.

Tests the detection of offsetting child variances that mask the parent
node's true variance magnitude. Uses small hand-crafted DataFrames
rather than loading full synthetic data.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from services.computation.detection.netting import detect_netting
from shared.config.thresholds import ThresholdConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def threshold_config() -> ThresholdConfig:
    """Load the standard threshold config from the project YAML."""
    return ThresholdConfig()


def _make_variance_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Helper to build a variance DataFrame with all required columns.

    Each row dict should specify account_id, variance_amount, variance_pct,
    and pl_category at minimum. Other dimension columns are filled with
    consistent defaults.
    """
    defaults = {
        "period_id": "2026-03",
        "bu_id": "BU1",
        "costcenter_node_id": "CC1",
        "geo_node_id": "GEO1",
        "segment_node_id": "SEG1",
        "lob_node_id": "LOB1",
        "fiscal_year": 2026,
        "view_id": "MTD",
        "base_id": "BUDGET",
        "is_calculated": False,
        "actual_amount": 0,
        "comparator_amount": 0,
    }
    full_rows = [{**defaults, **r} for r in rows]
    return pd.DataFrame(full_rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGrossOffset:
    """Check 1: Parent with small net but large gross child variances."""

    def test_gross_offset_detected(self, threshold_config: ThresholdConfig) -> None:
        """Parent below materiality with gross child sum >> |net| should be flagged.

        Parent acct_revenue: variance=+2K (below $50K threshold).
        Child A: +51K, Child B: -49K.
        Net = 2K, Gross = 100K, ratio = 100/2 = 50 >> 3.0 threshold.
        """
        df = _make_variance_df([
            # Parent (rollup) — variance is sum of children = 2K
            {
                "account_id": "acct_revenue",
                "variance_amount": 2_000,
                "variance_pct": 0.5,
                "pl_category": "Revenue",
            },
            # Child A
            {
                "account_id": "acct_advisory_fees",
                "variance_amount": 51_000,
                "variance_pct": 12.0,
                "pl_category": "Revenue",
            },
            # Child B
            {
                "account_id": "acct_consulting_fees",
                "variance_amount": -49_000,
                "variance_pct": -11.0,
                "pl_category": "Revenue",
            },
        ])

        result = detect_netting(df, threshold_config, period_id="2026-03")

        # Should find at least one gross_offset flag
        gross_flags = result[result["check_type"] == "gross_offset"]
        assert len(gross_flags) >= 1, "Expected gross_offset netting flag"
        assert gross_flags.iloc[0]["netting_ratio"] > 3.0


@pytest.mark.unit
class TestDispersion:
    """Check 2: High dispersion of child variance percentages."""

    def test_dispersion_detected(self, threshold_config: ThresholdConfig) -> None:
        """Parent with high child variance_pct std dev (>10pp) should be flagged.

        Child variance pcts: +25%, -15% -> std dev ~28.3 >> 10.
        """
        df = _make_variance_df([
            # Parent — sum of children
            {
                "account_id": "acct_revenue",
                "variance_amount": 5_000,
                "variance_pct": 1.0,
                "pl_category": "Revenue",
            },
            # Child A: high positive pct
            {
                "account_id": "acct_advisory_fees",
                "variance_amount": 25_000,
                "variance_pct": 25.0,
                "pl_category": "Revenue",
            },
            # Child B: negative pct
            {
                "account_id": "acct_consulting_fees",
                "variance_amount": -20_000,
                "variance_pct": -15.0,
                "pl_category": "Revenue",
            },
        ])

        result = detect_netting(df, threshold_config, period_id="2026-03")

        dispersion_flags = result[result["check_type"] == "dispersion"]
        assert len(dispersion_flags) >= 1, "Expected dispersion netting flag"


@pytest.mark.unit
class TestDirectionalSplit:
    """Check 3: Parent below threshold with children in opposite directions."""

    def test_directional_split_detected(self, threshold_config: ThresholdConfig) -> None:
        """Parent below threshold with some children positive, others negative.

        Parent variance = +1K (well below $50K threshold).
        Children: +3K and -2K.
        """
        df = _make_variance_df([
            {
                "account_id": "acct_opex",
                "variance_amount": 1_000,
                "variance_pct": 0.2,
                "pl_category": "OpEx",
            },
            {
                "account_id": "acct_comp_benefits",
                "variance_amount": 3_000,
                "variance_pct": 1.5,
                "pl_category": "OpEx",
            },
            {
                "account_id": "acct_travel",
                "variance_amount": -2_000,
                "variance_pct": -4.0,
                "pl_category": "OpEx",
            },
        ])

        result = detect_netting(df, threshold_config, period_id="2026-03")

        split_flags = result[result["check_type"] == "directional_split"]
        assert len(split_flags) >= 1, "Expected directional_split netting flag"


@pytest.mark.unit
class TestNoFalsePositives:
    """Ensure material parents are NOT flagged by checks 1 and 3."""

    def test_no_false_positives_material_parent(
        self, threshold_config: ThresholdConfig
    ) -> None:
        """A material parent should NOT be flagged for gross_offset or directional_split.

        Parent variance = $80K (above $50K threshold), children: +100K, -20K.
        The parent is material, so checks 1 and 3 should not flag it.
        """
        df = _make_variance_df([
            {
                "account_id": "acct_revenue",
                "variance_amount": 80_000,
                "variance_pct": 8.0,
                "pl_category": "Revenue",
            },
            {
                "account_id": "acct_advisory_fees",
                "variance_amount": 100_000,
                "variance_pct": 15.0,
                "pl_category": "Revenue",
            },
            {
                "account_id": "acct_consulting_fees",
                "variance_amount": -20_000,
                "variance_pct": -5.0,
                "pl_category": "Revenue",
            },
        ])

        result = detect_netting(df, threshold_config, period_id="2026-03")

        # Checks 1 and 3 should not flag since parent is material
        offset_flags = result[result["check_type"] == "gross_offset"]
        split_flags = result[result["check_type"] == "directional_split"]

        # Filter to flags about this specific parent
        offset_for_parent = offset_flags[offset_flags["parent_node_id"] == "acct_revenue"]
        split_for_parent = split_flags[split_flags["parent_node_id"] == "acct_revenue"]

        assert len(offset_for_parent) == 0, (
            "Material parent should not be flagged for gross_offset"
        )
        assert len(split_for_parent) == 0, (
            "Material parent should not be flagged for directional_split"
        )
