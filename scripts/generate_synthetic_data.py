#!/usr/bin/env python3
"""CLI entry point for synthetic data generation.

Usage:
    python scripts/generate_synthetic_data.py [--output-dir data/output] [--seed 42] [--format parquet csv]

Generates all 15 tables from the synthetic data spec and saves to disk.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.data.synthetic import SyntheticDataGenerator


def main() -> None:
    """Run the synthetic data generator."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic FP&A data for the Variance Analysis Agent"
    )
    parser.add_argument(
        "--spec",
        default="docs/synthetic-data-spec.json",
        help="Path to synthetic data spec (default: docs/synthetic-data-spec.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/output",
        help="Output directory (default: data/output)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--format",
        nargs="+",
        default=["parquet", "csv"],
        choices=["parquet", "csv"],
        help="Output formats (default: parquet csv)",
    )
    args = parser.parse_args()

    print(f"Synthetic Data Generator")
    print(f"  Spec:    {args.spec}")
    print(f"  Output:  {args.output_dir}")
    print(f"  Seed:    {args.seed}")
    print(f"  Formats: {', '.join(args.format)}")
    print()

    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    generator = SyntheticDataGenerator(args.spec, seed=args.seed)
    tables = generator.generate()

    # Show table summary
    print("\nGenerated Tables:")
    print(f"{'Table':<35} {'Rows':>8}")
    print("-" * 45)
    for name, df in sorted(tables.items()):
        print(f"  {name:<33} {len(df):>8,}")

    # Validate
    issues = generator.validate()
    if issues:
        print(f"\nValidation FAILED ({len(issues)} issues):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\nValidation PASSED")

    # Save
    generator.save(args.output_dir, formats=args.format)
    print(f"\nOutput saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
