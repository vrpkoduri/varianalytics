"""Dashboard endpoints — summary cards, waterfall, heatmap, trends.

Prefix: /dashboard
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# GET /dashboard/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def get_summary_cards(
    period_id: str | None = Query(None, description="Period key (e.g. '2026-03')"),
    view: str = Query("MTD", description="Aggregation view: MTD | QTD | YTD"),
    comparison_base: str = Query("Budget", description="Budget | Forecast | PY"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
) -> dict[str, Any]:
    """Return summary KPI cards: Revenue, EBITDA, Total Costs, etc.

    Each card contains actual, comparison, variance ($), variance (%),
    and a materiality flag.
    """
    # TODO: compute from fact_financials + fact_variance_material
    return {
        "period_id": period_id,
        "view": view,
        "comparison_base": comparison_base,
        "cards": [
            {
                "metric": "Revenue",
                "actual": 0.0,
                "comparison": 0.0,
                "variance_amount": 0.0,
                "variance_pct": None,
                "is_material": False,
            },
            {
                "metric": "EBITDA",
                "actual": 0.0,
                "comparison": 0.0,
                "variance_amount": 0.0,
                "variance_pct": None,
                "is_material": False,
            },
        ],
    }


# ---------------------------------------------------------------------------
# GET /dashboard/waterfall
# ---------------------------------------------------------------------------

@router.get("/waterfall")
async def get_waterfall_data(
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
    bu_id: str | None = Query(None),
) -> dict[str, Any]:
    """Return waterfall chart data bridging comparison to actual.

    Each step has a label, delta value, running total, and color hint
    (positive / negative / subtotal).
    """
    # TODO: build bridge from comparison → actual via account hierarchy
    return {
        "period_id": period_id,
        "view": view,
        "comparison_base": comparison_base,
        "steps": [],
    }


# ---------------------------------------------------------------------------
# GET /dashboard/heatmap
# ---------------------------------------------------------------------------

@router.get("/heatmap")
async def get_heatmap_data(
    period_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
    dimension: str = Query("account", description="Heatmap dimension: account | geo | segment"),
) -> dict[str, Any]:
    """Return variance heatmap: rows × columns with color-coded variance %.

    Rows = dimension members (accounts, geos, etc.).
    Columns = periods (trailing 6 or 12 months).
    """
    # TODO: pivot fact_variance_material into heatmap grid
    return {
        "dimension": dimension,
        "view": view,
        "comparison_base": comparison_base,
        "rows": [],
        "columns": [],
        "cells": [],
    }


# ---------------------------------------------------------------------------
# GET /dashboard/trends
# ---------------------------------------------------------------------------

@router.get("/trends")
async def get_trend_data(
    account_id: str | None = Query(None, description="Specific account to trend"),
    bu_id: str | None = Query(None),
    view: str = Query("MTD"),
    comparison_base: str = Query("Budget"),
    periods: int = Query(12, ge=3, le=36, description="Number of trailing periods"),
) -> dict[str, Any]:
    """Return time-series trend data for sparklines and trend charts.

    Each series contains period labels and values for actual,
    comparison, and variance.
    """
    # TODO: query fact_financials over trailing periods
    return {
        "account_id": account_id,
        "bu_id": bu_id,
        "view": view,
        "comparison_base": comparison_base,
        "periods": periods,
        "series": [],
    }
