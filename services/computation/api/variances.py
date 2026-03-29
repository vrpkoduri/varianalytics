"""Variance endpoints — list, detail, by-account.

Prefix: /variances
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from shared.data.service import DataService

router = APIRouter(prefix="/variances", tags=["variances"])


def _get_ds(request: Request) -> DataService:
    """Retrieve DataService from app state."""
    return request.app.state.data_service


# ---------------------------------------------------------------------------
# GET /variances/
# ---------------------------------------------------------------------------

@router.get("/")
async def list_material_variances(
    request: Request,
    period_id: str = Query(..., description="Period key"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    view_id: str = Query("MTD", description="MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    pl_category: str | None = Query(None, description="Revenue | COGS | OpEx"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=500, description="Items per page"),
    sort_by: str = Query("variance_amount", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
) -> dict[str, Any]:
    """Return paginated list of material variances with filter support.

    Results come from fact_variance_material (Pass 2 output) enriched
    with netting flags, trend flags, and decomposition summaries.
    """
    ds = _get_ds(request)
    return ds.get_variance_list(
        period_id=period_id,
        bu_id=bu_id,
        view_id=view_id,
        base_id=base_id,
        pl_category=pl_category,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


# ---------------------------------------------------------------------------
# GET /variances/by-account/{account_id}
# ---------------------------------------------------------------------------

@router.get("/by-account/{account_id}")
async def get_variances_by_account(
    request: Request,
    account_id: str,
    period_id: str = Query(..., description="Period key"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    view_id: str = Query("MTD", description="MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
) -> dict[str, Any]:
    """Return account summary with child variances and decomposition.

    Useful for account-centric analysis (e.g., all Revenue variances).
    """
    ds = _get_ds(request)
    result = ds.get_account_detail(
        account_id=account_id,
        period_id=period_id,
        bu_id=bu_id,
        view_id=view_id,
        base_id=base_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return result


# ---------------------------------------------------------------------------
# GET /variances/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/{variance_id}")
async def get_variance_detail(
    request: Request,
    variance_id: str,
) -> dict[str, Any]:
    """Return full detail for a single material variance.

    Includes: raw numbers, decomposition, netting context,
    trend flags, correlation links, and multi-level narratives
    (detail / midlevel / summary / oneliner).
    """
    ds = _get_ds(request)
    result = ds.get_variance_detail(variance_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Variance {variance_id} not found")
    return result
