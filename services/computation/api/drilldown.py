"""Drill-down endpoints — hierarchy traversal, decomposition, netting, correlations.

Prefix: /drilldown
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from shared.data.service import DataService

router = APIRouter(prefix="/drilldown", tags=["drilldown"])


def _get_ds(request: Request) -> DataService:
    """Retrieve DataService from app state."""
    return request.app.state.data_service


# ---------------------------------------------------------------------------
# GET /drilldown/{node_id}
# ---------------------------------------------------------------------------

@router.get("/{node_id}")
async def drill_into_node(
    request: Request,
    node_id: str,
    period_id: str = Query(..., description="Period key"),
    dimension: str = Query("account", description="Dimension: account | geo | segment | lob | costcenter"),
    view_id: str = Query("MTD", description="MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
) -> dict[str, Any]:
    """Drill into a hierarchy node and return its children with variances.

    Supports ragged hierarchies via materialized rollup_path in
    dim_hierarchy. Returns each child's contribution to the parent
    variance (absolute $ and % of parent).
    """
    ds = _get_ds(request)

    if dimension == "account":
        # Use account detail which returns child variances
        result = ds.get_account_detail(
            account_id=node_id,
            period_id=period_id,
            view_id=view_id,
            base_id=base_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return {
            "node_id": node_id,
            "node_label": result["account_name"],
            "total_variance": result["variance_amount"],
            "children": result["child_variances"],
        }

    # For geo/segment/lob/costcenter dimensions, filter variance data
    vm = ds._table("fact_variance_material")
    if vm.empty:
        return {"node_id": node_id, "node_label": None, "total_variance": 0.0, "children": []}

    # Determine the column for this dimension
    dim_col_map = {
        "geo": "geo_node_id",
        "segment": "segment_node_id",
        "lob": "lob_node_id",
        "costcenter": "costcenter_node_id",
    }
    dim_col = dim_col_map.get(dimension)
    if dim_col is None:
        raise HTTPException(status_code=400, detail=f"Unknown dimension: {dimension}")

    # Get children of this node from dim_hierarchy
    dh = ds._table("dim_hierarchy")
    if dh.empty:
        return {"node_id": node_id, "node_label": None, "total_variance": 0.0, "children": []}

    node_row = dh[dh["node_id"] == node_id]
    node_label = node_row.iloc[0]["node_name"] if not node_row.empty else node_id
    child_nodes = dh[dh["parent_id"] == node_id]

    filtered = ds._filter_variance(vm, period_id, None, view_id, base_id)

    children: list[dict[str, Any]] = []
    for _, child in child_nodes.iterrows():
        child_id = child["node_id"]
        child_rows = filtered[filtered[dim_col] == child_id]
        if child_rows.empty:
            continue
        var_amt = child_rows["variance_amount"].sum()
        children.append({
            "node_id": child_id,
            "node_name": child["node_name"],
            "variance_amount": round(float(var_amt), 2),
        })

    total_var = sum(c["variance_amount"] for c in children)
    return {
        "node_id": node_id,
        "node_label": node_label,
        "total_variance": round(total_var, 2),
        "children": children,
    }


# ---------------------------------------------------------------------------
# GET /drilldown/decomposition/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/decomposition/{variance_id}")
async def get_decomposition(
    request: Request,
    variance_id: str,
) -> dict[str, Any]:
    """Return variance decomposition detail.

    Decomposition type depends on account category:
    - Revenue: Volume x Price x Mix x FX
    - COGS: Rate x Volume x Mix
    - OpEx: Rate x Volume x Timing x Onetime

    Falls back to simpler methods when unit-level data is unavailable.
    """
    ds = _get_ds(request)
    detail = ds.get_variance_detail(variance_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Variance {variance_id} not found")

    decomposition = detail.get("decomposition")
    if decomposition is None:
        return {
            "variance_id": variance_id,
            "decomposition_type": None,
            "components": [],
            "total_explained": 0.0,
            "residual": 0.0,
        }

    return {
        "variance_id": variance_id,
        "decomposition_type": decomposition["method"],
        "components": decomposition["components"],
        "total_explained": decomposition["total_explained"],
        "residual": decomposition["residual"],
    }


# ---------------------------------------------------------------------------
# GET /drilldown/netting/{node_id}
# ---------------------------------------------------------------------------

@router.get("/netting/{node_id}")
async def get_netting_detail(
    request: Request,
    node_id: str,
    period_id: str = Query(..., description="Period key"),
) -> dict[str, Any]:
    """Return netting analysis for a hierarchy node.

    Netting detection (Pass 1.5) identifies summary nodes where
    child variances offset each other, masking material movements.
    MVP implements checks 1-4 of the 6 defined netting rules.
    """
    ds = _get_ds(request)
    netting = ds._table("fact_netting_flags")
    if netting.empty:
        return {
            "node_id": node_id,
            "is_netted": False,
            "netting_flags": [],
        }

    # Filter for this node and period
    mask = netting["node_id"] == node_id
    if "period_id" in netting.columns:
        mask &= netting["period_id"] == period_id
    node_flags = netting[mask]

    if node_flags.empty:
        return {
            "node_id": node_id,
            "is_netted": False,
            "netting_flags": [],
        }

    flags: list[dict[str, Any]] = []
    for _, row in node_flags.iterrows():
        flags.append({
            "netting_id": row.get("netting_id", ""),
            "check_type": row.get("check_type", ""),
            "is_netted": bool(row.get("is_netted", False)),
            "net_variance": DataService._safe_float(row.get("net_variance")),
            "gross_positive": DataService._safe_float(row.get("gross_positive")),
            "gross_negative": DataService._safe_float(row.get("gross_negative")),
            "netting_ratio": DataService._safe_float(row.get("netting_ratio")),
        })

    return {
        "node_id": node_id,
        "is_netted": any(f["is_netted"] for f in flags),
        "netting_flags": flags,
    }


# ---------------------------------------------------------------------------
# GET /drilldown/correlations/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/correlations/{variance_id}")
async def get_correlations(
    request: Request,
    variance_id: str,
) -> dict[str, Any]:
    """Return correlated variances and root-cause hypotheses.

    Pass 4 performs pairwise correlation scans and batched LLM
    hypothesis generation across material variances.
    """
    ds = _get_ds(request)
    detail = ds.get_variance_detail(variance_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Variance {variance_id} not found")

    return {
        "variance_id": variance_id,
        "correlations": detail.get("correlations", []),
    }
