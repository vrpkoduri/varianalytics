"""Variance Persistence — tracks whether a variance is decaying, stable, or widening.

Answers: "Is this variance getting better, worse, or staying the same?"

Example output:
    "Decaying — was -10.2% in May, now -8.7%. Narrowing at 0.5pp/month."
"""

from __future__ import annotations

from typing import Any

# Minimum periods needed for meaningful persistence analysis
_MIN_PERIODS = 3

# Threshold for "stable" — changes within this range are considered flat
_STABLE_THRESHOLD_PP = 0.3  # percentage points per month


def compute_persistence(
    period_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess variance persistence trend from period history.

    Args:
        period_history: List of dicts with period_id, variance_amount,
            variance_pct. Should be sorted oldest-first.

    Returns:
        Dict with trend, periods_tracked, start/current pct,
        change_rate, and note.
    """
    if not period_history or len(period_history) < 2:
        return {
            "trend": "new",
            "periods_tracked": len(period_history) if period_history else 0,
            "start_pct": None,
            "current_pct": None,
            "change_rate": 0.0,
            "note": "Insufficient history for persistence analysis." if period_history else "",
        }

    # Extract variance_pct values (filter None/NaN)
    pcts = []
    for h in period_history:
        pct = h.get("variance_pct")
        if pct is not None and isinstance(pct, (int, float)):
            pcts.append((h.get("period_id", ""), float(pct)))

    if len(pcts) < 2:
        return {
            "trend": "new",
            "periods_tracked": len(pcts),
            "start_pct": pcts[0][1] if pcts else None,
            "current_pct": pcts[-1][1] if pcts else None,
            "change_rate": 0.0,
            "note": "",
        }

    start_period, start_pct = pcts[0]
    current_period, current_pct = pcts[-1]
    periods_tracked = len(pcts)

    # Compute change in absolute variance percentage
    abs_start = abs(start_pct)
    abs_current = abs(current_pct)
    total_change = abs_current - abs_start
    change_rate = total_change / max(periods_tracked - 1, 1)

    # Classify trend
    if periods_tracked < _MIN_PERIODS:
        trend = "new"
    elif abs(change_rate) <= _STABLE_THRESHOLD_PP:
        trend = "stable"
    elif change_rate < 0:
        trend = "decaying"  # Absolute variance is shrinking → improving
    else:
        trend = "widening"  # Absolute variance is growing → worsening

    # Build note
    note = _build_persistence_note(
        trend, start_pct, current_pct, change_rate,
        start_period, current_period, periods_tracked,
    )

    return {
        "trend": trend,
        "periods_tracked": periods_tracked,
        "start_pct": round(start_pct, 2),
        "current_pct": round(current_pct, 2),
        "change_rate": round(change_rate, 2),
        "note": note,
    }


def _build_persistence_note(
    trend: str,
    start_pct: float,
    current_pct: float,
    change_rate: float,
    start_period: str,
    current_period: str,
    periods_tracked: int,
) -> str:
    """Build a concise persistence note."""
    if trend == "new":
        return f"New variance — only {periods_tracked} months of history."

    # Extract month names for readability
    start_month = _month_name(start_period)
    current_month = _month_name(current_period)

    abs_rate = abs(change_rate)
    rate_str = f"{abs_rate:.1f}pp/month"

    if trend == "decaying":
        direction = "Narrowing" if current_pct < 0 else "Improving"
        return (
            f"Decaying — was {start_pct:+.1f}% in {start_month}, "
            f"now {current_pct:+.1f}%. {direction} at {rate_str}."
        )
    elif trend == "widening":
        direction = "Widening" if abs(current_pct) > abs(start_pct) else "Worsening"
        return (
            f"Widening — was {start_pct:+.1f}% in {start_month}, "
            f"now {current_pct:+.1f}%. {direction} at {rate_str}."
        )
    else:  # stable
        return (
            f"Stable — holding at ~{current_pct:+.1f}% "
            f"over {periods_tracked} months (change < {_STABLE_THRESHOLD_PP}pp/month)."
        )


_MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _month_name(period_id: str) -> str:
    """Extract month name from period_id like '2026-06'."""
    try:
        month = int(period_id.split("-")[1])
        return _MONTH_NAMES[month] if 1 <= month <= 12 else period_id
    except (IndexError, ValueError):
        return period_id
