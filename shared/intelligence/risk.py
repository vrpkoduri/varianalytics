"""Risk Classification — categorizes variance drivers by controllability.

Uses decomposition components to determine whether a variance is driven
by controllable factors (pricing, operations) or uncontrollable factors
(FX rates, market demand).

Example output:
    "FX-driven (65%): uncontrollable. Remaining volume/price: controllable."
"""

from __future__ import annotations

from typing import Any, Optional


# Controllability mapping by decomposition component
_CONTROLLABILITY: dict[str, str] = {
    "fx": "uncontrollable",
    "volume": "partially_controllable",
    "price": "controllable",
    "rate": "controllable",
    "mix": "controllable",
    "timing": "controllable",
    "onetime": "controllable",
}

# Human-readable labels
_CONTROLLABILITY_LABELS: dict[str, str] = {
    "uncontrollable": "uncontrollable (external market)",
    "partially_controllable": "partially controllable (market demand)",
    "controllable": "controllable (operational decision)",
}

# Threshold for a component to be considered "dominant"
_DOMINANT_THRESHOLD = 0.40  # 40%


def classify_risk(
    decomposition: Optional[dict[str, Any]],
    pl_category: str = "",
) -> dict[str, Any]:
    """Classify risk based on decomposition drivers.

    Args:
        decomposition: Decomposition dict with 'components' key.
            e.g. {"method": "vol_price_mix_fx", "components": {"volume": 50K, "price": 20K, "fx": 130K}}
        pl_category: P&L category (Revenue, COGS, OpEx).

    Returns:
        Dict with classification, primary driver, controllability, and note.
    """
    if not decomposition or not decomposition.get("components"):
        return {
            "classification": "unknown",
            "primary_driver": None,
            "driver_pct": 0.0,
            "controllability": "unknown",
            "note": "",
        }

    components = decomposition["components"]
    if not isinstance(components, dict) or not components:
        return {
            "classification": "unknown",
            "primary_driver": None,
            "driver_pct": 0.0,
            "controllability": "unknown",
            "note": "",
        }

    # Calculate absolute total and percentages
    abs_total = sum(abs(v) for v in components.values() if isinstance(v, (int, float)))
    if abs_total == 0:
        return {
            "classification": "unknown",
            "primary_driver": None,
            "driver_pct": 0.0,
            "controllability": "unknown",
            "note": "",
        }

    # Find component percentages (sorted by absolute contribution)
    comp_pcts: list[tuple[str, float]] = []
    for comp_name, comp_value in components.items():
        if isinstance(comp_value, (int, float)) and comp_name not in ("residual", "method", "is_fallback"):
            pct = abs(comp_value) / abs_total
            comp_pcts.append((comp_name, pct))

    comp_pcts.sort(key=lambda x: x[1], reverse=True)

    if not comp_pcts:
        return {
            "classification": "unknown",
            "primary_driver": None,
            "driver_pct": 0.0,
            "controllability": "unknown",
            "note": "",
        }

    # Primary driver
    primary_name, primary_pct = comp_pcts[0]
    primary_ctrl = _CONTROLLABILITY.get(primary_name, "unknown")

    # Classification based on dominant driver
    if primary_pct >= _DOMINANT_THRESHOLD:
        classification = primary_ctrl
    else:
        classification = "mixed_drivers"

    # Build note
    note = _build_risk_note(comp_pcts, classification, primary_name, primary_pct)

    return {
        "classification": classification,
        "primary_driver": primary_name,
        "driver_pct": round(primary_pct, 3),
        "controllability": _CONTROLLABILITY_LABELS.get(classification, classification),
        "note": note,
    }


def _build_risk_note(
    comp_pcts: list[tuple[str, float]],
    classification: str,
    primary_name: str,
    primary_pct: float,
) -> str:
    """Build a concise risk classification note."""
    primary_label = primary_name.upper()
    ctrl_label = _CONTROLLABILITY.get(primary_name, "unknown")

    if classification == "mixed_drivers":
        top_names = [f"{n} ({p:.0%})" for n, p in comp_pcts[:3]]
        return f"Mixed drivers: {', '.join(top_names)}."

    note = f"{primary_label}-driven ({primary_pct:.0%}): {ctrl_label}."

    # Add secondary drivers
    remaining = [(n, p) for n, p in comp_pcts[1:] if p >= 0.10]
    if remaining:
        remaining_names = "/".join(n for n, _ in remaining[:2])
        remaining_ctrl = _CONTROLLABILITY.get(remaining[0][0], "")
        if remaining_ctrl and remaining_ctrl != ctrl_label:
            note += f" Remaining {remaining_names}: {remaining_ctrl}."

    return note
