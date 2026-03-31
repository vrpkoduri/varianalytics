"""Tests for Pass 5 LLM narrative generation.

Validates the LLM-first + template-fallback path in Pass 5, ensuring:
- Template-only mode works when no LLM is in context.
- LLM failures gracefully fall back to templates.
- Successful LLM responses produce narratives with source='llm'.
- Audit entry tracks LLM vs template counts.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from services.computation.engine.pass5_narrative import (
    _generate_llm_narrative,
    generate_narratives,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_minimal_context(n_rows: int = 3, llm_client=None, rag_retriever=None):
    """Build a minimal Pass 5 context with synthetic material variances."""
    rows = []
    for i in range(n_rows):
        rows.append(
            {
                "variance_id": f"var-{i:03d}",
                "account_id": f"acct_{i}",
                "bu_id": "BU_NORTH",
                "period_id": "2026-03",
                "view_id": "MTD",
                "base_id": "BUDGET",
                "variance_amount": (i + 1) * 10_000.0,
                "variance_pct": (i + 1) * 2.5,
                "actual_amount": 100_000 + (i + 1) * 10_000,
                "budget_amount": 100_000.0,
            }
        )
    material = pd.DataFrame(rows)
    ctx: dict = {
        "period_id": "2026-03",
        "material_variances": material,
        "acct_meta": {
            f"acct_{i}": {"account_name": f"Account {i}", "variance_sign": "natural"}
            for i in range(n_rows)
        },
    }
    if llm_client is not None:
        ctx["llm_client"] = llm_client
    if rag_retriever is not None:
        ctx["rag_retriever"] = rag_retriever
    return ctx


def _mock_llm_response(detail: str, midlevel: str, summary: str, oneliner: str):
    """Create a mock LLM response with valid JSON narratives."""
    payload = json.dumps(
        {"detail": detail, "midlevel": midlevel, "summary": summary, "oneliner": oneliner}
    )
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = payload
    return mock_resp


# ---------------------------------------------------------------------------
# Tests — template-only mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass5TemplateOnly:
    """Pass 5 works with templates when no LLM in context."""

    @pytest.mark.asyncio
    async def test_generates_without_llm(self):
        """Template narratives are produced when no llm_client."""
        ctx = _build_minimal_context(n_rows=3)
        await generate_narratives(ctx)

        assert "narratives" in ctx
        narr = ctx["narratives"]
        assert len(narr) == 3
        # All should be template-sourced
        assert (narr["narrative_source"] == "generated").all()
        # Audit should reflect template-only
        audit = ctx["audit_entries"][0]
        assert audit.details["template_generated"] == 3
        assert audit.details["llm_generated"] == 0
        assert audit.details["method"] == "template"

    @pytest.mark.asyncio
    async def test_empty_material_produces_empty_output(self):
        """No material variances => empty narratives."""
        ctx = {"material_variances": pd.DataFrame(), "acct_meta": {}}
        await generate_narratives(ctx)
        assert ctx["narratives"].empty
        assert ctx["review_status"] == []


# ---------------------------------------------------------------------------
# Tests — LLM fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass5LLMFallback:
    """If LLM raises, falls back to template gracefully."""

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_exception(self):
        """LLM that throws should trigger template fallback."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(side_effect=Exception("API Error"))

        ctx = _build_minimal_context(n_rows=2, llm_client=mock_llm)
        await generate_narratives(ctx)

        narr = ctx["narratives"]
        assert len(narr) == 2
        # Should have fallen back to templates
        assert (narr["narrative_source"] == "generated").all()
        audit = ctx["audit_entries"][0]
        assert audit.details["template_generated"] == 2
        assert audit.details["llm_generated"] == 0

    @pytest.mark.asyncio
    async def test_falls_back_on_fallback_dict(self):
        """LLM returning fallback dict should trigger template path."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(
            return_value={"fallback": True, "content": "LLM not configured"}
        )

        ctx = _build_minimal_context(n_rows=2, llm_client=mock_llm)
        await generate_narratives(ctx)

        narr = ctx["narratives"]
        assert len(narr) == 2
        assert (narr["narrative_source"] == "generated").all()

    @pytest.mark.asyncio
    async def test_falls_back_on_invalid_json(self):
        """LLM returning non-JSON should trigger template path."""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "This is not JSON at all."

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        ctx = _build_minimal_context(n_rows=2, llm_client=mock_llm)
        await generate_narratives(ctx)

        narr = ctx["narratives"]
        assert len(narr) == 2
        assert (narr["narrative_source"] == "generated").all()


# ---------------------------------------------------------------------------
# Tests — LLM success path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass5LLMSuccess:
    """Successful LLM responses produce LLM-sourced narratives."""

    @pytest.mark.asyncio
    async def test_llm_narratives_used_when_available(self):
        """Valid LLM JSON response => source='llm'."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(
            return_value=_mock_llm_response(
                detail="LLM detail text.",
                midlevel="LLM midlevel.",
                summary="LLM summary.",
                oneliner="LLM one.",
            )
        )

        ctx = _build_minimal_context(n_rows=2, llm_client=mock_llm)
        await generate_narratives(ctx)

        narr = ctx["narratives"]
        assert len(narr) == 2
        assert (narr["narrative_source"] == "llm").all()
        assert narr.iloc[0]["narrative_detail"] == "LLM detail text."
        assert narr.iloc[0]["narrative_oneliner"] == "LLM one."

        audit = ctx["audit_entries"][0]
        assert audit.details["llm_generated"] == 2
        assert audit.details["template_generated"] == 0
        assert audit.details["method"] == "llm+template"

    @pytest.mark.asyncio
    async def test_llm_handles_markdown_wrapped_json(self):
        """LLM response wrapped in ```json``` fences should parse OK."""
        payload = json.dumps(
            {
                "detail": "Detail from LLM.",
                "midlevel": "Mid.",
                "summary": "Sum.",
                "oneliner": "One.",
            }
        )
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = f"```json\n{payload}\n```"

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        ctx = _build_minimal_context(n_rows=1, llm_client=mock_llm)
        await generate_narratives(ctx)

        narr = ctx["narratives"]
        assert narr.iloc[0]["narrative_detail"] == "Detail from LLM."
        assert narr.iloc[0]["narrative_source"] == "llm"

    @pytest.mark.asyncio
    async def test_review_status_created_for_llm_narratives(self):
        """Review entries should be created with AI_DRAFT for LLM narratives."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(
            return_value=_mock_llm_response("D", "M", "S", "O")
        )

        ctx = _build_minimal_context(n_rows=2, llm_client=mock_llm)
        await generate_narratives(ctx)

        reviews = ctx["review_status"]
        assert len(reviews) == 2
        for r in reviews:
            assert r["status"] == "AI_DRAFT"
            assert r["original_narrative"] == "D"


# ---------------------------------------------------------------------------
# Tests — _generate_llm_narrative helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateLLMNarrativeHelper:
    """Direct tests on the _generate_llm_narrative helper function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_llm_fails(self):
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("boom"))
        result = await _generate_llm_narrative(mock_llm, None, {}, {})
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_keys(self):
        """JSON missing required keys should return None."""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({"detail": "only detail"})

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        result = await _generate_llm_narrative(mock_llm, None, {}, {})
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self):
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=_mock_llm_response("d", "m", "s", "o")
        )
        result = await _generate_llm_narrative(mock_llm, None, {}, {})
        assert result == {"detail": "d", "midlevel": "m", "summary": "s", "oneliner": "o"}

    @pytest.mark.asyncio
    async def test_uses_rag_retriever_when_provided(self):
        """RAG retriever should be called for few-shot examples."""
        mock_commentary = MagicMock()
        mock_commentary.narrative_text = "Example commentary."

        mock_rag = MagicMock()
        mock_rag.retrieve_similar = AsyncMock(return_value=[mock_commentary])

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=_mock_llm_response("d", "m", "s", "o")
        )

        result = await _generate_llm_narrative(
            mock_llm, mock_rag, {"account_id": "acct_1"}, {"account_name": "Revenue"}
        )
        assert result is not None
        mock_rag.retrieve_similar.assert_called_once()
        # Check that LLM prompt included the example
        call_args = mock_llm.complete.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "Example commentary" in user_msg
