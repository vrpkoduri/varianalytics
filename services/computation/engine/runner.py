"""Engine Runner — orchestrates the 5.5-pass materiality-first pipeline.

Pass sequence:
    Pass 1   — Raw variance at ALL intersections. Calculated rows
               (Gross Profit, EBITDA, EBIT, EBT, Net Income) resolved
               in dependency order AFTER rollup.
    Pass 1.5 — Netting detection: 6 checks (MVP: 1-4). Summary nodes
               below threshold that mask offsetting child variances.
    Pass 2   — Threshold filter (OR logic). Three qualification types:
               material, netted, trending.
    Pass 2.5 — Trend detection: 4 rules (MVP: 1-2). Identifies
               consecutive-period and acceleration patterns.
    Pass 3   — Decomposition: Revenue (Vol x Price x Mix x FX),
               COGS (Rate x Vol x Mix), OpEx (Rate x Vol x Timing x Onetime).
               Fallback methods when unit data unavailable.
    Pass 4   — Correlation + root cause: pairwise scan of material
               variances, batched LLM hypothesis generation.
    Pass 5   — RAG-enhanced multi-level narrative generation
               (detail / midlevel / summary / oneliner; board on-demand).
               Creates fact_review_status entries as AI_DRAFT.
               Logs to audit_log.

Post-engine:
    - Notifications dispatched (Teams / Slack webhooks).
    - Synthesis runs separately, triggered by analyst approval.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from services.computation.engine.pass1_variance import compute_raw_variances
from services.computation.engine.pass15_netting import detect_netting
from services.computation.engine.pass2_threshold import apply_threshold_filter
from services.computation.engine.pass25_trend import detect_trends
from services.computation.engine.pass3_decomposition import decompose_variances
from services.computation.engine.pass4_correlation import find_correlations
from services.computation.engine.pass5_narrative import generate_narratives

logger = logging.getLogger("computation.engine")


@dataclass
class PassTiming:
    """Tracks execution time for each pass."""

    pass_name: str
    elapsed_seconds: float = 0.0


@dataclass
class PipelineResult:
    """Aggregate result from a full engine run."""

    total_variances_computed: int = 0
    material_variances: int = 0
    netted_nodes: int = 0
    trending_variances: int = 0
    narratives_generated: int = 0
    timings: list[PassTiming] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EngineRunner:
    """Orchestrates the 5.5-pass materiality-first computation pipeline.

    Usage::

        runner = EngineRunner()
        result = await runner.run_full_pipeline(
            period_id="2026-03",
            view="MTD",
            comparison_base="Budget",
        )
    """

    async def run_full_pipeline(
        self,
        period_id: str,
        view: str = "MTD",
        comparison_base: str = "Budget",
        bu_id: str | None = None,
        data_dir: str = "data/output",
    ) -> PipelineResult:
        """Execute all passes of the computation engine in sequence.

        Args:
            period_id: Target period key (e.g. '2026-03').
            view: Aggregation window — MTD, QTD, or YTD.
            comparison_base: Comparison column — Budget, Forecast, or PY.
            bu_id: Optional filter to a single business unit.

        Returns:
            PipelineResult with counts, timings, and any errors.
        """
        result = PipelineResult()
        context: dict[str, Any] = {
            "period_id": period_id,
            "view": view,
            "comparison_base": comparison_base,
            "bu_id": bu_id,
            "data_dir": data_dir,
        }

        # Order: 1 → 1.5 → 2.5 → 2 → 3 → 4 → 5
        # Pass 2.5 (trend) runs BEFORE Pass 2 (threshold) so that
        # trending variances are included in the OR filter.
        passes = [
            ("Pass 1 — Raw Variance", compute_raw_variances),
            ("Pass 1.5 — Netting Detection", detect_netting),
            ("Pass 2.5 — Trend Detection", detect_trends),
            ("Pass 2 — Threshold Filter", apply_threshold_filter),
            ("Pass 3 — Decomposition", decompose_variances),
            ("Pass 4 — Correlation & Root Cause", find_correlations),
            ("Pass 5 — Narrative Generation", generate_narratives),
        ]

        for pass_name, pass_fn in passes:
            logger.info("Starting %s", pass_name)
            start = time.monotonic()
            try:
                await pass_fn(context)
            except Exception:
                logger.exception("Error in %s", pass_name)
                result.errors.append(pass_name)
            elapsed = time.monotonic() - start
            result.timings.append(PassTiming(pass_name=pass_name, elapsed_seconds=elapsed))
            logger.info("Completed %s in %.3f s", pass_name, elapsed)

        # Populate result counts from context
        if "all_variances" in context:
            result.total_variances_computed = len(context["all_variances"])
        if "material_variances" in context:
            mv = context["material_variances"]
            result.material_variances = len(mv)
        if "netting_flags" in context:
            result.netted_nodes = len(context["netting_flags"])
        if "trend_flags" in context:
            result.trending_variances = len(context["trend_flags"])
        if "narratives" in context:
            result.narratives_generated = len(context["narratives"])

        # Store context for external access
        self._last_context = context

        logger.info(
            "Pipeline complete — %d passes, %d errors, %d material variances",
            len(passes),
            len(result.errors),
            result.material_variances,
        )
        return result
