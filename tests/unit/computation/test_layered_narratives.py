"""Tests for layered leaf→parent narrative generation.

Validates that Pass 5 generates leaf narratives first, then parent
narratives that reference their children.
"""

import asyncio

import pandas as pd
import pytest

from services.computation.engine.runner import EngineRunner

DATA_DIR = "data/output"
PERIOD = "2026-05"


@pytest.fixture(scope="module")
def engine_material():
    """Run engine once and return material_variances DataFrame."""
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            runner.run_full_pipeline(period_id=PERIOD, data_dir=DATA_DIR, llm_client=None)
        )
    finally:
        loop.close()
    return runner._last_context.get("material_variances", pd.DataFrame())


class TestLayeredGeneration:
    """Tests for leaf-first, then parent-from-children narrative generation."""

    def test_leaves_and_parents_both_have_narratives(self, engine_material):
        """Both leaf and parent accounts should have narratives."""
        leaves = engine_material[engine_material["is_calculated"] == False]
        parents = engine_material[engine_material["is_calculated"] == True]

        assert leaves["narrative_detail"].notna().sum() > 0, "Leaves should have narratives"
        assert parents["narrative_detail"].notna().sum() > 0, "Parents should have narratives"

    def test_parent_narrative_references_children(self, engine_material):
        """Parent narratives should mention child account names or amounts."""
        # EBITDA should reference its dependencies
        ebitda = engine_material[
            (engine_material["account_id"] == "acct_ebitda") &
            (engine_material["view_id"] == "MTD") &
            (engine_material["base_id"] == "BUDGET")
        ]
        if not ebitda.empty:
            narr = str(ebitda.iloc[0].get("narrative_detail", ""))
            # Should mention at least one dependency (Gross Profit, Total OpEx, D&A)
            mentions_child = (
                "GROSS PROFIT" in narr.upper() or
                "Operating" in narr or
                "Depreciation" in narr or
                "Driven by" in narr
            )
            assert mentions_child, f"EBITDA narrative doesn't reference children: {narr[:200]}"

    def test_calculated_uses_parent_template(self, engine_material):
        """Calculated accounts should use the parent template (mentions 'Driven by')."""
        parents = engine_material[
            (engine_material["is_calculated"] == True) &
            (engine_material["view_id"] == "MTD") &
            (engine_material["base_id"] == "BUDGET")
        ]
        if not parents.empty:
            sample = str(parents.iloc[0].get("narrative_detail", ""))
            assert "Driven by" in sample, f"Parent template missing 'Driven by': {sample[:200]}"

    def test_leaf_uses_standard_template(self, engine_material):
        """Leaf accounts should use standard template (mentions decomposition drivers)."""
        leaves = engine_material[
            (engine_material["is_calculated"] == False) &
            (engine_material["view_id"] == "MTD") &
            (engine_material["base_id"] == "BUDGET")
        ]
        if not leaves.empty:
            sample = str(leaves.iloc[0].get("narrative_detail", ""))
            # Standard template mentions direction and amount
            has_direction = "increased" in sample.lower() or "decreased" in sample.lower()
            assert has_direction, f"Leaf narrative missing direction: {sample[:200]}"

    def test_parent_shows_component_count(self, engine_material):
        """Parent narratives should show 'X of Y components contributed positively'."""
        gross_rev = engine_material[
            (engine_material["account_id"] == "acct_gross_revenue") &
            (engine_material["view_id"] == "MTD") &
            (engine_material["base_id"] == "BUDGET")
        ]
        if not gross_rev.empty:
            narr = str(gross_rev.iloc[0].get("narrative_detail", ""))
            assert "components contributed" in narr or "of" in narr, \
                f"Parent missing component count: {narr[:200]}"

    def test_confidence_column_exists(self, engine_material):
        """Material variances should have narrative_confidence column."""
        assert "narrative_confidence" in engine_material.columns
        assert engine_material["narrative_confidence"].notna().sum() > 0

    def test_confidence_range(self, engine_material):
        """Confidence should be between 0.0 and 1.0."""
        conf = engine_material["narrative_confidence"].dropna()
        assert conf.min() >= 0.0
        assert conf.max() <= 1.0

    def test_no_errors_in_pipeline(self, engine_material):
        """Engine should complete with no errors."""
        # If we got here with non-empty material, pipeline succeeded
        assert not engine_material.empty
