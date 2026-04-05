#!/usr/bin/env python3
"""CLI entry point for running the 5.5-pass computation engine.

Phase 3B: Supports independent execution of Process A and Process B.

Usage:
    # Full pipeline (backward compatible)
    python scripts/run_engine.py --period 2026-06

    # Process A only (variance math, no LLM, ~15-20s)
    python scripts/run_engine.py --period 2026-06 --process a

    # Process B only (narratives, requires prior Process A output)
    python scripts/run_engine.py --period 2026-06 --process b

    # Multi-period with LLM from a specific month
    python scripts/run_engine.py --multi-period --llm-from 2026-04

    # Cost estimate before running Process B
    python scripts/run_engine.py --period 2026-06 --process b --estimate-cost
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env for API keys (override=True to replace empty shell env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from services.computation.engine.runner import EngineRunner


def main() -> None:
    """Run the computation engine."""
    parser = argparse.ArgumentParser(
        description="Run the 5.5-pass variance computation engine"
    )
    parser.add_argument(
        "--period",
        default="2026-06",
        help="Analysis period (default: 2026-06). Use --multi-period for 12-month run.",
    )
    parser.add_argument(
        "--multi-period",
        action="store_true",
        help="Run engine for 12 trailing periods (e.g. 2025-07 through 2026-06)",
    )
    parser.add_argument(
        "--data-dir",
        default="data/output",
        help="Data directory (default: data/output)",
    )
    parser.add_argument(
        "--llm-from",
        default=None,
        help="Enable LLM from this period onwards (e.g. --llm-from 2026-04). Earlier periods use templates.",
    )
    parser.add_argument(
        "--process",
        choices=["a", "b", "full"],
        default="full",
        help="Which process to run: 'a' (math only), 'b' (narratives only), 'full' (both, default)",
    )
    parser.add_argument(
        "--estimate-cost",
        action="store_true",
        help="Print cost estimate before running Process B, then exit.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Determine periods to run
    if args.multi_period:
        from datetime import datetime as _dt
        end = _dt.strptime(args.period, "%Y-%m")
        periods = []
        for i in range(11, -1, -1):
            month = end.month - i
            year = end.year
            while month <= 0:
                month += 12
                year -= 1
            periods.append(f"{year}-{month:02d}")
    else:
        periods = [args.period]

    process_label = {
        "a": "Process A (variance math only)",
        "b": "Process B (narratives only)",
        "full": "Full Pipeline (Process A + B)",
    }

    print("5.5-Pass Computation Engine")
    print(f"  Mode:     {process_label[args.process]}")
    print(f"  Periods:  {len(periods)} ({periods[0]} to {periods[-1]})")
    print(f"  Data:     {args.data_dir}")

    # Cost estimation (--estimate-cost)
    if args.estimate_cost:
        _print_cost_estimate(args.data_dir, periods)
        return

    # Initialize LLM + RAG if needed (not for Process A)
    llm_client = None
    rag_retriever = None
    if args.process != "a":
        llm_client, rag_retriever = _init_llm()
    else:
        print("  LLM:      skipped (Process A is LLM-free)")

    print()

    import pandas as pd

    # Load existing data for narrative preservation
    _out = Path(args.data_dir)
    existing_review_status = None
    existing_material = None
    try:
        rs_path = _out / "fact_review_status.parquet"
        if rs_path.exists():
            existing_review_status = pd.read_parquet(rs_path)
            approved = existing_review_status[existing_review_status["status"].isin(["APPROVED", "ANALYST_REVIEWED"])]
            print(f"  Existing: {len(existing_review_status)} review records ({len(approved)} approved/reviewed — will preserve)")
        vm_path = _out / "fact_variance_material.parquet"
        if vm_path.exists():
            existing_material = pd.read_parquet(vm_path)
    except Exception as exc:
        print(f"  Warning: Could not load existing data for preservation: {exc}")

    runner = EngineRunner()
    all_material = []
    all_decomposition = []
    all_netting = []
    all_trend = []
    all_correlations = []
    all_review = []
    all_section_narratives = []
    all_executive_summaries = []

    for i, period in enumerate(periods):
        print(f"\n--- Running period: {period} ({i+1}/{len(periods)}) ---")

        # Build cumulative material for carry-forward
        if i > 0 and all_material:
            cumulative_material = pd.concat(
                [existing_material] + all_material if existing_material is not None else all_material,
                ignore_index=True,
            )
        else:
            cumulative_material = existing_material

        # Determine LLM usage for this period
        use_llm = llm_client if (args.llm_from and period >= args.llm_from) else None

        if args.process == "a":
            # ---- Process A only ----
            result = asyncio.run(runner.run_process_a(
                period_id=period,
                data_dir=args.data_dir,
                existing_review_status=existing_review_status,
                existing_material=cumulative_material,
                save_intermediate=True,
            ))
            ctx = runner._last_context
            print(f"  Process A: {result.material_variances:,} material, "
                  f"{result.graph_node_count:,} graph nodes, {len(result.errors)} errors")

        elif args.process == "b":
            # ---- Process B only (from disk) ----
            if use_llm:
                print(f"  LLM: ENABLED (period >= {args.llm_from})")
            else:
                print(f"  LLM: template mode")

            b_result = asyncio.run(runner.run_process_b(
                data_dir=args.data_dir,
                period_id=period,
                llm_client=use_llm,
                rag_retriever=rag_retriever if use_llm else None,
                existing_review_status=existing_review_status,
                existing_material=cumulative_material,
            ))
            ctx = runner._last_context
            print(f"  Process B: {b_result.narratives_generated:,} narratives, "
                  f"{b_result.correlations_found:,} correlations, {len(b_result.errors)} errors")

        else:
            # ---- Full pipeline ----
            if use_llm:
                print(f"  LLM: ENABLED (period >= {args.llm_from})")
            else:
                print(f"  LLM: template mode")

            result = asyncio.run(runner.run_full_pipeline(
                period_id=period,
                data_dir=args.data_dir,
                llm_client=use_llm,
                rag_retriever=rag_retriever if use_llm else None,
                existing_review_status=existing_review_status,
                existing_material=cumulative_material,
            ))
            ctx = runner._last_context
            print(f"  Material: {result.material_variances:,}, Errors: {len(result.errors)}")

        # Collect outputs from context
        if ctx:
            _collect_outputs(ctx, all_material, all_decomposition, all_netting,
                            all_trend, all_correlations, all_review,
                            all_section_narratives, all_executive_summaries)

    # Print timings from last run
    _print_timings(runner)

    # Concatenate and save
    _save_all_outputs(args.data_dir, all_material, all_decomposition, all_netting,
                      all_trend, all_correlations, all_review,
                      all_section_narratives, all_executive_summaries)

    print("\nEngine run complete.")


def _init_llm():
    """Initialize LLM client and RAG retriever. Returns (llm_client, rag_retriever)."""
    llm_client = None
    rag_retriever = None
    try:
        from shared.llm.client import LLMClient
        from shared.knowledge.embedding import EmbeddingService
        from shared.knowledge.vector_store import create_vector_store
        from shared.knowledge.rag import RAGRetriever

        llm_client = LLMClient()
        if llm_client.is_available:
            print(f"  LLM:      {llm_client.provider} (available)")
            embedding_svc = EmbeddingService()
            vector_store = create_vector_store(qdrant_url=None)
            rag_retriever = RAGRetriever(embedding_svc, vector_store)
        else:
            print("  LLM:      unavailable (template mode)")
            llm_client = None
    except Exception as exc:
        print(f"  LLM:      initialization failed ({exc})")
    return llm_client, rag_retriever


def _print_cost_estimate(data_dir: str, periods: list[str]) -> None:
    """Print cost estimate for Process B and exit."""
    from shared.engine.cost_estimator import (
        estimate_process_b_cost,
        format_cost_summary,
    )
    import pandas as pd

    out = Path(data_dir)
    vm_path = out / "fact_variance_material.parquet"
    if not vm_path.exists():
        print("\n  No Process A output found. Run --process a first.")
        return

    material = pd.read_parquet(vm_path)
    for period in periods:
        period_material = material[material["period_id"] == period] if "period_id" in material.columns else material
        est = estimate_process_b_cost(len(period_material), mode="llm")
        print(f"\n  Period {period}:")
        print(f"    {format_cost_summary(est)}")

    total_est = estimate_process_b_cost(len(material), mode="llm")
    print(f"\n  ALL PERIODS:")
    print(f"    {format_cost_summary(total_est)}")


def _collect_outputs(ctx, all_material, all_decomposition, all_netting,
                     all_trend, all_correlations, all_review,
                     all_section_narratives, all_executive_summaries):
    """Collect outputs from context into accumulator lists."""
    import pandas as pd

    mv = ctx.get("material_variances")
    if isinstance(mv, pd.DataFrame) and not mv.empty:
        all_material.append(mv)

    for key, acc in [
        ("decomposition", all_decomposition),
        ("netting_flags", all_netting),
        ("trend_flags", all_trend),
        ("correlations", all_correlations),
        ("review_status", all_review),
    ]:
        data = ctx.get(key)
        if isinstance(data, list) and data:
            data = pd.DataFrame(data)
        if isinstance(data, pd.DataFrame) and not data.empty:
            acc.append(data)

    sn = ctx.get("section_narratives")
    if isinstance(sn, list) and sn:
        all_section_narratives.extend(sn)
    es = ctx.get("executive_summary")
    if isinstance(es, dict) and es:
        all_executive_summaries.append(es)


def _print_timings(runner):
    """Print timing summary from the last engine run."""
    ctx = runner._last_context
    if not ctx:
        return

    # Get timings from the runner's process objects
    if hasattr(runner, 'process_a') and hasattr(runner, 'process_b'):
        print("\n=== Process Timings ===")
        # Access via the last full pipeline result if available
    print()


def _save_all_outputs(data_dir, all_material, all_decomposition, all_netting,
                      all_trend, all_correlations, all_review,
                      all_section_narratives, all_executive_summaries):
    """Concatenate and save all collected outputs."""
    import pandas as pd
    out = Path(data_dir)

    concat_tables = {
        "fact_variance_material": all_material,
        "fact_decomposition": all_decomposition,
        "fact_netting_flags": all_netting,
        "fact_trend_flags": all_trend,
        "fact_correlations": all_correlations,
        "fact_review_status": all_review,
    }

    for name, frames in concat_tables.items():
        if not frames:
            continue
        combined = pd.concat(frames, ignore_index=True)
        combined.to_parquet(out / f"{name}.parquet", index=False)
        combined.to_csv(out / f"{name}.csv", index=False)
        print(f"  Saved {name}: {len(combined):,} rows")

    if all_section_narratives:
        sn_df = pd.DataFrame(all_section_narratives)
        sn_df.to_parquet(out / "fact_section_narrative.parquet", index=False)
        sn_df.to_csv(out / "fact_section_narrative.csv", index=False)
        print(f"  Saved fact_section_narrative: {len(sn_df):,} rows")

    if all_executive_summaries:
        es_df = pd.DataFrame(all_executive_summaries)
        es_df.to_parquet(out / "fact_executive_summary.parquet", index=False)
        es_df.to_csv(out / "fact_executive_summary.csv", index=False)
        print(f"  Saved fact_executive_summary: {len(es_df):,} rows")


if __name__ == "__main__":
    main()
