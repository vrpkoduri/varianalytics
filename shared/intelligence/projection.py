"""Cumulative Projection — full-year run-rate extrapolation.

Answers: "If this variance continues, what's the full-year impact?"

Example output:
    "Full-year impact: $3.2M at current run rate (6 months remaining)"
"""

from __future__ import annotations

from typing import Any, Optional


def compute_cumulative_projection(
    variance_amount: float,
    period_id: str,
    period_history: list[dict[str, Any]],
    fiscal_year_months: int = 12,
) -> dict[str, Any]:
    """Compute full-year projection from current + historical variances.

    Args:
        variance_amount: Current period's variance amount.
        period_id: Current period (e.g. "2026-06").
        period_history: Prior period variances from knowledge graph.
            Each dict has: period_id, variance_amount, variance_pct.
        fiscal_year_months: Months in fiscal year (default 12).

    Returns:
        Dict with months_elapsed, ytd_cumulative, run_rate, fy_projection, note.
    """
    # Determine months elapsed from period_id
    months_elapsed = _extract_month(period_id)
    if months_elapsed <= 0:
        months_elapsed = 1

    months_remaining = max(0, fiscal_year_months - months_elapsed)

    # Sum YTD cumulative (history + current)
    history_amounts = [
        h.get("variance_amount", 0)
        for h in period_history
        if isinstance(h.get("variance_amount"), (int, float))
    ]
    ytd_cumulative = sum(history_amounts) + variance_amount

    # Monthly run rate
    run_rate = ytd_cumulative / months_elapsed if months_elapsed > 0 else variance_amount

    # Full-year projection
    fy_projection = ytd_cumulative + (run_rate * months_remaining)

    # Build note
    note = _build_projection_note(
        fy_projection, run_rate, months_elapsed, months_remaining
    )

    return {
        "months_elapsed": months_elapsed,
        "months_remaining": months_remaining,
        "ytd_cumulative": round(ytd_cumulative, 2),
        "run_rate_monthly": round(run_rate, 2),
        "fy_projection": round(fy_projection, 2),
        "note": note,
    }


def _extract_month(period_id: str) -> int:
    """Extract month number from period_id like '2026-06'."""
    try:
        return int(period_id.split("-")[1])
    except (IndexError, ValueError):
        return 0


def _build_projection_note(
    fy_projection: float,
    run_rate: float,
    months_elapsed: int,
    months_remaining: int,
) -> str:
    """Build a concise projection note."""
    if months_remaining <= 0:
        return f"Full-year actual: ${abs(fy_projection):,.0f}."

    direction = "favorable" if fy_projection > 0 else "unfavorable"

    if abs(fy_projection) >= 1_000_000:
        proj_str = f"${abs(fy_projection)/1_000_000:.1f}M"
    else:
        proj_str = f"${abs(fy_projection):,.0f}"

    return (
        f"Full-year projection: {proj_str} {direction} "
        f"at current run rate ({months_remaining} months remaining)."
    )
