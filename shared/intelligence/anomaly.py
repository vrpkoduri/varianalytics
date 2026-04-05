"""Anomaly Detection — statistical outlier flagging using z-score.

Identifies variances whose magnitude has never (or rarely) occurred
in the historical record.

Example output:
    "Anomaly: $200K exceeds 36-month max ($150K) by 33%. Z-score: 3.2."
"""

from __future__ import annotations

import math
from typing import Any


# Z-score threshold for anomaly flagging
_Z_SCORE_THRESHOLD = 2.0


def compute_anomaly_score(
    current_amount: float,
    period_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute anomaly score using z-score from historical variance amounts.

    Args:
        current_amount: Current period's variance amount.
        period_history: Historical periods with variance_amount.

    Returns:
        Dict with is_anomaly, z_score, historical stats, note.
    """
    amounts = [
        h.get("variance_amount", 0)
        for h in period_history
        if isinstance(h.get("variance_amount"), (int, float))
    ]

    if len(amounts) < 3:
        return {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "z_score": 0.0,
            "historical_max": None,
            "historical_min": None,
            "percentile": 50,
            "note": "",
        }

    # Statistics
    n = len(amounts)
    mean = sum(amounts) / n
    variance = sum((x - mean) ** 2 for x in amounts) / n
    std = math.sqrt(variance) if variance > 0 else 0

    hist_max = max(amounts)
    hist_min = min(amounts)

    # Z-score
    z_score = (current_amount - mean) / std if std > 0 else 0.0

    # Anomaly score (0-1, based on absolute z-score)
    abs_z = abs(z_score)
    anomaly_score = min(abs_z / 4.0, 1.0)  # Normalize: z=4 → score=1.0

    # Percentile (approximate)
    below_count = sum(1 for a in amounts if a <= current_amount)
    percentile = int((below_count / n) * 100)

    is_anomaly = abs_z >= _Z_SCORE_THRESHOLD

    note = _build_note(
        is_anomaly, current_amount, z_score, hist_max, hist_min, n,
    )

    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 3),
        "z_score": round(z_score, 2),
        "historical_max": round(hist_max, 2),
        "historical_min": round(hist_min, 2),
        "percentile": percentile,
        "note": note,
    }


def _build_note(
    is_anomaly: bool,
    current: float,
    z_score: float,
    hist_max: float,
    hist_min: float,
    n: int,
) -> str:
    if not is_anomaly:
        return ""

    abs_current = abs(current)

    if current > hist_max:
        exceed_pct = ((current - hist_max) / abs(hist_max) * 100) if hist_max != 0 else 0
        return (
            f"Anomaly: ${abs_current:,.0f} exceeds {n}-month max "
            f"(${abs(hist_max):,.0f}) by {exceed_pct:.0f}%. Z-score: {z_score:.1f}."
        )
    elif current < hist_min:
        exceed_pct = ((hist_min - current) / abs(hist_min) * 100) if hist_min != 0 else 0
        return (
            f"Anomaly: ${abs_current:,.0f} below {n}-month min "
            f"(${abs(hist_min):,.0f}) by {exceed_pct:.0f}%. Z-score: {z_score:.1f}."
        )
    else:
        return f"Statistical outlier: z-score {z_score:.1f} (>{_Z_SCORE_THRESHOLD})."
