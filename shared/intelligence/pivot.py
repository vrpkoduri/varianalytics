"""Cross-Dimensional Pivot — identifies where variance is concentrated.

Analyzes variance distribution across geography, segment, LOB, and
cost center to find if one dimension value dominates.

Example output:
    "85% concentrated in EMEA geography — not a cost center issue."
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

# Dimensions to check for concentration
_DIMENSION_COLUMNS = [
    ("geo_node_id", "geography"),
    ("segment_node_id", "segment"),
    ("lob_node_id", "line of business"),
    ("costcenter_node_id", "cost center"),
]

# Threshold for a single dimension value to be considered "dominant"
_DOMINANT_THRESHOLD = 0.60  # 60%


def compute_dimensional_pivot(
    variance_id: str,
    material_variances: pd.DataFrame,
    account_id: str,
) -> dict[str, Any]:
    """Analyze variance concentration across dimensions.

    Args:
        variance_id: Current variance ID.
        material_variances: All material variances for the period.
        account_id: Account to analyze.

    Returns:
        Dict with dominant_dimension, concentration_pct, distribution, note.
    """
    if material_variances.empty:
        return _empty_result()

    # Filter to same account (all BUs/dimensions)
    acct_rows = material_variances[material_variances["account_id"] == account_id]
    if acct_rows.empty or len(acct_rows) < 2:
        return _empty_result()

    total_abs = acct_rows["variance_amount"].abs().sum()
    if total_abs == 0:
        return _empty_result()

    # Check each dimension for concentration
    best_dim = None
    best_node = None
    best_pct = 0.0
    best_distribution: dict[str, float] = {}
    best_dim_label = ""

    for col, label in _DIMENSION_COLUMNS:
        if col not in acct_rows.columns:
            continue

        grouped = acct_rows.groupby(col)["variance_amount"].apply(lambda x: x.abs().sum())
        if grouped.empty:
            continue

        distribution = (grouped / total_abs).to_dict()
        top_node = grouped.idxmax()
        top_pct = grouped.max() / total_abs

        if top_pct > best_pct:
            best_pct = float(top_pct)
            best_dim = col
            best_node = str(top_node)
            best_distribution = {str(k): round(float(v), 3) for k, v in distribution.items()}
            best_dim_label = label

    if best_dim is None or best_pct < _DOMINANT_THRESHOLD:
        return {
            "dominant_dimension": None,
            "dominant_node": None,
            "concentration_pct": round(best_pct, 3) if best_pct else 0.0,
            "distribution": best_distribution,
            "note": "",
        }

    # Identify what it's NOT concentrated in
    other_dims = [label for col, label in _DIMENSION_COLUMNS if col != best_dim and col in acct_rows.columns]
    not_clause = f" — not a {other_dims[0]} issue" if other_dims else ""

    note = f"{best_pct:.0%} concentrated in {best_node} {best_dim_label}{not_clause}."

    return {
        "dominant_dimension": best_dim_label,
        "dominant_node": best_node,
        "concentration_pct": round(best_pct, 3),
        "distribution": best_distribution,
        "note": note,
    }


def _empty_result() -> dict[str, Any]:
    return {
        "dominant_dimension": None,
        "dominant_node": None,
        "concentration_pct": 0.0,
        "distribution": {},
        "note": "",
    }
