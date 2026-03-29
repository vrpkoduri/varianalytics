"""Revenue Variance Decomposition — Volume x Price x Mix x FX.

Decomposes a revenue variance into four orthogonal drivers using a
fallback proportional method when unit-level data is unavailable (MVP):

- Volume effect:  60% of total variance (default split)
- Price effect:   25% of total variance
- Mix effect:     10% of total variance
- FX effect:      Computed from actual_local_amount * (actual_fx_rate - budget_fx_rate)
                  when FX data is present; remaining variance redistributed.
- Residual:       total - sum(components)

When FX data is available the FX component is calculated first and the
remaining variance is split proportionally among Volume/Price/Mix.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default proportional splits for the fallback method (no unit data).
_DEFAULT_VOLUME_SPLIT = 0.60
_DEFAULT_PRICE_SPLIT = 0.25
_DEFAULT_MIX_SPLIT = 0.10
# Remaining 5% is FX placeholder when no FX data exists.


def decompose_revenue(
    row: dict[str, Any],
    ff_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decompose a revenue variance into Volume x Price x Mix x FX.

    Args:
        row: Material variance row dict. Must contain at least
             ``variance_amount`` and ``variance_id``.
        ff_row: Optional matching row from ``fact_financials`` used to
                extract FX rate data (actual_fx_rate, budget_fx_rate,
                actual_local_amount).

    Returns:
        Dict with keys: volume, price, mix, fx, residual, method, is_fallback.
    """
    variance = row.get("variance_amount", 0.0)
    if variance == 0.0:
        return _zero_result()

    fx_effect = 0.0
    fx_computed = False

    # ------------------------------------------------------------------
    # FX component: use actual rate data when available
    # ------------------------------------------------------------------
    if ff_row is not None:
        actual_fx = ff_row.get("actual_fx_rate")
        budget_fx = ff_row.get("budget_fx_rate")
        actual_local = ff_row.get("actual_local_amount")

        if (
            actual_fx is not None
            and budget_fx is not None
            and actual_local is not None
            and actual_fx != budget_fx
        ):
            fx_effect = actual_local * (actual_fx - budget_fx)
            fx_computed = True
            logger.debug(
                "Revenue FX effect for %s: %.2f (local=%.2f, rate_delta=%.4f)",
                row.get("variance_id", "?"),
                fx_effect,
                actual_local,
                actual_fx - budget_fx,
            )

    # ------------------------------------------------------------------
    # Remaining variance after FX
    # ------------------------------------------------------------------
    remaining = variance - fx_effect

    # Proportional split on the remaining variance
    volume = remaining * _DEFAULT_VOLUME_SPLIT
    price = remaining * _DEFAULT_PRICE_SPLIT
    mix = remaining * _DEFAULT_MIX_SPLIT

    # Residual is whatever is left after the proportional + FX allocation
    residual = variance - (volume + price + mix + fx_effect)

    return {
        "volume": round(volume, 2),
        "price": round(price, 2),
        "mix": round(mix, 2),
        "fx": round(fx_effect, 2),
        "residual": round(residual, 2),
        "method": "vol_price_mix_fx",
        "is_fallback": True,
        "fx_computed": fx_computed,
    }


def _zero_result() -> dict[str, Any]:
    """Return a zeroed-out decomposition for zero-variance rows."""
    return {
        "volume": 0.0,
        "price": 0.0,
        "mix": 0.0,
        "fx": 0.0,
        "residual": 0.0,
        "method": "vol_price_mix_fx",
        "is_fallback": True,
        "fx_computed": False,
    }
