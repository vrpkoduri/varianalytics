"""Unit tests for LLM intent classifier."""

import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from services.gateway.agents.intent import (
    ExtractedEntities,
    Intent,
    KeywordIntentClassifier,
    LLMIntentClassifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_client(available: bool = True) -> MagicMock:
    client = MagicMock()
    type(client).is_available = PropertyMock(return_value=available)
    return client


def _make_tool_call_response(args: dict) -> MagicMock:
    """Build a mock LiteLLM response with a function-call result."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [MagicMock()]
    mock_response.choices[0].message.tool_calls[0].function.arguments = json.dumps(args)
    return mock_response


# ---------------------------------------------------------------------------
# Classification via LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLLMClassify:

    @pytest.mark.asyncio
    async def test_llm_classify_revenue_question(self):
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({"intent": "revenue_overview"})
        )

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("How did revenue perform?")

        assert intent == Intent.REVENUE_OVERVIEW
        client.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_classify_with_entities(self):
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({
                "intent": "trend",
                "bu_id": "marsh",
                "period_id": "2026-06",
            })
        )

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("Show Marsh trend for June 2026")

        assert intent == Intent.TREND
        assert entities.bu_id == "marsh"
        assert entities.period_id == "2026-06"

    @pytest.mark.asyncio
    async def test_llm_classify_pl_summary(self):
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({"intent": "pl_summary"})
        )

        classifier = LLMIntentClassifier(client)
        intent, _ = await classifier.classify("Show me the P&L")

        assert intent == Intent.PL_SUMMARY

    @pytest.mark.asyncio
    async def test_llm_classify_with_account_and_dimension(self):
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({
                "intent": "drill_down",
                "account_id": "acct_revenue",
                "dimension": "geography",
            })
        )

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("Drill into revenue by geography")

        assert intent == Intent.DRILL_DOWN
        assert entities.account_id == "acct_revenue"
        assert entities.dimension == "geography"


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLLMFallback:

    @pytest.mark.asyncio
    async def test_llm_classify_fallback_on_error(self):
        client = _make_llm_client()
        client.complete = AsyncMock(side_effect=Exception("API timeout"))

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("How did revenue perform this month?")

        # Keyword classifier should catch "revenue"
        assert intent == Intent.REVENUE_OVERVIEW

    @pytest.mark.asyncio
    async def test_llm_classify_fallback_when_unavailable(self):
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value={"fallback": True, "content": "LLM not configured"}
        )

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("Show the P&L")

        # Keyword classifier should catch "P&L"
        assert intent == Intent.PL_SUMMARY


# ---------------------------------------------------------------------------
# Tool definition integrity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestToolDefinition:

    def test_function_definition_has_all_intents(self):
        """The classify_intent tool enum must list every Intent value."""
        tool_enum = (
            LLMIntentClassifier._CLASSIFY_TOOL["function"]["parameters"]["properties"]["intent"]["enum"]
        )
        intent_values = [i.value for i in Intent]
        assert sorted(tool_enum) == sorted(intent_values)


# ---------------------------------------------------------------------------
# UI context merging
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUIContextMerging:

    @pytest.mark.asyncio
    async def test_ui_context_merged_with_llm_entities(self):
        """When LLM returns no period, UI context fills it in."""
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({
                "intent": "revenue_overview",
                # No period_id returned by LLM
            })
        )

        classifier = LLMIntentClassifier(client)
        ui_ctx = {"period_id": "2026-03", "bu_id": "mercer"}
        intent, entities = await classifier.classify("How did revenue do?", ui_context=ui_ctx)

        assert intent == Intent.REVENUE_OVERVIEW
        assert entities.period_id == "2026-03"
        assert entities.bu_id == "mercer"

    @pytest.mark.asyncio
    async def test_llm_entities_override_ui_context(self):
        """LLM-extracted entities take precedence over UI context."""
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({
                "intent": "trend",
                "bu_id": "marsh",
                "period_id": "2026-06",
            })
        )

        classifier = LLMIntentClassifier(client)
        ui_ctx = {"period_id": "2026-03", "bu_id": "mercer"}
        intent, entities = await classifier.classify(
            "Show Marsh trend for June 2026",
            ui_context=ui_ctx,
        )

        assert entities.bu_id == "marsh"
        assert entities.period_id == "2026-06"


# ---------------------------------------------------------------------------
# Defensive guards — tool_calls parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLLMIntentGuards:

    @pytest.mark.asyncio
    async def test_llm_returns_no_tool_calls_fallback(self):
        """If LLM response has no tool_calls, fall back to keyword."""
        client = _make_llm_client()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None  # No tool calls
        client.complete = AsyncMock(return_value=mock_response)

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("How did revenue do?")

        # Keyword classifier should catch "revenue"
        assert intent == Intent.REVENUE_OVERVIEW

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_intent_value_fallback(self):
        """If LLM returns intent not in enum, use GENERAL."""
        client = _make_llm_client()
        client.complete = AsyncMock(
            return_value=_make_tool_call_response({"intent": "unknown_xyz"})
        )

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("Something unusual")

        assert intent == Intent.GENERAL

    @pytest.mark.asyncio
    async def test_llm_returns_malformed_arguments_fallback(self):
        """If LLM returns non-JSON arguments, fall back to keyword."""
        client = _make_llm_client()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]
        mock_response.choices[0].message.tool_calls[0].function.arguments = "not valid json"
        client.complete = AsyncMock(return_value=mock_response)

        classifier = LLMIntentClassifier(client)
        intent, entities = await classifier.classify("Show the P&L statement")

        # Keyword classifier should catch "P&L"
        assert intent == Intent.PL_SUMMARY
