"""COGS Variance Decomposition — Rate x Volume x Mix.

Decomposes a cost-of-goods-sold variance into three drivers using a
fallback proportional method when unit cost data is unavailable (MVP):

- Rate effect:   50% of total variance
- Volume effect: 35% of total variance
- Mix effect:    15% of total variance
- Residual:      total - sum(components)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default proportional splits for the fallback method.
_DEFAULT_RATE_SPLIT = 0.50
_DEFAULT_VOLUME_SPLIT = 0.35
_DEFAULT_MIX_SPLIT = 0.15


def decompose_cogs(
    row: dict[str, Any],
    ff_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decompose a COGS variance into Rate x Volume x Mix.

    Args:
        row: Material variance row dict. Must contain at least
             ``variance_amount`` and ``variance_id``.
        ff_row: Optional matching row from ``fact_financials``.
                Reserved for Phase 2 when unit cost data becomes available.

    Returns:
        Dict with keys: rate, volume, mix, residual, method, is_fallback.
    """
    variance = row.get("variance_amount", 0.0)
    if variance == 0.0:
        return _zero_result()

    rate = variance * _DEFAULT_RATE_SPLIT
    volume = variance * _DEFAULT_VOLUME_SPLIT
    mix = variance * _DEFAULT_MIX_SPLIT

    residual = variance - (rate + volume + mix)

    return {
        "rate": round(rate, 2),
        "volume": round(volume, 2),
        "mix": round(mix, 2),
        "residual": round(residual, 2),
        "method": "rate_vol_mix",
        "is_fallback": True,
    }


def _zero_result() -> dict[str, Any]:
    """Return a zeroed-out decomposition for zero-variance rows."""
    return {
        "rate": 0.0,
        "volume": 0.0,
        "mix": 0.0,
        "residual": 0.0,
        "method": "rate_vol_mix",
        "is_fallback": True,
    }
