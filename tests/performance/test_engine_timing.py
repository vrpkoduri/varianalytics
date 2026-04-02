"""Engine performance benchmark tests.

Validates that the 5.5-pass computation engine completes within SLA thresholds.
Tests run with llm_client=None (template mode) for deterministic timing.

SLAs:
- Full pipeline (template mode): < 15 seconds
- Pass 1 (raw variance): < 3 seconds
- Pass 3 (decomposition): < 2 seconds
- Pass 5 (narrative template): < 2 seconds
"""

import asyncio
import time

import pytest

from services.computation.engine.runner import EngineRunner, PipelineResult

DATA_DIR = "data/output"
PERIOD_ID = "2026-03"


@pytest.fixture(scope="module")
def pipeline_result() -> PipelineResult:
    """Run the full pipeline once (template mode, no LLM) and reuse across tests."""
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            runner.run_full_pipeline(
                period_id=PERIOD_ID,
                data_dir=DATA_DIR,
                llm_client=None,  # Template mode — no LLM calls
                rag_retriever=None,
            )
        )
    finally:
        loop.close()
    return result


@pytest.mark.performance
@pytest.mark.slow
class TestEnginePipelineTiming:
    """Performance SLA tests for the computation engine."""

    def test_full_pipeline_under_60s(self, pipeline_result: PipelineResult):
        """Full 5.5-pass pipeline (template mode) completes in < 60 seconds."""
        total = sum(t.elapsed_seconds for t in pipeline_result.timings)
        assert total < 60.0, (
            f"Pipeline took {total:.2f}s (SLA: < 60s). "
            f"Breakdown: {', '.join(f'{t.pass_name}: {t.elapsed_seconds:.2f}s' for t in pipeline_result.timings)}"
        )

    def test_pass1_under_3s(self, pipeline_result: PipelineResult):
        """Pass 1 (raw variance) completes in < 3 seconds."""
        pass1 = next(
            (t for t in pipeline_result.timings if "Pass 1 " in t.pass_name and "1.5" not in t.pass_name),
            None,
        )
        assert pass1 is not None, "Pass 1 timing not found"
        assert pass1.elapsed_seconds < 3.0, (
            f"Pass 1 took {pass1.elapsed_seconds:.2f}s (SLA: < 3s)"
        )

    def test_pass3_decomposition_under_2s(self, pipeline_result: PipelineResult):
        """Pass 3 (decomposition) completes in < 2 seconds."""
        pass3 = next(
            (t for t in pipeline_result.timings if "Pass 3" in t.pass_name),
            None,
        )
        assert pass3 is not None, "Pass 3 timing not found"
        assert pass3.elapsed_seconds < 2.0, (
            f"Pass 3 took {pass3.elapsed_seconds:.2f}s (SLA: < 2s)"
        )

    def test_pass5_narrative_template_under_2s(self, pipeline_result: PipelineResult):
        """Pass 5 (narrative generation, layered template mode) completes in < 30 seconds."""
        pass5 = next(
            (t for t in pipeline_result.timings if "Pass 5" in t.pass_name),
            None,
        )
        assert pass5 is not None, "Pass 5 timing not found"
        assert pass5.elapsed_seconds < 60.0, (
            f"Pass 5 took {pass5.elapsed_seconds:.2f}s (SLA: < 60s)"
        )

    def test_pipeline_produces_correct_counts(self, pipeline_result: PipelineResult):
        """Pipeline produces expected data volumes."""
        assert pipeline_result.total_variances_computed > 200_000, (
            f"Expected >200K variances, got {pipeline_result.total_variances_computed}"
        )
        assert pipeline_result.material_variances > 3_000, (
            f"Expected >3K material variances, got {pipeline_result.material_variances}"
        )

    def test_pipeline_zero_errors(self, pipeline_result: PipelineResult):
        """Pipeline completes with zero errors."""
        assert len(pipeline_result.errors) == 0, (
            f"Pipeline had {len(pipeline_result.errors)} errors: {pipeline_result.errors}"
        )
