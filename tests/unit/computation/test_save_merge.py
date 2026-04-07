"""Tests for single-period save/merge accumulation logic.

Validates that running single periods accumulates data properly:
- First period creates new files
- Second period merges with existing, keeping prior period data
- Re-running same period replaces (not duplicates) its rows
- Different tables all merge correctly

Tests the merge logic directly without importing run_engine.py
(which has heavy dependencies).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


def _save_with_merge(
    out: Path,
    name: str,
    new_data: pd.DataFrame,
    periods_processed: list[str],
) -> None:
    """Replicate the merge logic from _save_all_outputs."""
    existing_path = out / f"{name}.parquet"
    if periods_processed and existing_path.exists():
        try:
            existing = pd.read_parquet(existing_path)
            if "period_id" in existing.columns:
                keep = existing[~existing["period_id"].isin(periods_processed)]
                combined = pd.concat([keep, new_data], ignore_index=True)
                combined = combined.sort_values("period_id").reset_index(drop=True)
            else:
                combined = new_data
        except Exception:
            combined = new_data
    else:
        combined = new_data

    combined.to_parquet(out / f"{name}.parquet", index=False)
    combined.to_csv(out / f"{name}.csv", index=False)


def _make_df(period_id: str, n_rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "variance_id": f"v-{period_id}-{i}",
            "period_id": period_id,
            "account_id": f"acct_{i}",
            "variance_amount": -(i + 1) * 10_000,
        }
        for i in range(n_rows)
    ])


@pytest.mark.unit
class TestSaveMerge:
    """Test merge logic for single-period accumulation."""

    def test_first_period_creates_new_file(self, tmp_path):
        jul = _make_df("2025-07")
        _save_with_merge(tmp_path, "fact_variance_material", jul, ["2025-07"])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 3
        assert set(result["period_id"]) == {"2025-07"}

    def test_second_period_merges_with_first(self, tmp_path):
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-07"), ["2025-07"])
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-08", 4), ["2025-08"])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 7  # 3 + 4
        assert set(result["period_id"]) == {"2025-07", "2025-08"}

    def test_rerun_same_period_replaces_not_duplicates(self, tmp_path):
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-07", 3), ["2025-07"])
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-07", 5), ["2025-07"])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 5  # Replaced, not 3+5

    def test_three_periods_accumulate(self, tmp_path):
        for period in ["2025-07", "2025-08", "2025-09"]:
            _save_with_merge(tmp_path, "fact_variance_material", _make_df(period, 2), [period])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 6  # 2+2+2
        assert set(result["period_id"]) == {"2025-07", "2025-08", "2025-09"}
        # Should be sorted by period
        periods = result["period_id"].tolist()
        assert periods == sorted(periods)

    def test_twelve_periods_full_accumulation(self, tmp_path):
        """Simulate full 12-month period-by-period run."""
        all_periods = [f"2025-{m:02d}" for m in range(7, 13)] + [f"2026-{m:02d}" for m in range(1, 7)]

        for period in all_periods:
            _save_with_merge(tmp_path, "fact_variance_material", _make_df(period, 3), [period])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 36  # 12 periods × 3 rows
        assert len(result["period_id"].unique()) == 12
        # Verify sorted
        periods = result["period_id"].tolist()
        assert periods == sorted(periods)

    def test_rerun_middle_period_preserves_others(self, tmp_path):
        """Re-running Aug should keep Jul and Sep intact."""
        for period in ["2025-07", "2025-08", "2025-09"]:
            _save_with_merge(tmp_path, "fact_variance_material", _make_df(period, 2), [period])

        # Re-run Aug with different row count
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-08", 5), ["2025-08"])

        result = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        assert len(result) == 9  # Jul(2) + Aug(5) + Sep(2)
        jul = result[result["period_id"] == "2025-07"]
        aug = result[result["period_id"] == "2025-08"]
        sep = result[result["period_id"] == "2025-09"]
        assert len(jul) == 2
        assert len(aug) == 5
        assert len(sep) == 2

    def test_multiple_tables_independent(self, tmp_path):
        """Different tables merge independently."""
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-07", 3), ["2025-07"])
        _save_with_merge(tmp_path, "fact_correlations", pd.DataFrame([
            {"correlation_id": "c1", "period_id": "2025-07", "score": 0.8},
        ]), ["2025-07"])

        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-08", 4), ["2025-08"])
        _save_with_merge(tmp_path, "fact_correlations", pd.DataFrame([
            {"correlation_id": "c2", "period_id": "2025-08", "score": 0.9},
        ]), ["2025-08"])

        material = pd.read_parquet(tmp_path / "fact_variance_material.parquet")
        corr = pd.read_parquet(tmp_path / "fact_correlations.parquet")
        assert len(material) == 7
        assert len(corr) == 2

    def test_csv_also_saved(self, tmp_path):
        """Both parquet and CSV should be created."""
        _save_with_merge(tmp_path, "fact_variance_material", _make_df("2025-07"), ["2025-07"])

        assert (tmp_path / "fact_variance_material.parquet").exists()
        assert (tmp_path / "fact_variance_material.csv").exists()

        csv_df = pd.read_csv(tmp_path / "fact_variance_material.csv")
        assert len(csv_df) == 3
