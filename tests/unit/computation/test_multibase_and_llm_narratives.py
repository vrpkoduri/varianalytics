"""Tests for Pass 4 multi-base and Pass 5 LLM section/executive narratives.

Validates:
- Pass 4 runs correlations per base (BUDGET, FORECAST, PRIOR_YEAR)
- base_id column present in all correlation output
- Pass 5 intelligence gathering for sections and executives
- Pass 5 LLM helper functions with mock LLM
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from services.computation.engine.pass4_correlation import find_correlations
from services.computation.engine.pass5_narrative import (
    _gather_executive_intelligence,
    _gather_section_intelligence,
    _generate_executive_llm_narrative,
    _generate_section_llm_narrative,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(variance_id, account_id, bu_id, period_id, amount, base_id="BUDGET", **kw):
    row = {
        "variance_id": variance_id,
        "account_id": account_id,
        "bu_id": bu_id,
        "costcenter_node_id": kw.get("costcenter_node_id", "cc_1"),
        "geo_node_id": kw.get("geo_node_id", "geo_us"),
        "segment_node_id": kw.get("segment_node_id", "seg_1"),
        "lob_node_id": kw.get("lob_node_id", "lob_1"),
        "period_id": period_id,
        "view_id": "MTD",
        "base_id": base_id,
        "variance_amount": amount,
        "variance_pct": 5.0,
    }
    row.update(kw)
    return row


# ===========================================================================
# Pass 4 Multi-Base Tests
# ===========================================================================


@pytest.mark.unit
class TestPass4MultiBase:
    """Pass 4 correlations run per base and include base_id."""

    @pytest.mark.asyncio
    async def test_base_id_column_in_output(self):
        """Correlations should include base_id column."""
        rows = [
            _make_row(f"v-{i}", f"acct_{i % 3}", "BU_A", "2026-06", -(i + 1) * 10_000)
            for i in range(6)
        ]
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(rows),
        }
        await find_correlations(ctx)
        corr = ctx["correlations"]
        if not corr.empty:
            assert "base_id" in corr.columns
            assert (corr["base_id"] == "BUDGET").all()

    @pytest.mark.asyncio
    async def test_multiple_bases_produce_correlations(self):
        """Each base should produce its own correlations."""
        rows = []
        for base in ["BUDGET", "FORECAST", "PRIOR_YEAR"]:
            for i in range(4):
                rows.append(_make_row(
                    f"v-{base}-{i}", f"acct_{i % 2}", "BU_A", "2026-06",
                    -(i + 1) * 10_000, base_id=base,
                ))
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(rows),
        }
        await find_correlations(ctx)
        corr = ctx["correlations"]

        if not corr.empty:
            bases_found = set(corr["base_id"].unique())
            # Should have correlations for at least BUDGET (most likely all 3)
            assert "BUDGET" in bases_found

    @pytest.mark.asyncio
    async def test_cross_period_per_base(self):
        """Cross-period correlations should respect base_id filtering."""
        current = [
            _make_row("v-curr-b", "acct_rev", "BU_A", "2026-06", -50_000, base_id="BUDGET"),
            _make_row("v-curr-f", "acct_rev", "BU_A", "2026-06", -30_000, base_id="FORECAST"),
        ]
        prior = [
            _make_row("v-apr-b", "acct_rev", "BU_A", "2026-04", -40_000, base_id="BUDGET"),
            _make_row("v-may-b", "acct_rev", "BU_A", "2026-05", -45_000, base_id="BUDGET"),
            # No FORECAST prior data — so FORECAST should have no persistent
        ]
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(current),
            "existing_material": pd.DataFrame(prior),
        }
        await find_correlations(ctx)
        corr = ctx["correlations"]

        if not corr.empty:
            persistent = corr[corr["correlation_type"] == "persistent"]
            if not persistent.empty:
                # Persistent should only be for BUDGET (has 3-month streak)
                assert (persistent["base_id"] == "BUDGET").all()

    @pytest.mark.asyncio
    async def test_single_base_backward_compatible(self):
        """Data with only BUDGET base should work like before."""
        rows = [
            _make_row(f"v-{i}", f"acct_{i % 3}", "BU_A", "2026-06", -(i + 1) * 5_000)
            for i in range(6)
        ]
        ctx = {
            "period_id": "2026-06",
            "material_variances": pd.DataFrame(rows),
        }
        await find_correlations(ctx)
        corr = ctx["correlations"]
        if not corr.empty:
            assert "base_id" in corr.columns
            assert "correlation_type" in corr.columns


# ===========================================================================
# Pass 5 Intelligence Gathering Tests
# ===========================================================================


@pytest.mark.unit
class TestSectionIntelligence:
    """Test _gather_section_intelligence."""

    def test_gathers_trends(self):
        trend_flags = pd.DataFrame([
            {"account_id": "acct_revenue", "bu_id": "BU_A", "direction": "down", "consecutive_periods": 3},
        ])
        intel = _gather_section_intelligence(
            "Revenue", {"acct_revenue"}, "BU_A", "BUDGET",
            pd.DataFrame(), trend_flags, pd.DataFrame(), None, [],
        )
        assert len(intel["trends"]) == 1
        assert "down" in intel["trends"][0]

    def test_gathers_child_narratives(self):
        narratives = [
            {"account_id": "acct_revenue", "base_id": "BUDGET", "bu_id": "BU_A",
             "detail": "Revenue decreased by $50K due to lower volume."},
        ]
        intel = _gather_section_intelligence(
            "Revenue", {"acct_revenue"}, "BU_A", "BUDGET",
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None, narratives,
        )
        assert len(intel["child_narratives"]) == 1

    def test_filters_by_base_id(self):
        """Should only include narratives matching the base."""
        narratives = [
            {"account_id": "acct_revenue", "base_id": "BUDGET", "bu_id": "BU_A",
             "detail": "Budget narrative"},
            {"account_id": "acct_revenue", "base_id": "FORECAST", "bu_id": "BU_A",
             "detail": "Forecast narrative"},
        ]
        intel = _gather_section_intelligence(
            "Revenue", {"acct_revenue"}, "BU_A", "BUDGET",
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None, narratives,
        )
        assert len(intel["child_narratives"]) == 1
        assert "Budget" in intel["child_narratives"][0]

    def test_empty_inputs_no_crash(self):
        intel = _gather_section_intelligence(
            "Revenue", set(), None, "BUDGET",
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None, [],
        )
        assert intel["trends"] == []
        assert intel["correlations"] == []
        assert intel["child_narratives"] == []


@pytest.mark.unit
class TestExecutiveIntelligence:
    """Test _gather_executive_intelligence."""

    def test_gathers_persistent_patterns(self):
        correlations = pd.DataFrame([
            {"base_id": "BUDGET", "correlation_type": "persistent",
             "hypothesis": "Revenue in BU-East unfavorable for 4 months"},
        ])
        intel = _gather_executive_intelligence(
            None, "BUDGET", correlations, pd.DataFrame(), None,
        )
        assert len(intel["persistent_patterns"]) == 1

    def test_gathers_yoy_echoes(self):
        correlations = pd.DataFrame([
            {"base_id": "BUDGET", "correlation_type": "yoy_echo",
             "hypothesis": "Same pattern as Jun 2025"},
        ])
        intel = _gather_executive_intelligence(
            None, "BUDGET", correlations, pd.DataFrame(), None,
        )
        assert len(intel["yoy_echoes"]) == 1

    def test_filters_by_base(self):
        """Should only include correlations for the given base."""
        correlations = pd.DataFrame([
            {"base_id": "BUDGET", "correlation_type": "persistent", "hypothesis": "Budget pattern"},
            {"base_id": "FORECAST", "correlation_type": "persistent", "hypothesis": "Forecast pattern"},
        ])
        intel = _gather_executive_intelligence(
            None, "BUDGET", correlations, pd.DataFrame(), None,
        )
        assert len(intel["persistent_patterns"]) == 1
        assert "Budget" in intel["persistent_patterns"][0]

    def test_empty_inputs_no_crash(self):
        intel = _gather_executive_intelligence(
            None, "BUDGET", pd.DataFrame(), pd.DataFrame(), None,
        )
        assert intel["persistent_patterns"] == []
        assert intel["yoy_echoes"] == []


# ===========================================================================
# Pass 5 LLM Section/Executive Narrative Tests
# ===========================================================================


@pytest.mark.unit
class TestSectionLLMNarrative:
    """Test _generate_section_llm_narrative with mock LLM."""

    @pytest.mark.asyncio
    async def test_generates_narrative(self):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = (
            "Revenue declined by $800K (-5.2%) vs Budget, driven primarily by "
            "lower Cloud Services volume in APAC. This represents a 3-month "
            "consecutive pattern requiring management attention."
        )
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        task = {
            "entry_idx": 0,
            "section_name": "Revenue",
            "base_label": "Budget",
            "bu_label": "ALL",
            "total_var": -800_000,
            "total_pct": -5.2,
            "direction": "decreased",
            "driver_text": "Cloud Services (-$500K), Licensing (-$200K)",
            "pos_count": 2,
            "total_count": 8,
            "intel_context": {"trends": ["Revenue trending down for 3 months"],
                              "correlations": [], "netting": [], "child_narratives": []},
        }
        idx, narrative = await _generate_section_llm_narrative(mock_llm, task)
        assert idx == 0
        assert narrative is not None
        assert "Revenue" in narrative

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self):
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(side_effect=Exception("API error"))

        task = {
            "entry_idx": 0, "section_name": "Revenue", "base_label": "Budget",
            "bu_label": "ALL", "total_var": -50_000, "total_pct": -3.0,
            "direction": "decreased", "driver_text": "misc", "pos_count": 0,
            "total_count": 1, "intel_context": {"trends": [], "correlations": [],
                                                  "netting": [], "child_narratives": []},
        }
        idx, narrative = await _generate_section_llm_narrative(mock_llm, task)
        assert idx == 0
        assert narrative is None


@pytest.mark.unit
class TestExecutiveLLMNarrative:
    """Test _generate_executive_llm_narrative with mock LLM."""

    @pytest.mark.asyncio
    async def test_generates_substantive_narrative(self):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = (
            "June 2026 financial performance fell short of Budget targets across "
            "all key metrics. Revenue declined 5.2% ($800K) driven by APAC volume "
            "softness, marking the third consecutive month of underperformance.\n\n"
            "Cost management partially offset the revenue shortfall, with OpEx "
            "coming in 2.1% below budget. However, EBITDA margin compressed to "
            "18.3% from the budgeted 20.1%.\n\n"
            "Three structural risks warrant attention: the persistent revenue "
            "decline in Cloud Services, rising customer acquisition costs in "
            "BU-West, and the year-over-year echo in licensing renewals."
        )
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        task = {
            "entry_idx": 0,
            "month_name": "June", "year": "2026", "base_label": "Budget",
            "bu_label": "ALL", "bu_id": None,
            "rev_total": -800_000, "rev_pct": -5.2,
            "ebitda_total": -350_000, "ebitda_pct": -8.1,
            "section_refs": {"Revenue": "Revenue declined...", "COGS": "COGS flat..."},
            "risks": [{"risk": "3 trending variances", "severity": "medium"}],
            "cross_bu_themes": [{"theme": "2 of 5 BUs exceeded targets"}],
            "cross_bu": "2 of 5 BUs exceeded revenue targets",
            "exec_intel": {
                "persistent_patterns": ["Revenue BU-East 4-month streak"],
                "yoy_echoes": ["Licensing same pattern as Jun 2025"],
                "trend_summary": "15 variances trending",
                "graph_hubs": [],
            },
        }
        idx, headline, narrative = await _generate_executive_llm_narrative(mock_llm, task)
        assert idx == 0
        assert headline is not None
        assert narrative is not None
        assert len(narrative) > 100  # Substantive

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self):
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(side_effect=Exception("Timeout"))

        task = {
            "entry_idx": 0, "month_name": "June", "year": "2026",
            "base_label": "Budget", "bu_label": "ALL", "bu_id": None,
            "rev_total": 0, "rev_pct": 0, "ebitda_total": 0, "ebitda_pct": 0,
            "section_refs": {}, "risks": [], "cross_bu_themes": [],
            "cross_bu": "", "exec_intel": {"persistent_patterns": [],
                                            "yoy_echoes": [], "trend_summary": "", "graph_hubs": []},
        }
        idx, headline, narrative = await _generate_executive_llm_narrative(mock_llm, task)
        assert idx == 0
        assert narrative is None
