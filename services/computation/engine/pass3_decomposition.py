"""Pass 3 — Variance Decomposition.

Breaks down each material variance into driver components based on
the account's P&L category:

- Revenue:  Volume x Price x Mix x FX  (decomposition/revenue.py)
- COGS:     Rate x Volume x Mix        (decomposition/cogs.py)
- OpEx:     Rate x Volume x Timing x Onetime (decomposition/opex.py)

Calculated rows (EBITDA, Gross Profit, etc.), NonOp, and Tax categories
are skipped — they derive from their children.

Optionally joins to fact_financials to retrieve FX rate data for revenue
decomposition.

Output: populates context["decomposition"] as a DataFrame matching
the fact_decomposition schema.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from services.computation.decomposition.cogs import decompose_cogs
from services.computation.decomposition.opex import decompose_opex
from services.computation.decomposition.revenue import decompose_revenue
from shared.data.loader import DataLoader

logger = logging.getLogger(__name__)

# P&L categories eligible for decomposition.
_DECOMPOSABLE_CATEGORIES = {"Revenue", "COGS", "OpEx"}

# Columns used to join material variances back to fact_financials.
_FF_JOIN_COLS = [
    "period_id",
    "bu_id",
    "account_id",
    "geo_node_id",
    "segment_node_id",
    "lob_node_id",
    "costcenter_node_id",
]


async def decompose_variances(context: dict[str, Any]) -> None:
    """Decompose material variances into driver components.

    For each row in ``context["material_variances"]``:
    - Routes to the correct decomposition function by ``pl_category``.
    - Skips calculated rows and non-decomposable categories.
    - Optionally enriches revenue rows with FX data from fact_financials.

    Stores the result DataFrame in ``context["decomposition"]`` with columns:
    variance_id, method, components (JSON string), total_explained, residual,
    created_at.

    Args:
        context: Pipeline context dict. Must contain ``material_variances``
                 (DataFrame from Pass 2).
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 3: No material variances — skipping decomposition")
        context["decomposition"] = pd.DataFrame()
        return

    # ------------------------------------------------------------------
    # Optionally load fact_financials for FX enrichment
    # ------------------------------------------------------------------
    ff_lookup = _build_ff_lookup(context)

    # ------------------------------------------------------------------
    # Decompose each material variance
    # ------------------------------------------------------------------
    results: list[dict[str, Any]] = []
    skipped = 0

    for _, var_row in material.iterrows():
        row = var_row.to_dict()

        # Skip calculated rows
        if row.get("is_calculated"):
            skipped += 1
            continue

        pl_cat = row.get("pl_category")
        if pl_cat not in _DECOMPOSABLE_CATEGORIES:
            skipped += 1
            continue

        # Look up the matching fact_financials row (for FX data)
        ff_row = _lookup_ff_row(row, ff_lookup)

        # Route to the correct decomposition function
        if pl_cat == "Revenue":
            components = decompose_revenue(row, ff_row)
        elif pl_cat == "COGS":
            components = decompose_cogs(row, ff_row)
        elif pl_cat == "OpEx":
            components = decompose_opex(row, ff_row)
        else:
            # Defensive: should not reach here after the check above
            skipped += 1
            continue

        method = components.pop("method")
        is_fallback = components.pop("is_fallback")
        residual = components.pop("residual")
        # Remove any extra metadata keys before computing total_explained
        components.pop("fx_computed", None)

        total_explained = sum(components.values())

        results.append(
            {
                "variance_id": row["variance_id"],
                "method": method,
                "components": json.dumps(components),
                "total_explained": round(total_explained, 2),
                "residual": round(residual, 2),
                "is_fallback": is_fallback,
                "created_at": datetime.now(timezone.utc),
            }
        )

    decomp_df = pd.DataFrame(results) if results else pd.DataFrame()
    context["decomposition"] = decomp_df

    logger.info(
        "Pass 3: Decomposed %d variances (skipped %d — calculated/NonOp/Tax)",
        len(results),
        skipped,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_ff_lookup(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a lookup dict from fact_financials keyed by dimension tuple.

    Attempts to load fact_financials from the DataLoader. Returns an empty
    dict if the table is not available (graceful degradation).
    """
    try:
        loader = DataLoader()
        if not loader.table_exists("fact_financials"):
            logger.debug("Pass 3: fact_financials not found — FX enrichment skipped")
            return {}

        ff = loader.load_table("fact_financials")

        # Filter to the current period for efficiency
        period_id = context.get("period_id")
        if period_id and "period_id" in ff.columns:
            ff = ff[ff["period_id"] == period_id]

        # Build lookup keyed by dimension tuple
        lookup: dict[str, dict[str, Any]] = {}
        for _, ff_row in ff.iterrows():
            key = _make_join_key(ff_row.to_dict())
            lookup[key] = ff_row.to_dict()

        logger.debug("Pass 3: Loaded %d fact_financials rows for FX lookup", len(lookup))
        return lookup

    except Exception:
        logger.debug("Pass 3: Could not load fact_financials — FX enrichment skipped", exc_info=True)
        return {}


def _make_join_key(row: dict[str, Any]) -> str:
    """Create a pipe-delimited key from the join columns."""
    return "|".join(str(row.get(col, "")) for col in _FF_JOIN_COLS)


def _lookup_ff_row(
    var_row: dict[str, Any],
    ff_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Look up the fact_financials row matching a material variance."""
    if not ff_lookup:
        return None
    key = _make_join_key(var_row)
    return ff_lookup.get(key)
