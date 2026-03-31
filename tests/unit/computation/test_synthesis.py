"""Tests for narrative synthesis."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.computation.synthesis.narrative_synthesis import (
    SynthesisResult,
    _simple_synthesis,
    synthesize_narratives,
)


class TestSynthesizeNarratives:
    @pytest.mark.asyncio
    async def test_returns_blocked_with_no_children(self):
        result = await synthesize_narratives("var_parent", [])
        assert result.status == "blocked"
        assert "No child" in result.error

    @pytest.mark.asyncio
    async def test_returns_blocked_with_empty_narratives(self):
        result = await synthesize_narratives("var_parent", [{"account_id": "x"}])
        assert result.status == "blocked"

    @pytest.mark.asyncio
    async def test_simple_synthesis_without_llm(self):
        children = [
            {
                "account_id": "acct_advisory",
                "narrative_detail": "Advisory grew by 15% in APAC",
            },
            {
                "account_id": "acct_consulting",
                "narrative_detail": "Consulting declined 7% in EMEA",
            },
        ]
        result = await synthesize_narratives("var_parent", children)
        assert result.status == "completed"
        assert "midlevel" in result.narratives_synthesized
        assert "summary" in result.narratives_synthesized

    @pytest.mark.asyncio
    async def test_llm_synthesis_with_mock(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"midlevel": "Revenue mix shifted toward advisory.",'
            ' "summary": "Net favorable driven by APAC."}'
        )

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_response)

        children = [
            {"account_id": "acct_advisory", "narrative_detail": "Advisory grew 15%"},
            {
                "account_id": "acct_consulting",
                "narrative_detail": "Consulting declined 7%",
            },
        ]
        result = await synthesize_narratives(
            "var_parent", children, llm_client=mock_llm
        )
        assert result.status == "completed"
        assert mock_llm.complete.called

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_simple(self):
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(side_effect=Exception("API error"))

        children = [
            {"account_id": "acct_advisory", "narrative_detail": "Advisory grew"},
        ]
        result = await synthesize_narratives(
            "var_parent", children, llm_client=mock_llm
        )
        assert result.status == "completed"  # Falls back to simple synthesis

    @pytest.mark.asyncio
    async def test_child_count_populated(self):
        children = [
            {"account_id": "acct_a", "narrative_detail": "A grew"},
            {"account_id": "acct_b", "narrative_detail": "B declined"},
            {"account_id": "acct_c", "narrative_detail": "C flat"},
        ]
        result = await synthesize_narratives("var_parent", children)
        assert result.child_count == 3

    @pytest.mark.asyncio
    async def test_parent_variance_id_set(self):
        result = await synthesize_narratives("var_parent_123", [])
        assert result.parent_variance_id == "var_parent_123"


class TestSimpleSynthesis:
    def test_aggregates_children(self):
        children = [
            {"account_id": "acct_revenue", "narrative_detail": "Revenue grew"},
            {"account_id": "acct_costs", "narrative_detail": "Costs increased"},
        ]
        result = _simple_synthesis(children)
        assert "midlevel" in result
        assert "summary" in result
        assert len(result["midlevel"]) > 10

    def test_empty_children(self):
        result = _simple_synthesis([])
        assert result["midlevel"] == "Multiple variances aggregated."

    def test_limits_to_five_children(self):
        children = [
            {"account_id": f"acct_{i}", "narrative_detail": f"Narrative {i}"}
            for i in range(10)
        ]
        result = _simple_synthesis(children)
        # midlevel only uses first 3 of the 5 processed
        assert result["midlevel"].count(":") <= 3

    def test_strips_acct_prefix(self):
        children = [
            {"account_id": "acct_advisory_fees", "narrative_detail": "Grew 10%"},
        ]
        result = _simple_synthesis(children)
        assert "acct_" not in result["midlevel"]
