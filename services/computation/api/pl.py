"""P&L statement endpoints — full statement and account detail.

Prefix: /pl
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from shared.data.service import DataService

router = APIRouter(prefix="/pl", tags=["pl"])


def _get_ds(request: Request) -> DataService:
    """Retrieve DataService from app state."""
    return request.app.state.data_service


# ---------------------------------------------------------------------------
# GET /pl/statement
# ---------------------------------------------------------------------------

@router.get("/statement")
async def get_pl_statement(
    request: Request,
    period_id: str = Query(..., description="Period key"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    view_id: str = Query("MTD", description="MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return full P&L statement with hierarchy structure.

    The P&L follows the account hierarchy from dim_account with
    calculated rows (Gross Profit, EBITDA, EBIT, EBT, Net Income)
    resolved in dependency order AFTER rollup.

    Each row includes actual, comparator, variance ($), variance (%),
    and materiality flag. Rows are nested according to the account
    parent-child hierarchy.
    """
    ds = _get_ds(request)
    rows = ds.get_pl_statement(
        period_id=period_id,
        bu_id=bu_id,
        view_id=view_id,
        base_id=base_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    return {
        "rows": rows,
        "period_id": period_id,
        "bu_id": bu_id,
        "view_id": view_id,
        "base_id": base_id,
    }


# ---------------------------------------------------------------------------
# GET /pl/account/{account_id}/detail
# ---------------------------------------------------------------------------

@router.get("/account/{account_id}/detail")
async def get_account_detail(
    request: Request,
    account_id: str,
    period_id: str = Query(..., description="Period key"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    view_id: str = Query("MTD", description="MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return detailed breakdown for a single P&L account.

    Includes BU-level splits, child account variances,
    variance decomposition summary, and any netting or trend flags.
    """
    ds = _get_ds(request)
    result = ds.get_account_detail(
        account_id=account_id,
        period_id=period_id,
        bu_id=bu_id,
        view_id=view_id,
        base_id=base_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return result
