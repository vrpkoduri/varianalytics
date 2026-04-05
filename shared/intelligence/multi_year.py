"""Multi-Year Patterns — detects repeating seasonal or structural patterns.

Compares the same month/quarter across multiple years to identify
recurring patterns (e.g., Q2 softness every year).

Example output:
    "Same Q2 pattern: -2.8% in 2024, -3.2% in 2025. Recovered Q3 both years."
"""

from __future__ import annotations

from typing import Any, Optional

# Tolerance for pattern match (±Xpp)
_PATTERN_TOLERANCE_PP = 2.0


def compute_multi_year_pattern(
    period_history: list[dict[str, Any]],
    current_period_id: str,
) -> dict[str, Any]:
    """Detect multi-year repeating patterns.

    Args:
        period_history: Full variance history (up to 36 months), sorted oldest-first.
            Each dict has period_id, variance_amount, variance_pct.
        current_period_id: Current period (e.g. "2026-06").

    Returns:
        Dict with pattern_detected, pattern_type, same_quarter comparisons, note.
    """
    if not period_history or len(period_history) < 12:
        return _empty_result()

    current_month = _extract_month(current_period_id)
    current_year = _extract_year(current_period_id)
    if not current_month or not current_year:
        return _empty_result()

    # Find same month in prior years
    prior_year_match = _find_same_month(period_history, current_year - 1, current_month)
    two_year_match = _find_same_month(period_history, current_year - 2, current_month)

    # Current period's variance_pct
    current_pct = None
    for h in reversed(period_history):
        if h.get("period_id") == current_period_id:
            current_pct = h.get("variance_pct")
            break

    if current_pct is None:
        # Use last entry if current period not in history
        current_pct = period_history[-1].get("variance_pct") if period_history else None

    if current_pct is None:
        return _empty_result()

    # Check for pattern
    pattern_detected = False
    pattern_type = "none"

    if prior_year_match and two_year_match:
        py_pct = prior_year_match.get("variance_pct", 0)
        ty_pct = two_year_match.get("variance_pct", 0)
        # All three years same sign and within tolerance
        if (_same_sign(current_pct, py_pct) and _same_sign(current_pct, ty_pct)
                and abs(abs(current_pct) - abs(py_pct)) <= _PATTERN_TOLERANCE_PP
                and abs(abs(current_pct) - abs(ty_pct)) <= _PATTERN_TOLERANCE_PP):
            pattern_detected = True
            pattern_type = "seasonal_repeat"

    elif prior_year_match:
        py_pct = prior_year_match.get("variance_pct", 0)
        if (_same_sign(current_pct, py_pct)
                and abs(abs(current_pct) - abs(py_pct)) <= _PATTERN_TOLERANCE_PP):
            pattern_detected = True
            pattern_type = "seasonal_repeat"

    # Check for structural pattern (same direction but growing each year)
    if prior_year_match and not pattern_detected:
        py_pct = prior_year_match.get("variance_pct", 0)
        if _same_sign(current_pct, py_pct) and abs(current_pct) > abs(py_pct) * 1.2:
            pattern_detected = True
            pattern_type = "structural"

    note = _build_note(
        pattern_detected, pattern_type, current_pct, current_month,
        prior_year_match, two_year_match, current_year,
    )

    return {
        "pattern_detected": pattern_detected,
        "pattern_type": pattern_type,
        "current_pct": round(current_pct, 2) if current_pct else None,
        "same_quarter_prior_year": prior_year_match,
        "same_quarter_two_years": two_year_match,
        "note": note,
    }


def _find_same_month(
    history: list[dict], year: int, month: int
) -> Optional[dict[str, Any]]:
    target = f"{year}-{month:02d}"
    for h in history:
        if h.get("period_id") == target:
            return {"period": target, "variance_pct": h.get("variance_pct", 0)}
    return None


def _same_sign(a: float, b: float) -> bool:
    return (a >= 0) == (b >= 0)


def _extract_month(period_id: str) -> int:
    try:
        return int(period_id.split("-")[1])
    except (IndexError, ValueError):
        return 0


def _extract_year(period_id: str) -> int:
    try:
        return int(period_id.split("-")[0])
    except (IndexError, ValueError):
        return 0


_MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _build_note(
    detected: bool, ptype: str, current_pct: float, month: int,
    prior: Optional[dict], two_year: Optional[dict], current_year: int,
) -> str:
    if not detected:
        return ""

    month_name = _MONTH_NAMES[month] if 1 <= month <= 12 else str(month)

    if ptype == "seasonal_repeat":
        parts = []
        if two_year:
            parts.append(f"{two_year['variance_pct']:+.1f}% in {current_year-2}")
        if prior:
            parts.append(f"{prior['variance_pct']:+.1f}% in {current_year-1}")
        parts.append(f"{current_pct:+.1f}% in {current_year}")
        return f"Recurring {month_name} pattern: {', '.join(parts)}."

    elif ptype == "structural":
        py_pct = prior["variance_pct"] if prior else 0
        return (
            f"Structural trend: {month_name} variance grew from "
            f"{py_pct:+.1f}% ({current_year-1}) to {current_pct:+.1f}% ({current_year})."
        )

    return ""


def _empty_result() -> dict[str, Any]:
    return {
        "pattern_detected": False,
        "pattern_type": "none",
        "current_pct": None,
        "same_quarter_prior_year": None,
        "same_quarter_two_years": None,
        "note": "",
    }
