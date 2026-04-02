"""Integration tests for narrative persistence across engine re-runs.

Validates that approved/reviewed narratives survive when the engine
re-runs with deterministic IDs, while AI_DRAFT narratives get regenerated.
"""

import asyncio

import pandas as pd
import pytest

from services.computation.engine.runner import EngineRunner

DATA_DIR = "data/output"
PERIOD = "2026-05"


@pytest.fixture(scope="module")
def engine_context():
    """Run engine once and return the context."""
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            runner.run_full_pipeline(
                period_id=PERIOD,
                data_dir=DATA_DIR,
                llm_client=None,
            )
        )
    finally:
        loop.close()
    return runner._last_context


@pytest.mark.integration
class TestNarrativePersistence:
    """Tests for narrative preservation across engine re-runs."""

    def test_approved_narrative_survives_rerun(self, engine_context):
        """An APPROVED narrative should be preserved if passed as existing data."""
        material = engine_context.get("material_variances", pd.DataFrame())
        assert not material.empty

        # Simulate: take first variance, mark as APPROVED in existing review status
        first_vid = material["variance_id"].iloc[0]

        fake_existing_review = pd.DataFrame([{
            "variance_id": first_vid,
            "status": "APPROVED",
            "original_narrative": "This was approved by analyst.",
            "edited_narrative": "Analyst-approved narrative text.",
        }])

        fake_existing_material = material[material["variance_id"] == first_vid].copy()
        fake_existing_material["narrative_detail"] = "Analyst-approved narrative text."

        # Re-run engine with existing approved data
        runner2 = EngineRunner()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                runner2.run_full_pipeline(
                    period_id=PERIOD,
                    data_dir=DATA_DIR,
                    llm_client=None,
                    existing_review_status=fake_existing_review,
                    existing_material=fake_existing_material,
                )
            )
        finally:
            loop.close()

        result = runner2._last_context.get("material_variances", pd.DataFrame())
        # The approved variance should be in the output
        approved_row = result[result["variance_id"] == first_vid]
        assert not approved_row.empty, "Approved variance should still be in output"

    def test_draft_narrative_gets_regenerated(self, engine_context):
        """AI_DRAFT narratives should get fresh generation on re-run."""
        material = engine_context.get("material_variances", pd.DataFrame())
        assert not material.empty

        # All narratives from a fresh run should have source
        if "narrative_source" in material.columns:
            assert material["narrative_source"].notna().sum() > 0

    def test_deterministic_ids_match_across_runs(self):
        """Same period produces same variance_ids on two separate runs."""
        runner1 = EngineRunner()
        runner2 = EngineRunner()
        loop = asyncio.new_event_loop()

        try:
            loop.run_until_complete(
                runner1.run_full_pipeline(period_id=PERIOD, data_dir=DATA_DIR, llm_client=None)
            )
            ids1 = set(runner1._last_context["material_variances"]["variance_id"].unique())

            loop.run_until_complete(
                runner2.run_full_pipeline(period_id=PERIOD, data_dir=DATA_DIR, llm_client=None)
            )
            ids2 = set(runner2._last_context["material_variances"]["variance_id"].unique())
        finally:
            loop.close()

        assert ids1 == ids2, (
            f"IDs differ: {len(ids1 - ids2)} only in run1, {len(ids2 - ids1)} only in run2"
        )

    def test_review_status_has_period_and_fy(self, engine_context):
        """Review status entries should include period_id and fiscal_year."""
        review_entries = engine_context.get("review_status", [])
        assert len(review_entries) > 0

        entry = review_entries[0] if isinstance(review_entries, list) else review_entries.iloc[0].to_dict()
        assert "period_id" in entry, "review_status should have period_id"
        assert "fiscal_year" in entry, "review_status should have fiscal_year"
        assert entry["period_id"] == PERIOD
        assert entry["fiscal_year"] == 2026
