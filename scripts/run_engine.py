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
        help="Analysis period (default: 2026-06)",
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

    print("5.5-Pass Computation Engine")
    print(f"  Period:   {args.period}")
    print(f"  Data:     {args.data_dir}")
    print()

    runner = EngineRunner()
    result = asyncio.run(runner.run_full_pipeline(
        period_id=args.period,
        data_dir=args.data_dir,
    ))

    # Print results
    print("\n=== Pipeline Results ===")
    print(f"  Total variances computed: {result.total_variances_computed:,}")
    print(f"  Material variances:       {result.material_variances:,}")
    print(f"  Netting flags:            {result.netted_nodes:,}")
    print(f"  Trend flags:              {result.trending_variances:,}")
    print(f"  Narratives generated:     {result.narratives_generated:,}")

    print("\n=== Pass Timings ===")
    total_time = 0.0
    for t in result.timings:
        print(f"  {t.pass_name:<40} {t.elapsed_seconds:>6.2f}s")
        total_time += t.elapsed_seconds
    print(f"  {'TOTAL':<40} {total_time:>6.2f}s")

    if result.errors:
        print(f"\n=== Errors ({len(result.errors)}) ===")
        for e in result.errors:
            print(f"  - {e}")
        sys.exit(1)

    # Save output tables from context
    ctx = runner._last_context
    if ctx:
        _save_output_tables(ctx, args.data_dir)

    print("\nEngine run complete.")


def _save_output_tables(ctx: dict, data_dir: str) -> None:
    """Save enriched tables back to data directory."""
    import pandas as pd

    out = Path(data_dir)
    tables_to_save = {
        "fact_variance_material": ctx.get("narratives"),  # Has narrative columns
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
