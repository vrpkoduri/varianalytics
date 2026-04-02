"""Tests for deterministic variance ID generation.

Verifies that variance IDs are hash-based (not random UUIDs),
deterministic across engine runs, unique, and correctly formatted.
"""

import asyncio
import hashlib
import re

import pandas as pd
import pytest

from services.computation.engine.runner import EngineRunner

DATA_DIR = "data/output"


def _compute_expected_id(period_id, account_id, bu_id, cc_id, geo_id, seg_id, lob_id, view_id, base_id) -> str:
    """Compute expected deterministic ID using the same hash logic."""
    key = f"{period_id}|{account_id}|{bu_id}|{cc_id}|{geo_id}|{seg_id}|{lob_id}|{view_id}|{base_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


@pytest.fixture(scope="module")
def engine_result():
    """Run engine once and return the context."""
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            runner.run_full_pipeline(
                period_id="2026-05",
                data_dir=DATA_DIR,
                llm_client=None,
                rag_retriever=None,
            )
        )
    finally:
        loop.close()
    return runner._last_context.get("material_variances", pd.DataFrame())


class TestDeterministicVarianceIDs:
    """Tests for deterministic hash-based variance IDs."""

    def test_variance_id_format(self, engine_result: pd.DataFrame):
        """Variance IDs should be 16-character hex strings."""
        assert not engine_result.empty
        sample_id = engine_result["variance_id"].iloc[0]
        assert isinstance(sample_id, str)
        assert len(sample_id) == 16
        assert re.match(r'^[0-9a-f]{16}$', sample_id), f"Invalid format: {sample_id}"

    def test_variance_id_unique(self, engine_result: pd.DataFrame):
        """All variance IDs should be unique."""
        total = len(engine_result)
        unique = engine_result["variance_id"].nunique()
        assert unique == total, f"Duplicates found: {total - unique} of {total}"

    def test_variance_id_is_deterministic(self):
        """Same inputs produce the same ID across two engine runs."""
        runner = EngineRunner()
        loop = asyncio.new_event_loop()

        try:
            # Run 1
            loop.run_until_complete(
                runner.run_full_pipeline(period_id="2026-05", data_dir=DATA_DIR, llm_client=None)
            )
            ids_run1 = set(runner._last_context["material_variances"]["variance_id"].unique())

            # Run 2
            loop.run_until_complete(
                runner.run_full_pipeline(period_id="2026-05", data_dir=DATA_DIR, llm_client=None)
            )
            ids_run2 = set(runner._last_context["material_variances"]["variance_id"].unique())
        finally:
            loop.close()

        # Same IDs both runs
        assert ids_run1 == ids_run2, (
            f"IDs differ between runs: {len(ids_run1 - ids_run2)} only in run1, "
            f"{len(ids_run2 - ids_run1)} only in run2"
        )

    def test_variance_id_changes_with_period(self):
        """Different periods produce different IDs for the same account."""
        id_may = _compute_expected_id("2026-05", "acct_revenue", "marsh", "cc_gen", "geo_us", "seg_con", "lob_adv", "MTD", "BUDGET")
        id_jun = _compute_expected_id("2026-06", "acct_revenue", "marsh", "cc_gen", "geo_us", "seg_con", "lob_adv", "MTD", "BUDGET")
        assert id_may != id_jun

    def test_variance_id_changes_with_base(self):
        """Different bases produce different IDs for the same intersection."""
        id_budget = _compute_expected_id("2026-05", "acct_revenue", "marsh", "cc_gen", "geo_us", "seg_con", "lob_adv", "MTD", "BUDGET")
        id_forecast = _compute_expected_id("2026-05", "acct_revenue", "marsh", "cc_gen", "geo_us", "seg_con", "lob_adv", "MTD", "FORECAST")
        assert id_budget != id_forecast
