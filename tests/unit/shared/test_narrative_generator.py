"""Unit tests for LLM narrative generator."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from services.gateway.agents.intent import Intent
from shared.llm.narrative import NarrativeGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_client(available: bool = True) -> MagicMock:
    """Create a mock LLMClient."""
    client = MagicMock()
    type(client).is_available = PropertyMock(return_value=available)
    return client


def _sample_revenue_data() -> dict:
    return {
        "actual": 5_000_000,
        "comparator": 4_800_000,
        "variance": 200_000,
        "pct": "+4.2%",
        "period": "2026-03",
        "base": "Budget",
        "direction": "above",
        "table": "...",
        "top_driver": "Marsh drove $150K favorable",
        "top_variances": [
            {"name": "Marsh", "variance": 150_000, "pct": "+6.0%"},
            {"name": "Mercer", "variance": 50_000, "pct": "+2.0%"},
        ],
    }


def _sample_pl_data() -> dict:
    return {
        "period": "2026-03",
        "summary_table": "...",
        "highlights": "Revenue up, EBITDA down",
        "cards": [
            {"label": "Revenue", "actual": 5_000_000, "variance": 200_000, "pct": "+4.2%"},
            {"label": "EBITDA", "actual": 1_200_000, "variance": -50_000, "pct": "-4.0%"},
        ],
    }


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateStreaming:

    @pytest.mark.asyncio
    async def test_generate_streaming_emits_tokens(self):
        client = _make_llm_client(available=True)

        async def fake_stream(task, messages):
            for token in ["Revenue ", "was ", "strong."]:
                yield token

        client.stream = fake_stream

        gen = NarrativeGenerator(client)
        ctx = AsyncMock()

        await gen.generate_streaming(
            "revenue_agent",
            Intent.REVENUE_OVERVIEW,
            _sample_revenue_data(),
            ctx,
        )

        assert ctx.emit_token.await_count == 3
        calls = [c.args[0] for c in ctx.emit_token.await_args_list]
        assert calls == ["Revenue ", "was ", "strong."]

    @pytest.mark.asyncio
    async def test_fallback_to_templates_when_unavailable(self):
        client = _make_llm_client(available=False)
        gen = NarrativeGenerator(client)
        ctx = AsyncMock()

        await gen.generate_streaming(
            "revenue_agent",
            Intent.REVENUE_OVERVIEW,
            _sample_revenue_data(),
            ctx,
        )

        ctx.emit_token.assert_awaited_once()
        text = ctx.emit_token.await_args.args[0]
        # Template should contain some revenue-related text
        assert "Revenue" in text or "revenue" in text


# ---------------------------------------------------------------------------
# Complete (non-streaming)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateComplete:

    @pytest.mark.asyncio
    async def test_generate_complete_returns_text(self):
        client = _make_llm_client(available=True)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Revenue grew 4.2% vs budget."
        client.complete = AsyncMock(return_value=mock_response)

        gen = NarrativeGenerator(client)
        result = await gen.generate_complete(
            "revenue_agent",
            Intent.REVENUE_OVERVIEW,
            _sample_revenue_data(),
        )

        assert result == "Revenue grew 4.2% vs budget."
        client.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_complete_fallback_when_unavailable(self):
        client = _make_llm_client(available=False)
        gen = NarrativeGenerator(client)

        result = await gen.generate_complete(
            "revenue_agent",
            Intent.REVENUE_OVERVIEW,
            _sample_revenue_data(),
        )

        # Should use template fallback
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Data formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatDataContext:

    def test_build_data_prompt_revenue(self):
        gen = NarrativeGenerator(_make_llm_client(available=False))
        text = gen._format_data_context(Intent.REVENUE_OVERVIEW, _sample_revenue_data())
        assert "Revenue Performance Data" in text
        assert "5,000,000" in text
        assert "Marsh" in text

    def test_build_data_prompt_pl(self):
        gen = NarrativeGenerator(_make_llm_client(available=False))
        text = gen._format_data_context(Intent.PL_SUMMARY, _sample_pl_data())
        assert "P&L Summary Data" in text
        assert "Revenue" in text
        assert "EBITDA" in text

    def test_build_data_prompt_default_json(self):
        gen = NarrativeGenerator(_make_llm_client(available=False))
        data = {"foo": "bar", "count": 42}
        text = gen._format_data_context(Intent.GENERAL, data)
        assert "foo" in text
        assert "42" in text


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSystemPromptLoaded:

    def test_system_prompt_loaded(self):
        gen = NarrativeGenerator(_make_llm_client(available=False))
        # Should have loaded prompts from YAML (or fallen back to defaults)
        assert gen._prompts is not None
        # If YAML was found, check that at least one agent type exists
        if gen._prompts:
            assert "pl_agent" in gen._prompts or "revenue_agent" in gen._prompts
