"""Tests for Phase 3B: Engine Separation (Process A vs Process B).

Validates that ProcessARunner and ProcessBRunner can run independently
and that EngineRunner.run_full_pipeline() remains backward compatible.
"""

import asyncio
import sys
import time

import pytest

from services.computation.engine.runner import (
    EngineRunner,
    PassTiming,
    PipelineResult,
    ProcessAResult,
    ProcessARunner,
    ProcessBResult,
    ProcessBRunner,
)
from shared.engine.cost_estimator import (
    estimate_process_b_cost,
    format_cost_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir():
    return "data/output"


@pytest.fixture
def runner():
    return EngineRunner()


@pytest.fixture
def process_a_runner():
    return ProcessARunner()


@pytest.fixture
def process_b_runner():
    return ProcessBRunner()


# ---------------------------------------------------------------------------
# Tests: Result Dataclasses
# ---------------------------------------------------------------------------


class TestResultDataclasses:
    """Test ProcessAResult, ProcessBResult, PipelineResult."""

    def test_process_a_result_defaults(self):
        """ProcessAResult initializes with zero counts."""
        r = ProcessAResult()
        assert r.total_variances == 0
        assert r.material_variances == 0
        assert r.graph_node_count == 0
        assert r.errors == []

    def test_process_b_result_defaults(self):
        """ProcessBResult initializes with zero counts."""
        r = ProcessBResult()
        assert r.narratives_generated == 0
        assert r.correlations_found == 0
        assert r.errors == []

    def test_pipeline_result_from_ab(self):
        """PipelineResult.from_ab combines A + B results."""
        a = ProcessAResult(
            total_variances=1000,
            material_variances=100,
            netted_nodes=5,
            trending_variances=10,
            timings=[PassTiming("pass1", 1.0)],
            errors=[],
        )
        b = ProcessBResult(
            narratives_generated=80,
            correlations_found=20,
            timings=[PassTiming("pass4", 2.0)],
            errors=[],
        )
        combined = PipelineResult.from_ab(a, b)
        assert combined.total_variances_computed == 1000
        assert combined.material_variances == 100
        assert combined.narratives_generated == 80
        assert len(combined.timings) == 2
        assert combined.errors == []

    def test_pipeline_result_from_ab_with_errors(self):
        """PipelineResult.from_ab combines errors from both processes."""
        a = ProcessAResult(errors=["Pass 1 — Raw Variance"])
        b = ProcessBResult(errors=["Pass 5 — Narrative Generation"])
        combined = PipelineResult.from_ab(a, b)
        assert len(combined.errors) == 2


# ---------------------------------------------------------------------------
# Tests: Process A Runner
# ---------------------------------------------------------------------------


class TestProcessARunner:
    """Test Process A (variance math) independent execution."""

    @pytest.mark.asyncio
    async def test_process_a_runs_independently(self, process_a_runner, data_dir):
        """Process A completes without LLM client."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        assert isinstance(result, ProcessAResult)
        assert result.material_variances > 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_process_a_produces_material_variances(self, process_a_runner, data_dir):
        """Process A context contains material_variances DataFrame."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        import pandas as pd
        mv = result.context.get("material_variances")
        assert isinstance(mv, pd.DataFrame)
        assert not mv.empty

    @pytest.mark.asyncio
    async def test_process_a_produces_knowledge_graph(self, process_a_runner, data_dir):
        """Process A context contains knowledge_graph."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        assert "knowledge_graph" in result.context
        assert result.graph_node_count > 0
        assert result.graph_edge_count > 0

    @pytest.mark.asyncio
    async def test_process_a_no_narratives(self, process_a_runner, data_dir):
        """Process A does NOT produce narratives (that's Process B)."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        assert "narratives" not in result.context
        assert "review_status" not in result.context

    @pytest.mark.asyncio
    async def test_process_a_no_correlations(self, process_a_runner, data_dir):
        """Process A does NOT produce correlations (that's Process B)."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        assert "correlations" not in result.context

    @pytest.mark.asyncio
    async def test_process_a_timing_under_60s(self, process_a_runner, data_dir):
        """Process A completes in under 60 seconds."""
        start = time.monotonic()
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        elapsed = time.monotonic() - start
        assert elapsed < 60, f"Process A took {elapsed:.1f}s (budget: 60s)"

    @pytest.mark.asyncio
    async def test_process_a_has_pass_timings(self, process_a_runner, data_dir):
        """Process A records timing for each pass + knowledge graph."""
        result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        pass_names = [t.pass_name for t in result.timings]
        assert "Pass 1 — Raw Variance" in pass_names
        assert "Pass 3 — Decomposition" in pass_names
        assert any("Knowledge Graph" in n for n in pass_names)


# ---------------------------------------------------------------------------
# Tests: Process B Runner
# ---------------------------------------------------------------------------


class TestProcessBRunner:
    """Test Process B (intelligence + narratives) execution."""

    @pytest.mark.asyncio
    async def test_process_b_runs_with_context(self, process_a_runner, process_b_runner, data_dir):
        """Process B runs with Process A's context."""
        a_result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        b_result = await process_b_runner.run(
            context=a_result.context
        )
        assert isinstance(b_result, ProcessBResult)
        assert len(b_result.errors) == 0

    @pytest.mark.asyncio
    async def test_process_b_produces_narratives(self, process_a_runner, process_b_runner, data_dir):
        """Process B generates narratives."""
        a_result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        b_result = await process_b_runner.run(
            context=a_result.context
        )
        assert b_result.narratives_generated > 0

    @pytest.mark.asyncio
    async def test_process_b_produces_correlations(self, process_a_runner, process_b_runner, data_dir):
        """Process B generates correlations."""
        a_result = await process_a_runner.run(
            period_id="2026-06", data_dir=data_dir
        )
        b_result = await process_b_runner.run(
            context=a_result.context
        )
        assert b_result.correlations_found > 0

    @pytest.mark.asyncio
    async def test_process_b_from_disk(self, process_b_runner, data_dir):
        """Process B can load Process A output from disk."""
        b_result = await process_b_runner.run_from_disk(
            data_dir=data_dir, period_id="2026-06"
        )
        assert isinstance(b_result, ProcessBResult)
        assert b_result.narratives_generated > 0

    @pytest.mark.asyncio
    async def test_process_b_from_disk_no_output_raises(self, process_b_runner):
        """Process B raises FileNotFoundError when no Process A output."""
        with pytest.raises(FileNotFoundError, match="Process A output not found"):
            await process_b_runner.run_from_disk(
                data_dir="/nonexistent/path", period_id="2026-06"
            )


# ---------------------------------------------------------------------------
# Tests: Full Pipeline (Backward Compatibility)
# ---------------------------------------------------------------------------


class TestFullPipelineBackwardCompat:
    """Test that EngineRunner.run_full_pipeline remains backward compatible."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_pipeline_result(self, runner, data_dir):
        """Full pipeline returns PipelineResult (same type as before)."""
        result = await runner.run_full_pipeline(
            period_id="2026-06", data_dir=data_dir
        )
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_full_pipeline_has_all_counts(self, runner, data_dir):
        """Full pipeline populates all expected count fields."""
        result = await runner.run_full_pipeline(
            period_id="2026-06", data_dir=data_dir
        )
        assert result.total_variances_computed > 0
        assert result.material_variances > 0
        assert result.narratives_generated > 0

    @pytest.mark.asyncio
    async def test_full_pipeline_has_timings(self, runner, data_dir):
        """Full pipeline has timings from both Process A and B."""
        result = await runner.run_full_pipeline(
            period_id="2026-06", data_dir=data_dir
        )
        # Process A: 5 passes + KG. Process B: 2 passes. Total >= 7
        assert len(result.timings) >= 7

    @pytest.mark.asyncio
    async def test_full_pipeline_context_accessible(self, runner, data_dir):
        """_last_context is populated after full pipeline."""
        await runner.run_full_pipeline(
            period_id="2026-06", data_dir=data_dir
        )
        assert "material_variances" in runner._last_context
        assert "correlations" in runner._last_context


# ---------------------------------------------------------------------------
# Tests: Cost Estimator
# ---------------------------------------------------------------------------


class TestCostEstimator:
    """Test the LLM cost estimation helper."""

    def test_template_mode_zero_cost(self):
        """Template mode returns $0 cost."""
        est = estimate_process_b_cost(10000, mode="template")
        assert est["estimated_cost_usd"] == 0.0
        assert est["estimated_calls"] == 0

    def test_llm_mode_realistic_estimate(self):
        """LLM mode returns reasonable cost for 10K variances."""
        est = estimate_process_b_cost(10000, mode="llm")
        assert est["estimated_cost_usd"] > 0
        assert est["estimated_calls"] > 0
        assert est["estimated_time_minutes"] > 0
        # Empirically ~$55 for 10K variances
        assert 10 < est["estimated_cost_usd"] < 200

    def test_cost_scales_with_material_count(self):
        """Higher material count → higher cost."""
        small = estimate_process_b_cost(1000, mode="llm")
        large = estimate_process_b_cost(10000, mode="llm")
        assert large["estimated_cost_usd"] > small["estimated_cost_usd"]

    def test_breakdown_has_expected_keys(self):
        """Breakdown dict has all stage keys."""
        est = estimate_process_b_cost(5000, mode="llm")
        expected = {"leaves", "parents", "sections", "executive", "correlation_hypotheses"}
        assert set(est["breakdown"].keys()) == expected

    def test_format_cost_summary(self):
        """format_cost_summary returns a readable string."""
        est = estimate_process_b_cost(10000, mode="llm")
        summary = format_cost_summary(est)
        assert "Process B Cost Estimate" in summary
        assert "$" in summary
        assert "minutes" in summary

    def test_zero_material_count(self):
        """Zero material variances → zero cost."""
        est = estimate_process_b_cost(0, mode="llm")
        assert est["estimated_cost_usd"] == 0.0
        assert est["estimated_calls"] == 0
