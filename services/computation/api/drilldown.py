"""Drill-down endpoints — hierarchy traversal, decomposition, netting, correlations.

Prefix: /drilldown
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/drilldown", tags=["drilldown"])


# ---------------------------------------------------------------------------
# GET /drilldown/{node_id}
# ---------------------------------------------------------------------------

@router.get("/{node_id}")
async def drill_into_node(
    node_id: str,
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
) -> dict[str, Any]:
    """Drill into a hierarchy node and return its children with variances.

    Supports ragged hierarchies via materialized rollup_path in
    dim_hierarchy. Returns each child's contribution to the parent
    variance (absolute $ and % of parent).
    """
    # TODO: traverse dim_hierarchy, aggregate fact_variance_material
    return {
        "node_id": node_id,
        "node_label": None,
        "level": None,
        "total_variance": 0.0,
        "children": [],
    }


# ---------------------------------------------------------------------------
# GET /drilldown/decomposition/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/decomposition/{variance_id}")
async def get_decomposition(variance_id: str) -> dict[str, Any]:
    """Return variance decomposition detail.

    Decomposition type depends on account category:
    - Revenue: Volume x Price x Mix x FX
    - COGS: Rate x Volume x Mix
    - OpEx: Rate x Volume x Timing x Onetime

    Falls back to simpler methods when unit-level data is unavailable.
    """
    # TODO: query fact_decomposition
    return {
        "variance_id": variance_id,
        "decomposition_type": None,
        "components": [],
        "fallback_used": False,
        "total_explained": 0.0,
        "residual": 0.0,
    }


# ---------------------------------------------------------------------------
# GET /drilldown/netting/{node_id}
# ---------------------------------------------------------------------------

@router.get("/netting/{node_id}")
async def get_netting_detail(
    node_id: str,
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
) -> dict[str, Any]:
    """Return netting analysis for a hierarchy node.

    Netting detection (Pass 1.5) identifies summary nodes where
    child variances offset each other, masking material movements.
    MVP implements checks 1-4 of the 6 defined netting rules.
    """
    # TODO: query fact_netting_flags for node
    return {
        "node_id": node_id,
        "is_netted": False,
        "net_variance": 0.0,
        "gross_positive": 0.0,
        "gross_negative": 0.0,
        "netting_ratio": None,
        "children_detail": [],
    }


# ---------------------------------------------------------------------------
# GET /drilldown/correlations/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/correlations/{variance_id}")
async def get_correlations(variance_id: str) -> dict[str, Any]:
    """Return correlated variances and root-cause hypotheses.

    Pass 4 performs pairwise correlation scans and batched LLM
    hypothesis generation across material variances.
    """
    # TODO: query fact_correlations
    return {
        "variance_id": variance_id,
        "correlated_variances": [],
        "hypotheses": [],
    }
