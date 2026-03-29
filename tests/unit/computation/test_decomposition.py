"""Unit tests for variance decomposition — Revenue, COGS, and OpEx.

Tests the fallback proportional decomposition methods, verifying that
components sum to the total variance (within rounding tolerance) and
that zero-variance inputs produce all-zero outputs.
"""

from __future__ import annotations

import pytest

from services.computation.decomposition.cogs import decompose_cogs
from services.computation.decomposition.opex import decompose_opex
from services.computation.decomposition.revenue import decompose_revenue


# ---------------------------------------------------------------------------
# Revenue Decomposition Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRevenueDecomposition:
    """Test Revenue decomposition: Volume x Price x Mix x FX."""

    def test_revenue_fallback_components_sum(self) -> None:
        """Volume + Price + Mix + FX + Residual should equal total variance.

        With fallback proportional method (no FX data):
        - Volume = 60% of variance
        - Price = 25%
        - Mix = 10%
        - FX = 0 (no FX data)
        - Residual = 5% (remainder)
        """
        row = {"variance_amount": 100_000.0, "variance_id": "test-001"}
        result = decompose_revenue(row)

        total = result["volume"] + result["price"] + result["mix"] + result["fx"] + result["residual"]
        assert total == pytest.approx(100_000.0, abs=0.01)
        assert result["volume"] == pytest.approx(60_000.0, abs=0.01)
        assert result["price"] == pytest.approx(25_000.0, abs=0.01)
        assert result["mix"] == pytest.approx(10_000.0, abs=0.01)
        assert result["fx"] == 0.0
        assert result["is_fallback"] is True
        assert result["method"] == "vol_price_mix_fx"

    def test_revenue_negative_variance(self) -> None:
        """Negative variance should decompose with negative components."""
        row = {"variance_amount": -50_000.0, "variance_id": "test-002"}
        result = decompose_revenue(row)

        total = result["volume"] + result["price"] + result["mix"] + result["fx"] + result["residual"]
        assert total == pytest.approx(-50_000.0, abs=0.01)
        assert result["volume"] < 0
        assert result["price"] < 0

    def test_revenue_with_fx_data(self) -> None:
        """When FX data is available, the FX component should be computed
        and the remaining variance redistributed.
        """
        row = {"variance_amount": 100_000.0, "variance_id": "test-003"}
        ff_row = {
            "actual_fx_rate": 1.10,
            "budget_fx_rate": 1.00,
            "actual_local_amount": 200_000.0,
        }
        result = decompose_revenue(row, ff_row)

        # FX = 200K * (1.10 - 1.00) = 20K
        assert result["fx"] == pytest.approx(20_000.0, abs=0.01)
        assert result["fx_computed"] is True

        # Total should still equal variance
        total = result["volume"] + result["price"] + result["mix"] + result["fx"] + result["residual"]
        assert total == pytest.approx(100_000.0, abs=0.01)

    def test_revenue_zero_variance_returns_zeros(self) -> None:
        """Zero variance should return all zero components."""
        row = {"variance_amount": 0.0, "variance_id": "test-004"}
        result = decompose_revenue(row)

        assert result["volume"] == 0.0
        assert result["price"] == 0.0
        assert result["mix"] == 0.0
        assert result["fx"] == 0.0
        assert result["residual"] == 0.0


# ---------------------------------------------------------------------------
# COGS Decomposition Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCOGSDecomposition:
    """Test COGS decomposition: Rate x Volume x Mix."""

    def test_cogs_fallback_components_sum(self) -> None:
        """Rate + Volume + Mix + Residual should equal total variance.

        With fallback proportional method:
        - Rate = 50%
        - Volume = 35%
        - Mix = 15%
        """
        row = {"variance_amount": 80_000.0, "variance_id": "test-010"}
        result = decompose_cogs(row)

        total = result["rate"] + result["volume"] + result["mix"] + result["residual"]
        assert total == pytest.approx(80_000.0, abs=0.01)
        assert result["rate"] == pytest.approx(40_000.0, abs=0.01)
        assert result["volume"] == pytest.approx(28_000.0, abs=0.01)
        assert result["mix"] == pytest.approx(12_000.0, abs=0.01)
        assert result["is_fallback"] is True
        assert result["method"] == "rate_vol_mix"

    def test_cogs_zero_variance_returns_zeros(self) -> None:
        """Zero variance should return all zero components."""
        row = {"variance_amount": 0.0, "variance_id": "test-011"}
        result = decompose_cogs(row)

        assert result["rate"] == 0.0
        assert result["volume"] == 0.0
        assert result["mix"] == 0.0
        assert result["residual"] == 0.0


# ---------------------------------------------------------------------------
# OpEx Decomposition Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOpExDecomposition:
    """Test OpEx decomposition: Rate x Volume x Timing x One-time."""

    def test_opex_fallback_components_sum(self) -> None:
        """Rate + Volume + Timing + Onetime + Residual should equal total variance.

        With fallback proportional method:
        - Rate = 40%
        - Volume = 30%
        - Timing = 20%
        - Onetime = 10%
        """
        row = {"variance_amount": 200_000.0, "variance_id": "test-020"}
        result = decompose_opex(row)

        total = (
            result["rate"]
            + result["volume"]
            + result["timing"]
            + result["onetime"]
            + result["residual"]
        )
        assert total == pytest.approx(200_000.0, abs=0.01)
        assert result["rate"] == pytest.approx(80_000.0, abs=0.01)
        assert result["volume"] == pytest.approx(60_000.0, abs=0.01)
        assert result["timing"] == pytest.approx(40_000.0, abs=0.01)
        assert result["onetime"] == pytest.approx(20_000.0, abs=0.01)
        assert result["is_fallback"] is True
        assert result["method"] == "rate_vol_timing_onetime"

    def test_opex_zero_variance_returns_zeros(self) -> None:
        """Zero variance should return all zero components."""
        row = {"variance_amount": 0.0, "variance_id": "test-021"}
        result = decompose_opex(row)

        assert result["rate"] == 0.0
        assert result["volume"] == 0.0
        assert result["timing"] == 0.0
        assert result["onetime"] == 0.0
        assert result["residual"] == 0.0

    def test_opex_negative_variance(self) -> None:
        """Negative variance should decompose with negative components."""
        row = {"variance_amount": -100_000.0, "variance_id": "test-022"}
        result = decompose_opex(row)

        total = (
            result["rate"]
            + result["volume"]
            + result["timing"]
            + result["onetime"]
            + result["residual"]
        )
        assert total == pytest.approx(-100_000.0, abs=0.01)
        assert result["rate"] < 0
        assert result["volume"] < 0
