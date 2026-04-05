"""Budget Assumptions — compares actual performance vs budgeted assumptions.

Loads budget growth/FX assumptions from YAML config and identifies
gaps between what was budgeted and what actually happened.

Example output:
    "Budget assumed 8.0% revenue growth; actual 3.0% — 5.0pp shortfall."
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml


_DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent / "config" / "budget_assumptions.yaml",
    Path("shared/config/budget_assumptions.yaml"),
]


def compute_budget_gap(
    actual_pct: float,
    period_id: str,
    pl_category: str,
    config_path: Optional[str] = None,
) -> dict[str, Any]:
    """Compare actual variance % against budgeted assumptions.

    Args:
        actual_pct: Actual variance percentage (e.g. 3.0 for 3%).
        period_id: Period ID (e.g. "2026-06") to determine fiscal year.
        pl_category: P&L category (Revenue, COGS, OpEx).
        config_path: Override config file path.

    Returns:
        Dict with assumed_growth, actual, gap, and note.
    """
    config = _load_config(config_path)
    if not config:
        return _empty_result()

    # Extract fiscal year from period_id
    fiscal_year = period_id[:4] if len(period_id) >= 4 else ""
    assumptions = config.get("assumptions", {}).get(fiscal_year, {})
    if not assumptions:
        return _empty_result()

    # Find the relevant assumption for this P&L category
    category_map = config.get("category_mapping", {})
    assumption_key = category_map.get(pl_category)
    if not assumption_key or assumption_key not in assumptions:
        return _empty_result()

    assumed_value = float(assumptions[assumption_key])

    # Compute gap
    gap = actual_pct - assumed_value

    note = _build_note(pl_category, assumed_value, actual_pct, gap, assumption_key)

    return {
        "assumed_growth": assumed_value,
        "actual_growth": round(actual_pct, 2),
        "gap_pp": round(gap, 2),
        "assumption_key": assumption_key,
        "fiscal_year": fiscal_year,
        "note": note,
    }


def _build_note(
    category: str, assumed: float, actual: float, gap: float, key: str
) -> str:
    if abs(gap) < 0.5:
        return ""  # Within tolerance, no note needed

    label = key.replace("_pct", "").replace("_", " ")

    if gap < 0:
        return (
            f"Budget assumed {assumed:.1f}% {label}; actual {actual:.1f}% "
            f"— {abs(gap):.1f}pp shortfall."
        )
    else:
        return (
            f"Budget assumed {assumed:.1f}% {label}; actual {actual:.1f}% "
            f"— {gap:.1f}pp above plan."
        )


def _load_config(config_path: Optional[str] = None) -> dict:
    paths = [Path(config_path)] if config_path else _DEFAULT_CONFIG_PATHS
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def _empty_result() -> dict[str, Any]:
    return {
        "assumed_growth": None,
        "actual_growth": None,
        "gap_pp": 0.0,
        "assumption_key": None,
        "fiscal_year": None,
        "note": "",
    }
