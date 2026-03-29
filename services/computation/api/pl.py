"""P&L statement endpoints — full statement and account detail.

Prefix: /pl
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/pl", tags=["pl"])


# ---------------------------------------------------------------------------
# GET /pl/statement
# ---------------------------------------------------------------------------

@router.get("/statement")
async def get_pl_statement(
    period_id: str | None = Query(None, description="Period key"),
    view: str = Query("MTD", description="MTD | QTD | YTD"),
    comparison_base: str = Query("Budget", description="Budget | Forecast | PY"),
    bu_id: str | None = Query(None, description="Filter by business unit"),
    geo_id: str | None = Query(None, description="Filter by geography"),
    expand_level: int = Query(2, ge=1, le=5, description="Hierarchy depth to expand"),
) -> dict[str, Any]:
    """Return full P&L statement with hierarchy structure.

    The P&L follows the account hierarchy from dim_account with
    calculated rows (Gross Profit, EBITDA, EBIT, EBT, Net Income)
    resolved in dependency order AFTER rollup.

    Each row includes actual, comparison, variance ($), variance (%),
    and materiality flag. Rows are nested according to the account
    parent-child hierarchy up to the requested expand_level.
    """
    # TODO: build P&L tree from dim_account + fact_financials
    return {
        "period_id": period_id,
        "view": view,
        "comparison_base": comparison_base,
        "bu_id": bu_id,
        "rows": [],
        "calculated_rows": [],
    }


# ---------------------------------------------------------------------------
# GET /pl/account/{account_id}/detail
# ---------------------------------------------------------------------------

@router.get("/account/{account_id}/detail")
async def get_account_detail(
    account_id: str,
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
) -> dict[str, Any]:
    """Return detailed breakdown for a single P&L account.

    Includes BU-level splits, trailing period trend, variance
    decomposition summary, and any netting or trend flags.
    """
    # TODO: slice fact_financials by account, enrich with flags
    return {
        "account_id": account_id,
        "account_label": None,
        "period_id": period_id,
        "view": view,
        "comparison_base": comparison_base,
        "actual": 0.0,
        "comparison": 0.0,
        "variance_amount": 0.0,
        "variance_pct": None,
        "bu_splits": [],
        "trailing_trend": [],
        "flags": [],
    }
