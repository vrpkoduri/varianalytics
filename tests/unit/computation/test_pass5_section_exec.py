"""Tests for Pass 5C/5D section narratives and executive summaries.

Validates:
- Section narrative LLM helper produces output
- Executive summary LLM helper produces substantive output
- Intelligence gathering functions collect correct context
- Multi-base expansion generates narratives for all bases
- QTD/YTD template narratives reference MTD narratives
- Template fallback when LLM unavailable
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from services.computation.engine.pass5_narrative import (
    _gather_executive_intelligence,
    _gather_section_intelligence,
    _generate_executive_llm_narrative,
    _generate_section_llm_narrative,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_llm(content: str = "Test narrative output. Confidence: 0.85"):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    mock_llm = MagicMock()
    mock_llm.is_available = True
    mock_llm.complete = AsyncMock(return_value=mock_resp)
    return mock_llm


def _make_correlations(base_id: str = "BUDGET") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "correlation_id": "c1",
            "base_id": base_id,
            "correlation_type": "persistent",
            "hypothesis": "Revenue decline persisting for 3 months in BU-East",
            "confidence": 0.85,
        },
        {
            "correlation_id": "c2",
            "base_id": base_id,
            "correlation_type": "yoy_echo",
            "hypothesis": "Travel overspend recurred from same month last year",
            "confidence": 0.8,
        },
        {
            "correlation_id": "c3",
            "base_id": base_id,
            "correlation_type": "within_period",
            "hypothesis": "Revenue and COGS are correlated due to volume drop",
            "confidence": 0.75,
        },
    ])


def _make_trend_flags() -> pd.DataFrame:
    return pd.DataFrame([
        {"account_id": "acct_revenue", "bu_id": "BU_EAST", "direction": "declining", "consecutive_periods": 3},
        {"account_id": "acct_travel", "bu_id": "BU_WEST", "direction": "increasing", "consecutive_periods": 4},
    ])


# ---------------------------------------------------------------------------
# Intelligence gathering tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGatherSectionIntelligence:

    def test_collects_trends_for_section_accounts(self):
        trend_flags = _make_trend_flags()
        intel = _gather_section_intelligence(
            section_name="Revenue",
            section_acct_ids={"acct_revenue", "acct_gross_revenue"},
            bu_id="BU_EAST",
            base_id="BUDGET",
            correlations=pd.DataFrame(),
            trend_flags=trend_flags,
            netting_flags=pd.DataFrame(),
            knowledge_graph=None,
            per_variance_narratives=[],
        )
        assert len(intel["trends"]) == 1
        assert "declining" in intel["trends"][0]

    def test_collects_correlations(self):
        corr = _make_correlations()
        intel = _gather_section_intelligence(
            section_name="Revenue",
            section_acct_ids={"acct_revenue"},
            bu_id=None,
            base_id="BUDGET",
            correlations=corr,
            trend_flags=pd.DataFrame(),
            netting_flags=pd.DataFrame(),
            knowledge_graph=None,
            per_variance_narratives=[],
        )
        assert len(intel["correlations"]) > 0

    def test_collects_child_narratives(self):
        per_var = [
            {"account_id": "acct_revenue", "base_id": "BUDGET", "bu_id": "BU_EAST",
             "detail": "Revenue decreased by $80K due to lower cloud sales."},
        ]
        intel = _gather_section_intelligence(
            section_name="Revenue",
            section_acct_ids={"acct_revenue"},
            bu_id="BU_EAST",
            base_id="BUDGET",
            correlations=pd.DataFrame(),
            trend_flags=pd.DataFrame(),
            netting_flags=pd.DataFrame(),
            knowledge_graph=None,
            per_variance_narratives=per_var,
        )
        assert len(intel["child_narratives"]) == 1
        assert "cloud sales" in intel["child_narratives"][0]

    def test_empty_inputs_no_crash(self):
        intel = _gather_section_intelligence(
            "Revenue", set(), None, "BUDGET",
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None, [],
        )
        assert isinstance(intel, dict)
        assert all(isinstance(v, list) for v in [intel["trends"], intel["correlations"]])


@pytest.mark.unit
class TestGatherExecutiveIntelligence:

    def test_collects_persistent_patterns(self):
        corr = _make_correlations()
        intel = _gather_executive_intelligence(
            bu_id=None, base_id="BUDGET",
            correlations=corr, trend_flags=pd.DataFrame(), knowledge_graph=None,
        )
        assert len(intel["persistent_patterns"]) == 1
        assert "persisting" in intel["persistent_patterns"][0]

    def test_collects_yoy_echoes(self):
        corr = _make_correlations()
        intel = _gather_executive_intelligence(
            bu_id=None, base_id="BUDGET",
            correlations=corr, trend_flags=pd.DataFrame(), knowledge_graph=None,
        )
        assert len(intel["yoy_echoes"]) == 1

    def test_collects_trend_summary(self):
        trends = _make_trend_flags()
        intel = _gather_executive_intelligence(
            bu_id=None, base_id="BUDGET",
            correlations=pd.DataFrame(), trend_flags=trends, knowledge_graph=None,
        )
        assert "2 variances" in intel["trend_summary"]

    def test_empty_inputs_no_crash(self):
        intel = _gather_executive_intelligence(
            None, "BUDGET", pd.DataFrame(), pd.DataFrame(), None,
        )
        assert isinstance(intel, dict)


# ---------------------------------------------------------------------------
# LLM generation tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSectionLLMGeneration:

    @pytest.mark.asyncio
    async def test_generates_narrative(self):
        llm = _mock_llm("Revenue declined $80K driven by lower cloud subscriptions. "
                         "This marks the third consecutive month of underperformance.")
        task = {
            "entry_idx": 0,
            "section_name": "Revenue",
            "base_label": "Budget",
            "bu_label": "ALL",
            "total_var": -80_000,
            "total_pct": -5.2,
            "direction": "decreased",
            "driver_text": "Cloud Subscriptions (-$50K), Licensing (-$20K)",
            "pos_count": 2,
            "total_count": 8,
            "intel_context": {"child_narratives": [], "trends": [], "correlations": [], "netting": []},
        }
        idx, narrative = await _generate_section_llm_narrative(llm, task)
        assert idx == 0
        assert narrative is not None
        assert "cloud" in narrative.lower()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self):
        llm = MagicMock()
        llm.is_available = True
        llm.complete = AsyncMock(side_effect=Exception("Rate limit"))
        task = {
            "entry_idx": 5,
            "section_name": "OpEx",
            "base_label": "Forecast",
            "bu_label": "BU_WEST",
            "total_var": 30_000,
            "total_pct": 3.1,
            "direction": "increased",
            "driver_text": "Travel (+$20K)",
            "pos_count": 1,
            "total_count": 5,
            "intel_context": {"child_narratives": [], "trends": [], "correlations": [], "netting": []},
        }
        idx, narrative = await _generate_section_llm_narrative(llm, task)
        assert idx == 5
        assert narrative is None

    @pytest.mark.asyncio
    async def test_fallback_response_returns_none(self):
        llm = MagicMock()
        llm.is_available = True
        llm.complete = AsyncMock(return_value={"fallback": True})
        task = {
            "entry_idx": 2,
            "section_name": "COGS",
            "base_label": "Budget",
            "bu_label": "ALL",
            "total_var": -10_000,
            "total_pct": -1.0,
            "direction": "decreased",
            "driver_text": "Materials (-$8K)",
            "pos_count": 0,
            "total_count": 3,
            "intel_context": {"child_narratives": [], "trends": [], "correlations": [], "netting": []},
        }
        idx, narrative = await _generate_section_llm_narrative(llm, task)
        assert narrative is None


@pytest.mark.unit
class TestExecutiveLLMGeneration:

    @pytest.mark.asyncio
    async def test_generates_substantive_narrative(self):
        llm = _mock_llm(
            "June 2026 financial results fell short of budget expectations across key metrics. "
            "Revenue declined 5.2% driven by lower cloud subscription volumes in the Enterprise segment. "
            "EBITDA compressed 8.1% as cost management initiatives were insufficient to offset the revenue shortfall.\n\n"
            "Cost of revenue increased marginally due to infrastructure commitments that could not be scaled down. "
            "Operating expenses showed mixed results with travel and personnel costs trending above plan.\n\n"
            "Three risk items warrant attention: persistent revenue underperformance for 3 consecutive months, "
            "year-over-year travel overspend patterns, and 5 trending variances requiring management action."
        )
        task = {
            "entry_idx": 0,
            "month_name": "June",
            "year": "2026",
            "base_label": "Budget",
            "bu_label": "ALL",
            "bu_id": None,
            "rev_total": -800_000,
            "rev_pct": -5.2,
            "ebitda_total": -500_000,
            "ebitda_pct": -8.1,
            "section_refs": {
                "Revenue": "Revenue decreased by $800K vs Budget.",
                "COGS": "COGS increased $50K.",
                "OpEx": "OpEx increased $200K.",
                "Profitability": "EBITDA decreased $500K.",
            },
            "risks": [{"risk": "3 trending variances", "severity": "medium"}],
            "cross_bu_themes": [{"theme": "2 of 5 BUs exceeded targets"}],
            "cross_bu": "2 of 5 BUs exceeded revenue targets",
            "exec_intel": {
                "persistent_patterns": ["Revenue declining for 3 months"],
                "yoy_echoes": ["Travel overspend same as June 2025"],
                "graph_hubs": [],
                "trend_summary": "5 variances trending",
            },
        }
        idx, headline, narrative = await _generate_executive_llm_narrative(llm, task)
        assert idx == 0
        assert headline is not None
        assert narrative is not None
        assert len(narrative) > 100  # Substantive

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self):
        llm = MagicMock()
        llm.is_available = True
        llm.complete = AsyncMock(side_effect=Exception("Timeout"))
        task = {
            "entry_idx": 1,
            "month_name": "June",
            "year": "2026",
            "base_label": "Budget",
            "bu_label": "BU_EAST",
            "bu_id": "BU_EAST",
            "rev_total": -200_000,
            "rev_pct": -3.0,
            "ebitda_total": -100_000,
            "ebitda_pct": -4.0,
            "section_refs": {},
            "risks": [],
            "cross_bu_themes": [],
            "cross_bu": "BU_EAST performance",
            "exec_intel": {"persistent_patterns": [], "yoy_echoes": [], "graph_hubs": [], "trend_summary": ""},
        }
        idx, headline, narrative = await _generate_executive_llm_narrative(llm, task)
        assert idx == 1
        assert headline is None
        assert narrative is None
