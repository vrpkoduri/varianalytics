"""Integration tests for the full computation engine pipeline.

Runs EngineRunner.run_full_pipeline() on actual synthetic data and
validates that all passes produce expected outputs with correct counts.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pandas as pd
import pytest

from services.computation.engine.runner import EngineRunner, PipelineResult

# Path to synthetic data output
_DATA_DIR = str(Path(__file__).parent.parent.parent / "data" / "output")

# Use the latest period from the synthetic data
_PERIOD_ID = "2026-03"


# ---------------------------------------------------------------------------
# Module-scoped fixture: run the pipeline once and reuse the result
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline_result() -> PipelineResult:
    """Run the full engine pipeline on synthetic data once per module.

    This fixture has module scope so the expensive pipeline run is shared
    across all tests in this file.
    """
    runner = EngineRunner()
    result = asyncio.run(
        runner.run_full_pipeline(
            period_id=_PERIOD_ID,
            data_dir=_DATA_DIR,
        )
    )
    # Store the runner for tests that need context access
    result._runner = runner  # type: ignore[attr-defined]
    return result


@pytest.fixture(scope="module")
def pipeline_context(pipeline_result: PipelineResult) -> dict:
    """Access the pipeline's internal context for detailed assertions."""
    return pipeline_result._runner._last_context  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFullPipeline:
    """Integration tests for the end-to-end engine pipeline."""

    def test_full_pipeline_runs(self, pipeline_result: PipelineResult) -> None:
        """Run EngineRunner.run_full_pipeline() on actual synthetic data.

        Verifies the pipeline completes without fatal errors across all 7 passes.
        """
        assert len(pipeline_result.errors) == 0, (
            f"Pipeline had errors: {pipeline_result.errors}"
        )
        assert pipeline_result.total_variances_computed > 0

    def test_pipeline_produces_material_variances(
        self, pipeline_result: PipelineResult
    ) -> None:
        """Material variances count should be greater than zero.

        The synthetic data is designed to produce material variances across
        multiple accounts and business units.
        """
        assert pipeline_result.material_variances > 0, (
            "Expected at least 1 material variance from synthetic data"
        )

    def test_pipeline_netting_flags_exist(
        self, pipeline_context: dict
    ) -> None:
        """At least 1 netting flag should be produced.

        The synthetic data has offsetting child variances that should
        trigger netting detection.
        """
        netting_flags = pipeline_context.get("netting_flags", pd.DataFrame())
        assert len(netting_flags) >= 1, (
            "Expected at least 1 netting flag from synthetic data"
        )

    def test_pipeline_trend_flags_exist(
        self, pipeline_context: dict
    ) -> None:
        """At least 1 trend flag should be produced.

        With 36 months of synthetic data and varied variance patterns,
        trend detection should find consecutive-direction or cumulative
        YTD breach patterns.
        """
        trend_flags = pipeline_context.get("trend_flags", pd.DataFrame())
        assert len(trend_flags) >= 1, (
            "Expected at least 1 trend flag from 36 months of synthetic data"
        )

    def test_pipeline_decomposition_exists(
        self, pipeline_context: dict
    ) -> None:
        """Decomposition rows should be greater than zero.

        Every material variance with pl_category in {Revenue, COGS, OpEx}
        and is_calculated=False should have a decomposition row.
        """
        decomposition = pipeline_context.get("decomposition", pd.DataFrame())
        assert len(decomposition) > 0, (
            "Expected decomposition rows for material variances"
        )

    def test_pipeline_narratives_generated(
        self, pipeline_context: dict
    ) -> None:
        """All material variances should have narratives generated.

        Pass 5 should produce narrative_detail for every row in
        material_variances.
        """
        narratives = pipeline_context.get("narratives", pd.DataFrame())
        material = pipeline_context.get("material_variances", pd.DataFrame())

        assert len(narratives) > 0, "Expected narratives to be generated"

        if not narratives.empty:
            # Every narrative row should have a non-null detail narrative
            null_detail = narratives["narrative_detail"].isna().sum()
            assert null_detail == 0, (
                f"{null_detail} material variances are missing narrative_detail"
            )

    def test_pipeline_runs_under_budget(
        self, pipeline_result: PipelineResult
    ) -> None:
        """Total pipeline execution time should be under 60 seconds.

        This is a generous limit for CI environments. The pipeline
        typically runs in under 30 seconds on the synthetic dataset.
        """
        total_time = sum(t.elapsed_seconds for t in pipeline_result.timings)
        assert total_time < 60, (
            f"Pipeline took {total_time:.1f}s, exceeding 60s budget"
        )

    def test_pipeline_all_passes_have_timings(
        self, pipeline_result: PipelineResult
    ) -> None:
        """All 7 passes should have timing entries recorded."""
        assert len(pipeline_result.timings) == 7, (
            f"Expected 7 pass timings, got {len(pipeline_result.timings)}"
        )
        for timing in pipeline_result.timings:
            assert timing.elapsed_seconds >= 0

    def test_pipeline_variance_counts_reasonable(
        self, pipeline_result: PipelineResult
    ) -> None:
        """Total variance count should be in a reasonable range.

        The synthetic data with 49K fact rows across 3 bases and 3 views
        should produce a large number of variances (100K+).
        """
        assert pipeline_result.total_variances_computed > 100_000, (
            f"Expected > 100K total variances, got {pipeline_result.total_variances_computed}"
        )

    def test_pipeline_review_status_created(
        self, pipeline_context: dict
    ) -> None:
        """Review status entries should be created for all material variances.

        Pass 5 creates AI_DRAFT review entries for each material variance.
        """
        review_status = pipeline_context.get("review_status", [])
        assert len(review_status) > 0, "Expected review status entries"

        # All should be AI_DRAFT
        for entry in review_status:
            assert entry["status"] == "AI_DRAFT"

    def test_pipeline_all_10_calculated_accounts_present(
        self, pipeline_context: dict
    ) -> None:
        """All 10 calculated account IDs should appear in material variances.

        The engine resolves calculated rows (Gross Revenue, Total COR, Gross
        Profit, Total OpEx, EBITDA, Operating Income, Total NonOp, PBT,
        Net Income, Total P&L) in dependency order after rollup.
        """
        material = pipeline_context.get("material_variances", pd.DataFrame())
        assert not material.empty, "material_variances should not be empty"

        expected_calc_accounts = {
            "acct_gross_revenue", "acct_total_cor", "acct_gross_profit",
            "acct_total_opex", "acct_ebitda", "acct_operating_income",
            "acct_total_nonop", "acct_pbt", "acct_net_income", "acct_total_pl",
        }
        present_accounts = set(material["account_id"].unique())
        missing = expected_calc_accounts - present_accounts
        assert len(missing) == 0, (
            f"Missing calculated accounts in material variances: {missing}"
        )

    def test_pipeline_netting_cross_account_check_fires(
        self, pipeline_context: dict
    ) -> None:
        """Netting flags should include at least 1 cross_account check.

        The synthetic data has offsetting APAC advisory/consulting variances
        that should trigger the cross-account netting detection.
        """
        netting_flags = pipeline_context.get("netting_flags", pd.DataFrame())
        assert not netting_flags.empty, "netting_flags should not be empty"

        cross_account = netting_flags[
            netting_flags["check_type"].str.contains("cross_account", case=False)
        ]
        assert len(cross_account) >= 1, (
            f"Expected at least 1 cross_account netting flag, "
            f"got {len(cross_account)}"
        )
