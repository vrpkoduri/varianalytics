"""Market Context — external factor framing for variance narratives.

Loads market context data (FX rates, sector performance, macro factors)
from YAML config and provides relevant context for a given period.

Example output:
    "Market: EUR weakened 4.2%. Insurance sector -2.3% in Q2 2026."
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml


_DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent / "config" / "market_context.yaml",
    Path("shared/config/market_context.yaml"),
]


def compute_market_context(
    period_id: str,
    pl_category: str = "",
    geo_node: str = "",
    config_path: Optional[str] = None,
) -> dict[str, Any]:
    """Get market context for a given period.

    Args:
        period_id: Period (e.g. "2026-06").
        pl_category: P&L category for relevance filtering.
        geo_node: Geography node for regional context.
        config_path: Override config file path.

    Returns:
        Dict with has_market_context, quarter, factors, notes, and note string.
    """
    config = _load_config(config_path)
    if not config:
        return _empty_result()

    # Map period to quarter
    quarter = _period_to_quarter(period_id)
    if not quarter:
        return _empty_result()

    quarter_data = config.get("quarters", {}).get(quarter, {})
    if not quarter_data:
        return _empty_result()

    # Build factors list
    factors = []

    # Insurance sector growth
    sector = quarter_data.get("insurance_sector_growth")
    if sector is not None:
        direction = "grew" if sector > 0 else "declined"
        factors.append({
            "type": "sector",
            "impact": sector,
            "label": f"Insurance sector {direction} {abs(sector):.1f}%",
        })

    # FX impacts
    fx_data = quarter_data.get("fx_impact", {})
    for pair, impact in fx_data.items():
        if impact is not None:
            currency = pair.split("_")[0].upper()
            direction = "strengthened" if impact > 0 else "weakened"
            factors.append({
                "type": "fx",
                "impact": impact,
                "currency": currency,
                "label": f"{currency} {direction} {abs(impact):.1f}%",
            })

    # External notes
    ext_notes = quarter_data.get("notes", [])

    # Build human-readable note
    note = _build_note(quarter, factors, ext_notes)

    return {
        "has_market_context": True,
        "quarter": quarter,
        "factors": factors,
        "external_notes": ext_notes,
        "note": note,
    }


def _period_to_quarter(period_id: str) -> str:
    """Convert period_id like '2026-06' to quarter like '2026-Q2'."""
    try:
        year = period_id[:4]
        month = int(period_id[5:7])
        q = (month - 1) // 3 + 1
        return f"{year}-Q{q}"
    except (ValueError, IndexError):
        return ""


def _build_note(quarter: str, factors: list[dict], notes: list[str]) -> str:
    parts = []

    # Top 2 factors
    for f in factors[:2]:
        parts.append(f["label"])

    if parts:
        note = f"Market ({quarter}): {'. '.join(parts)}."
    else:
        note = ""

    # Add first external note if available
    if notes and len(notes) > 0:
        if note:
            note += f" {notes[0]}."
        else:
            note = f"Market ({quarter}): {notes[0]}."

    return note


def _load_config(config_path: Optional[str] = None) -> dict:
    paths = [Path(config_path)] if config_path else _DEFAULT_CONFIG_PATHS
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def _empty_result() -> dict[str, Any]:
    return {
        "has_market_context": False,
        "quarter": "",
        "factors": [],
        "external_notes": [],
        "note": "",
    }
