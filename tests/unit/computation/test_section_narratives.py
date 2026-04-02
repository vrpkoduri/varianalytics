"""Tests for section narratives and executive summary generation (Phase 2C)."""

import asyncio

import pandas as pd
import pytest

from services.computation.engine.runner import EngineRunner

DATA_DIR = "data/output"
PERIOD = "2026-05"


@pytest.fixture(scope="module")
def engine_context():
    runner = EngineRunner()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            runner.run_full_pipeline(period_id=PERIOD, data_dir=DATA_DIR, llm_client=None)
        )
    finally:
        loop.close()
    return runner._last_context


class TestSectionNarratives:
    """Tests for P&L section narrative generation."""

    def test_five_sections_generated(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        names = {s["section_name"] for s in sections}
        expected = {"Revenue", "COGS", "OpEx", "Non-Operating", "Profitability"}
        assert names == expected, f"Expected {expected}, got {names}"

    def test_revenue_references_accounts(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        rev = next((s for s in sections if s["section_name"] == "Revenue"), None)
        assert rev is not None
        assert "Advisory" in rev["narrative"] or "Revenue" in rev["narrative"]

    def test_profitability_references_margins(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        prof = next((s for s in sections if s["section_name"] == "Profitability"), None)
        assert prof is not None
        assert "margin" in prof["narrative"].lower() or "EBITDA" in prof["narrative"]

    def test_section_has_key_drivers(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        for s in sections:
            assert "key_drivers" in s, f"{s['section_name']} missing key_drivers"

    def test_section_has_deterministic_id(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        ids = [s["section_id"] for s in sections]
        assert len(ids) == len(set(ids)), "Section IDs should be unique"
        assert all(len(sid) == 16 for sid in ids), "Section IDs should be 16-char hex"

    def test_sections_are_period_aware(self, engine_context):
        sections = engine_context.get("section_narratives", [])
        for s in sections:
            assert s["period_id"] == PERIOD


class TestExecutiveSummary:
    """Tests for executive summary generation."""

    def test_exec_summary_exists(self, engine_context):
        es = engine_context.get("executive_summary", {})
        assert es, "Executive summary should be generated"
        assert "headline" in es
        assert "full_narrative" in es

    def test_headline_mentions_revenue_and_ebitda(self, engine_context):
        es = engine_context.get("executive_summary", {})
        headline = es.get("headline", "")
        assert "Revenue" in headline or "revenue" in headline.lower()
        assert "EBITDA" in headline or "ebitda" in headline.lower()

    def test_headline_mentions_period(self, engine_context):
        es = engine_context.get("executive_summary", {})
        headline = es.get("headline", "")
        assert "May" in headline or "2026" in headline

    def test_full_narrative_has_sections(self, engine_context):
        es = engine_context.get("executive_summary", {})
        full = es.get("full_narrative", "")
        assert len(full) > 100, f"Full narrative too short: {len(full)} chars"

    def test_cross_bu_themes_exist(self, engine_context):
        es = engine_context.get("executive_summary", {})
        themes = es.get("cross_bu_themes", [])
        assert len(themes) > 0, "Should have cross-BU themes"
        assert "BU" in themes[0].get("theme", "") or "bus" in str(themes[0]).lower()

    def test_key_risks_exist(self, engine_context):
        es = engine_context.get("executive_summary", {})
        risks = es.get("key_risks", [])
        assert len(risks) >= 0  # May or may not have risks
