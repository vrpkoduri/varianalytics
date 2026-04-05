"""Materiality Context — puts variance in perspective of total P&L.

Answers: "How big is this variance relative to revenue, EBITDA, etc.?"

Example output:
    "$200K is 0.3% of revenue but 8.0% of EBITDA"
"""

from __future__ import annotations

from typing import Any


def compute_materiality_context(
    variance_amount: float,
    period_totals: dict[str, float],
) -> dict[str, Any]:
    """Compute materiality percentages against P&L totals.

    Args:
        variance_amount: The variance dollar amount.
        period_totals: Dict of P&L totals, e.g.:
            {"revenue": 60_000_000, "ebitda": 2_500_000, "gross_profit": 15_000_000}

    Returns:
        Dict with percentage impacts and human-readable note.
    """
    abs_amount = abs(variance_amount)
    result: dict[str, Any] = {}

    # Compute percentage of each total
    percentages: dict[str, float] = {}
    for metric, total in period_totals.items():
        if total and abs(total) > 0:
            pct = abs_amount / abs(total)
            percentages[f"pct_of_{metric}"] = round(pct, 6)
            result[f"pct_of_{metric}"] = round(pct, 6)

    # Find which metric the variance is most material to
    if percentages:
        most_material = max(percentages, key=percentages.get)  # type: ignore[arg-type]
        result["most_material_to"] = most_material.replace("pct_of_", "")
        result["most_material_pct"] = percentages[most_material]
    else:
        result["most_material_to"] = None
        result["most_material_pct"] = 0.0

    # Build human-readable note
    result["note"] = _build_materiality_note(abs_amount, percentages, period_totals)

    return result


def _build_materiality_note(
    abs_amount: float,
    percentages: dict[str, float],
    period_totals: dict[str, float],
) -> str:
    """Build a concise materiality note string."""
    if not percentages:
        return ""

    amount_str = f"${abs_amount:,.0f}"

    # Find the lowest and highest impact for contrast
    sorted_pcts = sorted(percentages.items(), key=lambda x: x[1])

    if len(sorted_pcts) >= 2:
        low_key, low_pct = sorted_pcts[0]
        high_key, high_pct = sorted_pcts[-1]

        low_name = low_key.replace("pct_of_", "").replace("_", " ").title()
        high_name = high_key.replace("pct_of_", "").replace("_", " ").title()

        return (
            f"{amount_str} is {low_pct:.1%} of {low_name} "
            f"but {high_pct:.1%} of {high_name}."
        )
    elif len(sorted_pcts) == 1:
        key, pct = sorted_pcts[0]
        name = key.replace("pct_of_", "").replace("_", " ").title()
        return f"{amount_str} represents {pct:.1%} of {name}."

    return ""
