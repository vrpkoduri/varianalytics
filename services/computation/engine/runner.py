"""Engine Runner — orchestrates the 5.5-pass materiality-first pipeline.

Phase 3B: Separated into Process A (variance math) and Process B
(intelligence & narratives) for independent execution.

Process A (Pure Math, no LLM):
    Pass 1   — Raw variance at ALL intersections.
    Pass 1.5 — Netting detection (4 checks).
    Pass 2.5 — Trend detection (2 rules).
    Pass 2   — Threshold filter (OR logic).
    Pass 3   — Decomposition (Vol/Price/Mix/FX).
    —        — Knowledge Graph build.

Process B (Intelligence, LLM optional):
    Pass 4   — Correlation + root cause (scoring + LLM hypothesis).
    Pass 5   — Multi-level narrative generation (4 stages).

Execution modes:
    - ``run_full_pipeline()`` — Process A + B (backward compatible).
    - ``run_process_a()``     — Math only, no LLM, ~15-20s.
    - ``run_process_b()``     — Narratives only, from context or disk.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from services.computation.engine.pass1_variance import compute_raw_variances
from services.computation.engine.pass15_netting import detect_netting
from services.computation.engine.pass2_threshold import apply_threshold_filter
from services.computation.engine.pass25_trend import detect_trends
from services.computation.engine.pass3_decomposition import decompose_variances
from services.computation.engine.pass4_correlation import find_correlations
from services.computation.engine.pass5_narrative import generate_narratives
from shared.knowledge.graph_builder import build_variance_graph

logger = logging.getLogger("computation.engine")


# ======================================================================
# Result Dataclasses
# ======================================================================


@dataclass
class PassTiming:
    """Tracks execution time for each pass."""

    pass_name: str
    elapsed_seconds: float = 0.0


@dataclass
class ProcessAResult:
    """Output from Process A (variance math passes).

    Contains the full context dict that Process B can consume directly.
    """

    context: dict[str, Any] = field(default_factory=dict)
    total_variances: int = 0
    material_variances: int = 0
    netted_nodes: int = 0
    trending_variances: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    timings: list[PassTiming] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ProcessBResult:
    """Output from Process B (intelligence + narrative passes)."""

    context: dict[str, Any] = field(default_factory=dict)
    narratives_generated: int = 0
    correlations_found: int = 0
    timings: list[PassTiming] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Aggregate result from a full engine run (Process A + B).

    Backward compatible with all existing consumers.
    """

    total_variances_computed: int = 0
    material_variances: int = 0
    netted_nodes: int = 0
    trending_variances: int = 0
    narratives_generated: int = 0
    timings: list[PassTiming] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_ab(cls, a: ProcessAResult, b: ProcessBResult) -> PipelineResult:
        """Combine Process A + B results into a unified PipelineResult."""
        return cls(
            total_variances_computed=a.total_variances,
            material_variances=a.material_variances,
            netted_nodes=a.netted_nodes,
            trending_variances=a.trending_variances,
            narratives_generated=b.narratives_generated,
            timings=a.timings + b.timings,
            errors=a.errors + b.errors,
        )


# ======================================================================
# Process A: Variance Math (Pure Deterministic)
# ======================================================================


class ProcessARunner:
    """Runs variance math passes (1 -> 1.5 -> 2.5 -> 2 -> 3 -> Knowledge Graph).

    Pure deterministic computation. No LLM calls.
    Runtime: ~15-20 seconds per period.
    Cost: $0.

    Produces material_variances, decomposition, netting/trend flags,
    and a knowledge graph — everything Process B needs.
    """

    async def run(
        self,
        period_id: str,
        view: str = "MTD",
        comparison_base: str = "Budget",
        bu_id: Optional[str] = None,
        data_dir: str = "data/output",
        existing_review_status: Any = None,
        existing_material: Any = None,
        save_intermediate: bool = False,
    ) -> ProcessAResult:
        """Execute Process A: variance math passes.

        Args:
            period_id: Target period (e.g. '2026-06').
            view: Aggregation window (MTD/QTD/YTD).
            comparison_base: Comparator (Budget/Forecast/PY).
            bu_id: Optional BU filter.
            data_dir: Data output directory.
            existing_review_status: Prior review status for preservation.
            existing_material: Prior material variances for carry-forward.
            save_intermediate: If True, save Process A output to disk
                so Process B can load it later.

        Returns:
            ProcessAResult with context dict and counts.
        """
        result = ProcessAResult()
        context: dict[str, Any] = {
            "period_id": period_id,
            "view": view,
            "comparison_base": comparison_base,
            "bu_id": bu_id,
            "data_dir": data_dir,
            "existing_review_status": existing_review_status,
            "existing_material": existing_material,
        }

        # Process A passes: 1 → 1.5 → 2.5 → 2 → 3
        passes = [
            ("Pass 1 — Raw Variance", compute_raw_variances),
            ("Pass 1.5 — Netting Detection", detect_netting),
            ("Pass 2.5 — Trend Detection", detect_trends),
            ("Pass 2 — Threshold Filter", apply_threshold_filter),
            ("Pass 3 — Decomposition", decompose_variances),
        ]

        for pass_name, pass_fn in passes:
            logger.info("[Process A] Starting %s", pass_name)
            start = time.monotonic()
            try:
                await pass_fn(context)
            except Exception:
                logger.exception("[Process A] Error in %s", pass_name)
                result.errors.append(pass_name)
            elapsed = time.monotonic() - start
            result.timings.append(PassTiming(pass_name=pass_name, elapsed_seconds=elapsed))
            logger.info("[Process A] Completed %s in %.3f s", pass_name, elapsed)

        # Build knowledge graph (end of Process A)
        kg_start = time.monotonic()
        try:
            context["knowledge_graph"] = build_variance_graph(context)
            kg_elapsed = time.monotonic() - kg_start
            result.timings.append(
                PassTiming(pass_name="Knowledge Graph Build", elapsed_seconds=kg_elapsed)
            )
            kg = context["knowledge_graph"]
            result.graph_node_count = kg.node_count()
            result.graph_edge_count = kg.edge_count()
            logger.info(
                "[Process A] Knowledge graph built in %.3f s (%d nodes, %d edges)",
                kg_elapsed, result.graph_node_count, result.graph_edge_count,
            )
        except Exception:
            logger.exception("[Process A] Knowledge graph build failed")
            kg_elapsed = time.monotonic() - kg_start
            result.timings.append(
                PassTiming(pass_name="Knowledge Graph Build (failed)", elapsed_seconds=kg_elapsed)
            )
            result.errors.append("Knowledge Graph Build")

        # Populate result counts
        if "all_variances" in context:
            result.total_variances = len(context["all_variances"])
        if "material_variances" in context:
            result.material_variances = len(context["material_variances"])
        if "netting_flags" in context:
            result.netted_nodes = len(context["netting_flags"])
        if "trend_flags" in context:
            result.trending_variances = len(context["trend_flags"])

        result.context = context

        # Optional intermediate save
        if save_intermediate:
            self._save_intermediate(context, data_dir)

        total_time = sum(t.elapsed_seconds for t in result.timings)
        logger.info(
            "[Process A] Complete — %d material variances, %.1f s, %d errors",
            result.material_variances, total_time, len(result.errors),
        )
        return result

    @staticmethod
    def _save_intermediate(context: dict[str, Any], data_dir: str) -> None:
        """Save Process A output tables to disk for later Process B consumption."""
        out = Path(data_dir)
        tables = {
            "fact_variance_material": context.get("material_variances"),
            "fact_decomposition": context.get("decomposition"),
            "fact_netting_flags": context.get("netting_flags"),
            "fact_trend_flags": context.get("trend_flags"),
        }

        for name, data in tables.items():
            if data is None:
                continue
            if isinstance(data, list) and data:
                data = pd.DataFrame(data)
            if isinstance(data, pd.DataFrame) and not data.empty:
                data.to_parquet(out / f"{name}.parquet", index=False)
                data.to_csv(out / f"{name}.csv", index=False)
                logger.info("[Process A] Saved %s: %d rows", name, len(data))


# ======================================================================
# Process B: Intelligence & Narratives (LLM optional)
# ======================================================================


class ProcessBRunner:
    """Runs intelligence + narrative passes (Pass 4 → Pass 5).

    Uses LLM or templates for narrative generation.
    Can consume Process A context directly or load from disk.

    Runtime: ~3 min (template) to ~100 min (LLM) per period.
    Cost: ~$55/period (LLM), $0 (template).
    """

    async def run(
        self,
        context: dict[str, Any],
        llm_client: Any = None,
        rag_retriever: Any = None,
    ) -> ProcessBResult:
        """Execute Process B using a pre-built context from Process A.

        Args:
            context: Pipeline context dict from ProcessAResult.context.
                Must contain material_variances, decomposition, etc.
            llm_client: Optional LLM client for narrative generation.
            rag_retriever: Optional RAG retriever for few-shot examples.

        Returns:
            ProcessBResult with narrative counts and timings.
        """
        result = ProcessBResult()

        # Inject LLM + RAG into context for Pass 4 and 5
        context["llm_client"] = llm_client
        context["rag_retriever"] = rag_retriever

        passes = [
            ("Pass 4 — Correlation & Root Cause", find_correlations),
            ("Pass 5 — Narrative Generation", generate_narratives),
        ]

        for pass_name, pass_fn in passes:
            logger.info("[Process B] Starting %s", pass_name)
            start = time.monotonic()
            try:
                await pass_fn(context)
            except Exception:
                logger.exception("[Process B] Error in %s", pass_name)
                result.errors.append(pass_name)
            elapsed = time.monotonic() - start
            result.timings.append(PassTiming(pass_name=pass_name, elapsed_seconds=elapsed))
            logger.info("[Process B] Completed %s in %.3f s", pass_name, elapsed)

        # Populate result counts
        if "correlations" in context:
            corr = context["correlations"]
            result.correlations_found = len(corr) if isinstance(corr, (pd.DataFrame, list)) else 0
        if "narratives" in context:
            result.narratives_generated = len(context["narratives"])

        result.context = context

        total_time = sum(t.elapsed_seconds for t in result.timings)
        logger.info(
            "[Process B] Complete — %d narratives, %d correlations, %.1f s, %d errors",
            result.narratives_generated, result.correlations_found,
            total_time, len(result.errors),
        )
        return result

    async def run_from_disk(
        self,
        data_dir: str,
        period_id: str,
        view: str = "MTD",
        comparison_base: str = "Budget",
        bu_id: Optional[str] = None,
        llm_client: Any = None,
        rag_retriever: Any = None,
        existing_review_status: Any = None,
        existing_material: Any = None,
    ) -> ProcessBResult:
        """Load Process A output from disk and run Process B.

        Use this when Process A was run separately (e.g. via CLI --process a)
        and you want to generate narratives later.

        Args:
            data_dir: Directory with Process A parquet output.
            period_id: Target period.
            llm_client: Optional LLM client.
            rag_retriever: Optional RAG retriever.

        Returns:
            ProcessBResult.

        Raises:
            FileNotFoundError: If Process A output files don't exist.
        """
        from shared.data.loader import DataLoader

        loader = DataLoader(data_dir)

        # Verify Process A output exists
        required = "fact_variance_material"
        if not loader.table_exists(required):
            raise FileNotFoundError(
                f"Process A output not found: {data_dir}/{required}.parquet. "
                "Run Process A first (--process a)."
            )

        # Reconstruct context from disk
        material = loader.load_table("fact_variance_material")

        # Filter to target period if specified
        if period_id and "period_id" in material.columns:
            material = material[material["period_id"] == period_id]

        # Build acct_meta from dim_account
        dim_account = loader.load_table("dim_account") if loader.table_exists("dim_account") else pd.DataFrame()
        acct_meta: dict[str, dict] = {}
        if not dim_account.empty:
            for _, row in dim_account.iterrows():
                acct_id = str(row.get("account_id", ""))
                acct_meta[acct_id] = {
                    "account_id": acct_id,
                    "account_name": str(row.get("account_name", acct_id)),
                    "parent_id": row.get("parent_id"),
                    "pl_category": str(row.get("pl_category", "")),
                    "variance_sign": str(row.get("variance_sign", "natural")),
                    "is_calculated": bool(row.get("is_calculated", False)),
                }

        context: dict[str, Any] = {
            "period_id": period_id,
            "view": view,
            "comparison_base": comparison_base,
            "bu_id": bu_id,
            "data_dir": data_dir,
            "material_variances": material,
            "acct_meta": acct_meta,
            "decomposition": loader.load_table("fact_decomposition") if loader.table_exists("fact_decomposition") else pd.DataFrame(),
            "netting_flags": loader.load_table("fact_netting_flags") if loader.table_exists("fact_netting_flags") else pd.DataFrame(),
            "trend_flags": loader.load_table("fact_trend_flags") if loader.table_exists("fact_trend_flags") else pd.DataFrame(),
            "existing_review_status": existing_review_status,
            "existing_material": existing_material,
        }

        # Build knowledge graph from loaded data
        try:
            context["knowledge_graph"] = build_variance_graph(context)
        except Exception:
            logger.warning("[Process B] Could not build knowledge graph from disk data")

        logger.info(
            "[Process B] Loaded Process A output from disk: %d material variances",
            len(material),
        )

        return await self.run(context, llm_client=llm_client, rag_retriever=rag_retriever)


# ======================================================================
# EngineRunner: Orchestrator (Backward Compatible)
# ======================================================================


class EngineRunner:
    """Orchestrates the full variance analysis pipeline.

    Supports three execution modes:
        1. ``run_full_pipeline()``  — Process A + B (backward compatible)
        2. ``run_process_a()``      — Math only, no LLM
        3. ``run_process_b()``      — Narratives only, from context or disk

    Usage::

        runner = EngineRunner()

        # Full pipeline (backward compatible)
        result = await runner.run_full_pipeline(period_id="2026-06")

        # Process A only (fast, deterministic)
        a_result = await runner.run_process_a(period_id="2026-06")

        # Process B only (from prior Process A output)
        b_result = await runner.run_process_b(a_result.context, llm_client=client)
    """

    def __init__(self) -> None:
        self.process_a = ProcessARunner()
        self.process_b = ProcessBRunner()
        self._last_context: dict[str, Any] = {}

    async def run_full_pipeline(
        self,
        period_id: str,
        view: str = "MTD",
        comparison_base: str = "Budget",
        bu_id: str | None = None,
        data_dir: str = "data/output",
        llm_client: Any | None = None,
        rag_retriever: Any | None = None,
        existing_review_status: Any | None = None,
        existing_material: Any | None = None,
    ) -> PipelineResult:
        """Execute full pipeline: Process A + Process B.

        Backward compatible with all existing callers.

        Args:
            period_id: Target period key (e.g. '2026-03').
            view: Aggregation window — MTD, QTD, or YTD.
            comparison_base: Comparison column — Budget, Forecast, or PY.
            bu_id: Optional filter to a single business unit.
            data_dir: Path to data output directory.
            llm_client: Optional LLM client for narrative/hypothesis generation.
            rag_retriever: Optional RAG retriever for few-shot examples.
            existing_review_status: Prior review data for narrative preservation.
            existing_material: Prior material data for carry-forward.

        Returns:
            PipelineResult with counts, timings, and any errors.
        """
        # Process A: variance math
        a_result = await self.process_a.run(
            period_id=period_id,
            view=view,
            comparison_base=comparison_base,
            bu_id=bu_id,
            data_dir=data_dir,
            existing_review_status=existing_review_status,
            existing_material=existing_material,
        )

        # Process B: intelligence + narratives
        b_result = await self.process_b.run(
            context=a_result.context,
            llm_client=llm_client,
            rag_retriever=rag_retriever,
        )

        # Store combined context for external access
        self._last_context = b_result.context

        # Combine results
        pipeline_result = PipelineResult.from_ab(a_result, b_result)

        logger.info(
            "Full pipeline complete — %d material variances, %d narratives, %d errors",
            pipeline_result.material_variances,
            pipeline_result.narratives_generated,
            len(pipeline_result.errors),
        )

        return pipeline_result

    async def run_process_a(
        self,
        period_id: str,
        view: str = "MTD",
        comparison_base: str = "Budget",
        bu_id: str | None = None,
        data_dir: str = "data/output",
        existing_review_status: Any | None = None,
        existing_material: Any | None = None,
        save_intermediate: bool = False,
    ) -> ProcessAResult:
        """Run only Process A (variance math). No LLM.

        Args:
            period_id: Target period.
            save_intermediate: Save output to disk for later Process B.

        Returns:
            ProcessAResult with context and counts.
        """
        result = await self.process_a.run(
            period_id=period_id,
            view=view,
            comparison_base=comparison_base,
            bu_id=bu_id,
            data_dir=data_dir,
            existing_review_status=existing_review_status,
            existing_material=existing_material,
            save_intermediate=save_intermediate,
        )
        self._last_context = result.context
        return result

    async def run_process_b(
        self,
        context: dict[str, Any] | None = None,
        data_dir: str | None = None,
        period_id: str | None = None,
        llm_client: Any | None = None,
        rag_retriever: Any | None = None,
        existing_review_status: Any | None = None,
        existing_material: Any | None = None,
    ) -> ProcessBResult:
        """Run only Process B (intelligence + narratives).

        Either provide a context dict (from Process A) or a data_dir +
        period_id to load from disk.

        Args:
            context: Process A context dict. If None, loads from disk.
            data_dir: Data directory (required if context is None).
            period_id: Period (required if context is None).
            llm_client: Optional LLM client.
            rag_retriever: Optional RAG retriever.

        Returns:
            ProcessBResult.
        """
        if context is not None:
            result = await self.process_b.run(
                context=context,
                llm_client=llm_client,
                rag_retriever=rag_retriever,
            )
        elif data_dir and period_id:
            result = await self.process_b.run_from_disk(
                data_dir=data_dir,
                period_id=period_id,
                llm_client=llm_client,
                rag_retriever=rag_retriever,
                existing_review_status=existing_review_status,
                existing_material=existing_material,
            )
        else:
            raise ValueError(
                "Either 'context' or 'data_dir' + 'period_id' must be provided."
            )
        self._last_context = result.context
        return result
