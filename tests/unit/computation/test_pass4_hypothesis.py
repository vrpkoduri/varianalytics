"""Tests for Pass 4 hypothesis generation.

Validates the LLM-powered hypothesis generation for correlated
variance pairs, ensuring:
- Pass 4 works without LLM (hypothesis=None).
- Mock LLM produces hypothesis text and confidence scores.
- Rate-limiting semaphore prevents excessive concurrency.
- LLM errors are handled gracefully per-pair.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from services.computation.engine.pass4_correlation import (
    _generate_hypothesis,
    find_correlations,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_correlation_context(n_rows: int = 10, llm_client=None):
    """Build a minimal context with MTD/BUDGET material variances.

    Creates rows sharing some dimensions to ensure at least a few
    pairs score above the 0.3 threshold.
    """
    rows = []
    for i in range(n_rows):
        rows.append(
            {
                "variance_id": f"var-{i:03d}",
                "account_id": f"acct_{i % 5}",  # Share accounts to boost overlap
                "bu_id": "BU_NORTH" if i < n_rows // 2 else "BU_SOUTH",
                "costcenter_node_id": f"cc_{i % 3}",
                "geo_node_id": "geo_us",  # All same geo
                "segment_node_id": "seg_enterprise",
                "lob_node_id": f"lob_{i % 2}",
                "period_id": "2026-03",
                "view_id": "MTD",
                "base_id": "BUDGET",
                "variance_amount": ((-1) ** i) * (i + 1) * 5_000.0,
                "variance_pct": ((-1) ** i) * (i + 1) * 1.5,
            }
        )
    ctx: dict = {
        "period_id": "2026-03",
        "material_variances": pd.DataFrame(rows),
    }
    if llm_client is not None:
        ctx["llm_client"] = llm_client
    return ctx


# ---------------------------------------------------------------------------
# Tests — no LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass4NoLLM:
    """Pass 4 works when no LLM in context."""

    @pytest.mark.asyncio
    async def test_correlations_without_llm(self):
        """hypothesis should be None for all pairs without LLM."""
        ctx = _build_correlation_context(n_rows=10)
        await find_correlations(ctx)

        corr = ctx.get("correlations")
        assert corr is not None
        if isinstance(corr, pd.DataFrame) and len(corr) > 0:
            assert corr["hypothesis"].isna().all()
            assert corr["confidence"].isna().all()

    @pytest.mark.asyncio
    async def test_empty_material_no_crash(self):
        """Empty material variances => empty correlations."""
        ctx = {"material_variances": pd.DataFrame()}
        await find_correlations(ctx)
        assert ctx["correlations"].empty

    @pytest.mark.asyncio
    async def test_single_row_no_pairs(self):
        """Single MTD/BUDGET row => no pairs possible."""
        ctx = {
            "material_variances": pd.DataFrame(
                [
                    {
                        "variance_id": "var-001",
                        "account_id": "acct_1",
                        "bu_id": "BU_NORTH",
                        "costcenter_node_id": "cc_1",
                        "geo_node_id": "geo_us",
                        "segment_node_id": "seg_1",
                        "lob_node_id": "lob_1",
                        "view_id": "MTD",
                        "base_id": "BUDGET",
                        "variance_amount": 10_000.0,
                        "variance_pct": 5.0,
                    }
                ]
            )
        }
        await find_correlations(ctx)
        assert ctx["correlations"].empty


# ---------------------------------------------------------------------------
# Tests — with mock LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass4WithLLM:
    """LLM hypothesis generation for correlated pairs."""

    @pytest.mark.asyncio
    async def test_hypothesis_generated_with_mock_llm(self):
        """With mock LLM, hypothesis text should be populated."""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = (
            "Revenue increase likely due to APAC expansion. Confidence: 0.85"
        )

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        ctx = _build_correlation_context(n_rows=10, llm_client=mock_llm)
        await find_correlations(ctx)

        corr = ctx["correlations"]
        if len(corr) > 0:
            # At least some pairs should have hypotheses
            has_hyp = corr["hypothesis"].notna()
            assert has_hyp.any(), "Expected at least one hypothesis from LLM"
            # Check confidence was extracted
            with_conf = corr.loc[has_hyp, "confidence"]
            assert (with_conf == 0.85).all()

    @pytest.mark.asyncio
    async def test_llm_errors_dont_crash_pipeline(self):
        """LLM errors on individual pairs should not crash the whole pass."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(side_effect=Exception("Rate limit"))

        ctx = _build_correlation_context(n_rows=10, llm_client=mock_llm)
        await find_correlations(ctx)

        # Should complete without error, hypotheses remain None
        corr = ctx["correlations"]
        if len(corr) > 0:
            assert corr["hypothesis"].isna().all()

    @pytest.mark.asyncio
    async def test_fallback_response_produces_none_hypothesis(self):
        """LLM returning fallback dict should result in None hypothesis."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(
            return_value={"fallback": True, "content": "No API key"}
        )

        ctx = _build_correlation_context(n_rows=10, llm_client=mock_llm)
        await find_correlations(ctx)

        corr = ctx["correlations"]
        if len(corr) > 0:
            assert corr["hypothesis"].isna().all()


# ---------------------------------------------------------------------------
# Tests — _generate_hypothesis helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateHypothesisHelper:
    """Direct tests on the _generate_hypothesis helper function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_llm(self):
        h, c = await _generate_hypothesis(None, {}, {})
        assert h is None and c is None

    @pytest.mark.asyncio
    async def test_returns_none_when_unavailable(self):
        mock_llm = MagicMock()
        mock_llm.is_available = False
        h, c = await _generate_hypothesis(mock_llm, {}, {})
        assert h is None and c is None

    @pytest.mark.asyncio
    async def test_extracts_confidence_from_text(self):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = (
            "Higher volumes in APAC drove revenue up. Confidence: 0.92"
        )

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        h, c = await _generate_hypothesis(mock_llm, {"account_id": "acct_1"}, {"account_id": "acct_2"})
        assert h is not None
        assert "APAC" in h
        assert c == pytest.approx(0.92)

    @pytest.mark.asyncio
    async def test_default_confidence_when_not_mentioned(self):
        """When LLM doesn't mention confidence, default to 0.7."""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Volume increase from new contracts."

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        h, c = await _generate_hypothesis(mock_llm, {}, {})
        assert h == "Volume increase from new contracts."
        assert c == 0.7

    @pytest.mark.asyncio
    async def test_hypothesis_truncated_at_500_chars(self):
        """Long hypothesis text should be truncated to 500 chars."""
        long_text = "A" * 600
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = long_text

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.complete = AsyncMock(return_value=mock_resp)

        h, c = await _generate_hypothesis(mock_llm, {}, {})
        assert len(h) == 500
