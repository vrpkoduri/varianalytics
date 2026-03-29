"""Variance endpoints — list, detail, by-account, by-BU.

Prefix: /variances
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/variances", tags=["variances"])


# ---------------------------------------------------------------------------
# GET /variances/
# ---------------------------------------------------------------------------

@router.get("/")
async def list_material_variances(
    period_id: str | None = Query(None, description="Period key"),
    view: str = Query("MTD", description="MTD | QTD | YTD"),
    comparison_base: str = Query("Budget", description="Budget | Forecast | PY"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    account_id: str | None = Query(None, description="Filter by account"),
    geo_id: str | None = Query(None, description="Filter by geography"),
    segment_id: str | None = Query(None, description="Filter by segment"),
    min_amount: float | None = Query(None, description="Minimum absolute variance $"),
    sort_by: str = Query("variance_amount", description="Sort field"),
    sort_dir: str = Query("desc", description="asc | desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Return paginated list of material variances with filter support.

    Results come from fact_variance_material (Pass 2 output) enriched
    with netting flags, trend flags, and decomposition summaries.
    """
    # TODO: query fact_variance_material with filters
    return {
        "total": 0,
        "limit": limit,
        "offset": offset,
        "items": [],
    }


# ---------------------------------------------------------------------------
# GET /variances/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/{variance_id}")
async def get_variance_detail(variance_id: str) -> dict[str, Any]:
    """Return full detail for a single material variance.

    Includes: raw numbers, decomposition, netting context,
    trend flags, correlation links, and multi-level narratives
    (detail / midlevel / summary / oneliner).
    """
    # TODO: join fact_variance_material + fact_decomposition + narratives
    return {
        "variance_id": variance_id,
        "account": None,
        "business_unit": None,
        "period": None,
        "actual": 0.0,
        "comparison": 0.0,
        "variance_amount": 0.0,
        "variance_pct": None,
        "decomposition": None,
        "netting_flag": None,
        "trend_flag": None,
        "correlations": [],
        "narratives": {
            "detail": None,
            "midlevel": None,
            "summary": None,
            "oneliner": None,
        },
        "review_status": None,
    }


# ---------------------------------------------------------------------------
# GET /variances/by-account/{account_id}
# ---------------------------------------------------------------------------

@router.get("/by-account/{account_id}")
async def get_variances_by_account(
    account_id: str,
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
) -> dict[str, Any]:
    """Return all material variances for a given account across BUs/geos.

    Useful for account-centric analysis (e.g., all Revenue variances).
    """
    # TODO: filter fact_variance_material by account_id
    return {
        "account_id": account_id,
        "view": view,
        "comparison_base": comparison_base,
        "items": [],
    }


# ---------------------------------------------------------------------------
# GET /variances/by-bu/{bu_id}
# ---------------------------------------------------------------------------

@router.get("/by-bu/{bu_id}")
async def get_variances_by_bu(
    bu_id: str,
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
) -> dict[str, Any]:
    """Return all material variances for a given business unit.

    Useful for BU-leader dashboards showing their variance portfolio.
    """
    # TODO: filter fact_variance_material by bu_id
    return {
        "bu_id": bu_id,
        "view": view,
        "comparison_base": comparison_base,
        "items": [],
    }
