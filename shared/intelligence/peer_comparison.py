"""Peer Comparison — systemic vs isolated vs outlier pattern detection.

Compares the same account across all BUs to detect whether a variance
is enterprise-wide (systemic) or BU-specific (isolated).

Example output:
    "Systemic — 4/5 BUs show same direction. Enterprise-wide pattern."
"""

from __future__ import annotations

from typing import Any

# Thresholds
_SYSTEMIC_THRESHOLD = 0.80  # ≥80% BUs same direction → systemic
_OUTLIER_MULTIPLIER = 2.0   # >2x median → outlier within systemic pattern


def compute_peer_comparison(
    peer_variances: list[dict[str, Any]],
    current_bu_id: str,
    current_variance_amount: float,
    total_bus: int = 5,
) -> dict[str, Any]:
    """Compare variance across peer BUs.

    Args:
        peer_variances: From graph.get_peer_variances() — same account, diff BU.
        current_bu_id: This variance's BU.
        current_variance_amount: This variance's dollar amount.
        total_bus: Total BUs in the system (default 5).

    Returns:
        Dict with pattern, bus_affected, current_rank, note.
    """
    if not peer_variances:
        return {
            "pattern": "isolated",
            "bus_affected": 1,
            "bus_same_direction": 0,
            "current_rank": 1,
            "note": "No peer data — BU-specific variance.",
        }

    # Include current BU in the comparison
    all_variances = peer_variances + [{
        "bu_id": current_bu_id,
        "variance_amount": current_variance_amount,
    }]

    bus_total = len(all_variances)
    current_sign = 1 if current_variance_amount >= 0 else -1

    # Count BUs with same direction
    same_direction = sum(
        1 for p in all_variances
        if (p.get("variance_amount", 0) >= 0) == (current_sign >= 0)
    )

    same_direction_pct = same_direction / bus_total if bus_total > 0 else 0

    # Rank by absolute amount
    sorted_by_abs = sorted(all_variances, key=lambda x: abs(x.get("variance_amount", 0)), reverse=True)
    current_rank = next(
        (i + 1 for i, v in enumerate(sorted_by_abs) if v.get("bu_id") == current_bu_id),
        bus_total,
    )

    # Determine pattern
    if same_direction_pct >= _SYSTEMIC_THRESHOLD:
        # Check for outlier
        amounts = [abs(p.get("variance_amount", 0)) for p in all_variances]
        amounts.sort()
        median_amount = amounts[len(amounts) // 2] if amounts else 0
        current_abs = abs(current_variance_amount)

        if median_amount > 0 and current_abs > median_amount * _OUTLIER_MULTIPLIER:
            pattern = "outlier"
        else:
            pattern = "systemic"
    else:
        pattern = "isolated"

    # Build note
    note = _build_peer_note(pattern, same_direction, bus_total, current_rank)

    return {
        "pattern": pattern,
        "bus_affected": bus_total,
        "bus_same_direction": same_direction,
        "current_rank": current_rank,
        "note": note,
    }


def _build_peer_note(
    pattern: str, same_direction: int, total: int, rank: int
) -> str:
    if pattern == "systemic":
        return f"Systemic — {same_direction}/{total} BUs show same direction. Enterprise-wide pattern."
    elif pattern == "outlier":
        return (
            f"Outlier — {same_direction}/{total} BUs same direction, "
            f"but this BU ranked #{rank} by magnitude (>2x median). BU-amplified systemic issue."
        )
    else:
        return f"Isolated — only {same_direction}/{total} BUs share this direction. BU-specific variance."
