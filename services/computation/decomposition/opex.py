"""OpEx Variance Decomposition — Rate x Volume x Timing x One-time.

Decomposes an operating expense variance into four drivers using a
fallback proportional method when detailed driver data is unavailable (MVP):

- Rate effect:    40% of total variance
- Volume effect:  30% of total variance
- Timing effect:  20% of total variance
- One-time effect: 10% of total variance
- Residual:       total - sum(components)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default proportional splits for the fallback method.
_DEFAULT_RATE_SPLIT = 0.40
_DEFAULT_VOLUME_SPLIT = 0.30
_DEFAULT_TIMING_SPLIT = 0.20
_DEFAULT_ONETIME_SPLIT = 0.10


def decompose_opex(
    row: dict[str, Any],
    ff_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decompose an OpEx variance into Rate x Volume x Timing x One-time.

    Args:
        row: Material variance row dict. Must contain at least
             ``variance_amount`` and ``variance_id``.
        ff_row: Optional matching row from ``fact_financials``.
                Reserved for Phase 2 when headcount / transaction volume
                data becomes available.

    Returns:
        Dict with keys: rate, volume, timing, onetime, residual, method,
        is_fallback.
    """
    variance = row.get("variance_amount", 0.0)
    if variance == 0.0:
        return _zero_result()

    rate = variance * _DEFAULT_RATE_SPLIT
    volume = variance * _DEFAULT_VOLUME_SPLIT
    timing = variance * _DEFAULT_TIMING_SPLIT
    onetime = variance * _DEFAULT_ONETIME_SPLIT

    residual = variance - (rate + volume + timing + onetime)

    return {
        "rate": round(rate, 2),
        "volume": round(volume, 2),
        "timing": round(timing, 2),
        "onetime": round(onetime, 2),
        "residual": round(residual, 2),
        "method": "rate_vol_timing_onetime",
        "is_fallback": True,
    }


def _zero_result() -> dict[str, Any]:
    """Return a zeroed-out decomposition for zero-variance rows."""
    return {
        "rate": 0.0,
        "volume": 0.0,
        "timing": 0.0,
        "onetime": 0.0,
        "residual": 0.0,
        "method": "rate_vol_timing_onetime",
        "is_fallback": True,
    }
