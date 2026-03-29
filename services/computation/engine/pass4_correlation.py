"""Pass 4 — Correlation & Root Cause Analysis.

Performs pairwise correlation scans across material variances to
identify potential causal relationships. For Sprint 0 the LLM
hypothesis step is deferred — hypothesis and confidence are set to None.

Scoring formula (combined score for each pair):
    0.4 * dimension_overlap  +  0.3 * direction_match  +  0.3 * magnitude_similarity

Filters:
- Only MTD / BUDGET rows are considered.
- Pairs must score >= 0.3.
- Top 20 pairs kept (sorted descending by score).

Output: populates context["correlations"] as a DataFrame matching
the fact_correlations schema.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd

logger = logging.getLogger(__name__)

# Scoring weights
_W_OVERLAP = 0.4
_W_DIRECTION = 0.3
_W_MAGNITUDE = 0.3

# Thresholds
_MIN_SCORE = 0.3
_MAX_PAIRS = 20

# Dimension columns used for overlap scoring
_DIM_COLS = [
    "bu_id",
    "costcenter_node_id",
    "geo_node_id",
    "segment_node_id",
    "lob_node_id",
    "account_id",
]


async def find_correlations(context: dict[str, Any]) -> None:
    """Scan material variances for pairwise correlations.

    Takes material variances filtered to MTD + BUDGET. For each unique
    pair (i, j) where i < j, computes a combined score from:

    1. **Dimension overlap** — fraction of shared dimension values (0-1).
    2. **Direction match** — 1.0 if both positive or both negative, else 0.0.
    3. **Magnitude similarity** — ``1 - abs(log(abs(a)/abs(b)))`` clamped to [0, 1].

    Keeps top 20 pairs above the minimum score threshold.

    LLM hypothesis generation is deferred to Sprint 3.

    Args:
        context: Pipeline context dict. Must contain ``material_variances``.
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 4: No material variances — skipping correlation scan")
        context["correlations"] = pd.DataFrame()
        return

    # ------------------------------------------------------------------
    # Filter to MTD / BUDGET only
    # ------------------------------------------------------------------
    mask = (material["view_id"] == "MTD") & (material["base_id"] == "BUDGET")
    mtd_budget = material[mask].copy()

    if len(mtd_budget) < 2:
        logger.info("Pass 4: Fewer than 2 MTD/BUDGET variances — no pairs to scan")
        context["correlations"] = pd.DataFrame()
        return

    logger.info("Pass 4: Scanning %d MTD/BUDGET variances for correlations", len(mtd_budget))

    # Convert to list of dicts for pairwise iteration
    rows = mtd_budget.to_dict("records")
    n = len(rows)

    scored_pairs: list[dict[str, Any]] = []

    for i in range(n):
        for j in range(i + 1, n):
            row_a = rows[i]
            row_b = rows[j]

            overlap_score, shared_dims = _dimension_overlap(row_a, row_b)
            direction_score = _direction_match(row_a, row_b)
            magnitude_score = _magnitude_similarity(row_a, row_b)

            combined = (
                _W_OVERLAP * overlap_score
                + _W_DIRECTION * direction_score
                + _W_MAGNITUDE * magnitude_score
            )

            if combined >= _MIN_SCORE:
                scored_pairs.append(
                    {
                        "correlation_id": str(uuid4()),
                        "variance_id_a": row_a["variance_id"],
                        "variance_id_b": row_b["variance_id"],
                        "correlation_score": round(combined, 4),
                        "dimension_overlap": shared_dims,
                        "directional_match": direction_score == 1.0,
                        "hypothesis": None,  # Deferred to Sprint 3 (LLM)
                        "confidence": None,   # Deferred to Sprint 3 (LLM)
                        "created_at": datetime.now(timezone.utc),
                    }
                )

    # ------------------------------------------------------------------
    # Keep top N pairs by score
    # ------------------------------------------------------------------
    scored_pairs.sort(key=lambda p: p["correlation_score"], reverse=True)
    top_pairs = scored_pairs[:_MAX_PAIRS]

    corr_df = pd.DataFrame(top_pairs) if top_pairs else pd.DataFrame()
    context["correlations"] = corr_df

    logger.info(
        "Pass 4: Found %d candidate pairs, kept top %d (min_score=%.2f)",
        len(scored_pairs),
        len(top_pairs),
        _MIN_SCORE,
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _dimension_overlap(
    row_a: dict[str, Any],
    row_b: dict[str, Any],
) -> tuple[float, list[str]]:
    """Compute dimension overlap score and list of shared dimension values.

    Returns:
        Tuple of (overlap_score 0-1, list of shared dimension column names).
    """
    shared: list[str] = []
    for col in _DIM_COLS:
        val_a = row_a.get(col)
        val_b = row_b.get(col)
        if val_a is not None and val_b is not None and val_a == val_b:
            shared.append(col)

    total = len(_DIM_COLS)
    score = len(shared) / total if total > 0 else 0.0
    return score, shared


def _direction_match(row_a: dict[str, Any], row_b: dict[str, Any]) -> float:
    """Return 1.0 if both variances have the same sign, 0.0 otherwise."""
    va = row_a.get("variance_amount", 0.0)
    vb = row_b.get("variance_amount", 0.0)

    if va == 0.0 or vb == 0.0:
        return 0.0

    same_sign = (va > 0 and vb > 0) or (va < 0 and vb < 0)
    return 1.0 if same_sign else 0.0


def _magnitude_similarity(row_a: dict[str, Any], row_b: dict[str, Any]) -> float:
    """Compute magnitude similarity: 1 - abs(log(abs(a)/abs(b))), clamped to [0, 1].

    When one value is zero, returns 0.0 (no similarity).
    """
    va = abs(row_a.get("variance_amount", 0.0))
    vb = abs(row_b.get("variance_amount", 0.0))

    if va == 0.0 or vb == 0.0:
        return 0.0

    try:
        log_ratio = abs(math.log(va / vb))
    except (ValueError, ZeroDivisionError):
        return 0.0

    # Clamp to [0, 1]
    return max(0.0, min(1.0, 1.0 - log_ratio))
