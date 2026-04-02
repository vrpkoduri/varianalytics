#!/usr/bin/env python3
"""CLI entry point for running the 5.5-pass computation engine.

Usage:
    python scripts/run_engine.py [--period 2026-06] [--data-dir data/output]

Runs the full engine pipeline on synthetic data and outputs enriched tables.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Determine periods to run
    if args.multi_period:
        # Generate 12 trailing months ending at the specified period
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

    print("5.5-Pass Computation Engine")
    print(f"  Periods:  {len(periods)} ({periods[0]} to {periods[-1]})")
    print(f"  Data:     {args.data_dir}")
    print()

    # Initialize LLM + RAG if API key available
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

    print()

    import pandas as pd
    from pathlib import Path as _Path

    # Load existing data for narrative preservation
    _out = _Path(args.data_dir)
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
    total_result = None

    for period in periods:
        print(f"\n--- Running period: {period} ---")
        result = asyncio.run(runner.run_full_pipeline(
            period_id=period,
            data_dir=args.data_dir,
            llm_client=llm_client,
            rag_retriever=rag_retriever,
            existing_review_status=existing_review_status,
            existing_material=existing_material,
        ))

        ctx = runner._last_context
        if ctx:
            mv = ctx.get("material_variances")
            if isinstance(mv, pd.DataFrame) and not mv.empty:
                all_material.append(mv)
            dec = ctx.get("decomposition")
            if isinstance(dec, (pd.DataFrame, list)):
                if isinstance(dec, list) and dec:
                    dec = pd.DataFrame(dec)
                if isinstance(dec, pd.DataFrame) and not dec.empty:
                    all_decomposition.append(dec)
            nf = ctx.get("netting_flags")
            if isinstance(nf, pd.DataFrame) and not nf.empty:
                all_netting.append(nf)
            tf = ctx.get("trend_flags")
            if isinstance(tf, pd.DataFrame) and not tf.empty:
                all_trend.append(tf)
            cr = ctx.get("correlations")
            if isinstance(cr, (pd.DataFrame, list)):
                if isinstance(cr, list) and cr:
                    cr = pd.DataFrame(cr)
                if isinstance(cr, pd.DataFrame) and not cr.empty:
                    all_correlations.append(cr)
            rv = ctx.get("review_status")
            if isinstance(rv, (pd.DataFrame, list)):
                if isinstance(rv, list) and rv:
                    rv = pd.DataFrame(rv)
                if isinstance(rv, pd.DataFrame) and not rv.empty:
                    all_review.append(rv)

        total_result = result
        print(f"  Material: {result.material_variances:,}, Errors: {len(result.errors)}")

    # Print final results
    print("\n=== Pipeline Results (all periods) ===")
    print(f"  Periods processed:        {len(periods)}")
    print(f"  Total material rows:      {sum(len(df) for df in all_material):,}")

    if total_result:
        print("\n=== Last Period Timings ===")
        total_time = 0.0
        for t in total_result.timings:
            print(f"  {t.pass_name:<40} {t.elapsed_seconds:>6.2f}s")
            total_time += t.elapsed_seconds
        print(f"  {'TOTAL':<40} {total_time:>6.2f}s")

    # Concatenate and save
    out = Path(args.data_dir)
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

    print("\nEngine run complete.")


def _save_output_tables(ctx: dict, data_dir: str) -> None:
    """Save enriched tables back to data directory."""
    import pandas as pd

    out = Path(data_dir)
    tables_to_save = {
        "fact_variance_material": ctx.get("material_variances"),  # Filtered variances with all bases/views
        "fact_decomposition": ctx.get("decomposition"),
        "fact_netting_flags": ctx.get("netting_flags"),
        "fact_trend_flags": ctx.get("trend_flags"),
        "fact_correlations": ctx.get("correlations"),
        "fact_review_status": ctx.get("review_status"),
    }

    for name, data in tables_to_save.items():
        if data is None:
            continue
        # Convert list of dicts to DataFrame if needed
        if isinstance(data, list) and len(data) > 0:
            data = pd.DataFrame(data)
        if isinstance(data, pd.DataFrame) and len(data) > 0:
            path = out / f"{name}.parquet"
            data.to_parquet(path, index=False)
            csv_path = out / f"{name}.csv"
            data.to_csv(csv_path, index=False)
            print(f"  Saved {name}: {len(data):,} rows")


if __name__ == "__main__":
    main()
