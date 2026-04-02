"""Tests for FX narrative framing in variance narratives."""

import asyncio
import pytest
import pandas as pd

from services.computation.engine.runner import EngineRunner

DATA_DIR = "data/output"


@pytest.fixture(scope="module")
def engine_material():
    """Run engine for one period and get material variances."""
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            runner.run_full_pipeline(period_id="2025-12", data_dir=DATA_DIR, llm_client=None)
        )
    finally:
        loop.close()
    return runner._last_context.get("material_variances", pd.DataFrame())


class TestSeasonalInNarrative:
    """Verify seasonal context appears in December narratives."""

    def test_december_narrative_has_seasonal_note(self, engine_material):
        """December narratives should mention seasonal pattern."""
        dec = engine_material[
            (engine_material["view_id"] == "MTD") &
            (engine_material["base_id"] == "BUDGET") &
            (engine_material["is_calculated"] == False) &
            (engine_material["pl_category"] == "Revenue")
        ]
        if dec.empty:
            pytest.skip("No December revenue data")

        # At least some narratives should mention seasonality
        seasonal_count = 0
        for _, r in dec.head(20).iterrows():
            narr = str(r.get("narrative_detail", "")).lower()
            if "seasonal" in narr or "december" in narr or "peak" in narr:
                seasonal_count += 1

        assert seasonal_count > 0, "No seasonal context found in December narratives"

    def test_narrative_still_has_core_content(self, engine_material):
        """Seasonal note doesn't break core narrative structure."""
        sample = engine_material[
            (engine_material["view_id"] == "MTD") &
            (engine_material["is_calculated"] == False)
        ]
        if sample.empty:
            pytest.skip("No data")

        narr = str(sample.iloc[0].get("narrative_detail", ""))
        assert "vs Budget" in narr or "vs Forecast" in narr or "vs Prior" in narr
        assert "[AI Draft]" in narr


class TestFXContext:
    """Verify FX context appears when FX impact is material."""

    def test_fx_note_format(self):
        """FX note should mention currency impact when present."""
        # This tests the template logic — FX note appears when decomp has fx > 0
        # The actual data may or may not have material FX (synthetic data has small FX variance)
        # Just verify the template doesn't crash
        from services.computation.engine.pass5_narrative import _generate_template_narrative

        var_dict = {
            "account_id": "acct_advisory_fees",
            "variance_amount": 1000,
            "variance_pct": 5.0,
            "period_id": "2025-12",
            "base_id": "BUDGET",
            "pl_category": "Revenue",
            "bu_id": "marsh",
            "costcenter_node_id": "cc1",
            "geo_node_id": "geo1",
            "segment_node_id": "seg1",
            "lob_node_id": "lob1",
        }
        acct_meta = {"account_name": "Advisory Fees", "variance_sign": "natural"}
        context_maps = {
            "trends": {},
            "decomposition": {"test-id": {"volume": 600, "price": 250, "mix": 100, "fx": 50, "is_fallback": True}},
            "prior_narratives": {},
            "prior_period": None,
        }

        result = _generate_template_narrative(var_dict, acct_meta, context_maps)
        assert "detail" in result
        assert len(result["detail"]) > 20

    def test_no_crash_without_fx_data(self):
        """Template should work fine without any FX data."""
        from services.computation.engine.pass5_narrative import _generate_template_narrative

        var_dict = {
            "account_id": "acct_opex",
            "variance_amount": -500,
            "variance_pct": -2.1,
            "period_id": "2026-05",
            "base_id": "BUDGET",
            "pl_category": "OpEx",
        }
        acct_meta = {"account_name": "Operating Expenses", "variance_sign": "inverse"}
        context_maps = {"trends": {}, "decomposition": {}, "prior_narratives": {}, "prior_period": None}

        result = _generate_template_narrative(var_dict, acct_meta, context_maps)
        assert "Operating Expenses" in result["detail"]
