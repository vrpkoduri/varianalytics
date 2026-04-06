"""Dashboard endpoints — summary cards, waterfall, heatmap, trends.

Prefix: /dashboard
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query, Request

from shared.data.service import DataService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _get_ds(request: Request) -> DataService:
    """Retrieve DataService from app state."""
    return request.app.state.data_service


# ---------------------------------------------------------------------------
# GET /dashboard/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def get_summary_cards(
    request: Request,
    period_id: str = Query(..., description="Period key (e.g. '2026-03')"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
    view_id: str = Query("MTD", description="Aggregation view: MTD | QTD | YTD"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return summary KPI cards: Revenue, EBITDA, Total Costs, etc.

    Each card contains actual, comparator, variance ($), variance (%),
    and a materiality flag.
    """
    ds = _get_ds(request)
    cards = ds.get_summary_cards(
        period_id=period_id,
        bu_id=bu_id,
        view_id=view_id,
        base_id=base_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    metrics = ds.get_success_metrics(
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
        "cards": cards,
        "period_id": period_id,
        "view_id": view_id,
        "base_id": base_id,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/waterfall
# ---------------------------------------------------------------------------

@router.get("/waterfall")
async def get_waterfall_data(
    request: Request,
    period_id: str = Query(..., description="Period key"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    view_id: str = Query("MTD", description="View: MTD, QTD, YTD"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return waterfall chart data bridging comparison to actual.

    Each step has a label, delta value, running total, and color hint
    (positive / negative / subtotal).
    """
    ds = _get_ds(request)
    steps = ds.get_waterfall(
        period_id=period_id,
        bu_id=bu_id,
        base_id=base_id,
        view_id=view_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    return {
        "steps": steps,
        "period_id": period_id,
        "base_id": base_id,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/heatmap
# ---------------------------------------------------------------------------

@router.get("/heatmap")
async def get_heatmap_data(
    request: Request,
    period_id: str = Query(..., description="Period key"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    view_id: str = Query("MTD", description="View: MTD, QTD, YTD"),
    bu_id: str | None = Query(None, description="Business unit filter"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return variance heatmap: geo rows x BU columns with color-coded variance %.
    """
    ds = _get_ds(request)
    return ds.get_heatmap(
        period_id=period_id,
        base_id=base_id,
        view_id=view_id,
        bu_id=bu_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/trends
# ---------------------------------------------------------------------------

@router.get("/trends")
async def get_trend_data(
    request: Request,
    period_id: str | None = Query(None, description="Anchor period — trailing window ends here"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
    account_id: str = Query("acct_gross_revenue", description="Account to trend"),
    base_id: str = Query("BUDGET", description="BUDGET | FORECAST | PY"),
    periods: int = Query(12, ge=3, le=36, description="Number of trailing periods"),
    view_id: str = Query("MTD", description="View: MTD, QTD, YTD"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return time-series trend data for sparklines and trend charts.

    Each series contains period labels and values for actual,
    comparator, and variance.
    """
    ds = _get_ds(request)
    data = ds.get_trends(
        period_id=period_id,
        bu_id=bu_id,
        account_id=account_id,
        base_id=base_id,
        periods=periods,
        view_id=view_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    return {
        "data": data,
        "account_id": account_id,
        "periods": periods,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/alerts/netting
# ---------------------------------------------------------------------------

@router.get("/alerts/netting")
async def get_netting_alerts(
    request: Request,
    period_id: str = Query(..., description="Period to filter"),
    bu_id: str | None = Query(None, description="Business unit filter"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Get top netting alerts for the dashboard."""
    ds = _get_ds(request)
    alerts = ds.get_netting_alerts(
        period_id=period_id,
        bu_id=bu_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    return {"alerts": alerts, "count": len(alerts)}


# ---------------------------------------------------------------------------
# GET /dashboard/alerts/trends
# ---------------------------------------------------------------------------

@router.get("/alerts/trends")
async def get_trend_alerts(
    request: Request,
    period_id: str | None = Query(None, description="Period filter"),
    bu_id: str | None = Query(None, description="Business unit filter"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Get top trend alerts for the dashboard."""
    ds = _get_ds(request)
    alerts = ds.get_trend_alerts(
        period_id=period_id,
        bu_id=bu_id,
        geo_node_id=geo_node_id,
        segment_node_id=segment_node_id,
        lob_node_id=lob_node_id,
        costcenter_node_id=costcenter_node_id,
    )
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/section-narratives")
async def get_section_narratives(
    request: Request,
    period_id: str = Query(..., description="Period"),
    base_id: str = Query("BUDGET"),
    view_id: str = Query("MTD"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return P&L section narratives (Revenue, COGS, OpEx, Non-Op, Profitability)."""
    ds = _get_ds(request)
    sections = ds.get_section_narratives(period_id=period_id, base_id=base_id, view_id=view_id, bu_id=bu_id)
    return {"sections": sections, "count": len(sections)}


@router.get("/executive-summary")
async def get_executive_summary(
    request: Request,
    period_id: str = Query(..., description="Period"),
    base_id: str = Query("BUDGET"),
    view_id: str = Query("MTD"),
    bu_id: str | None = Query(None, description="Filter to a single business unit"),
    geo_node_id: Optional[str] = Query(None, description="Geography hierarchy node ID"),
    segment_node_id: Optional[str] = Query(None, description="Segment hierarchy node ID"),
    lob_node_id: Optional[str] = Query(None, description="LOB hierarchy node ID"),
    costcenter_node_id: Optional[str] = Query(None, description="Cost Center hierarchy node ID"),
) -> dict[str, Any]:
    """Return the CFO-level executive summary with headline, narrative, and risks."""
    ds = _get_ds(request)
    summary = ds.get_executive_summary(period_id=period_id, base_id=base_id, view_id=view_id, bu_id=bu_id)
    return summary or {"headline": None, "full_narrative": None, "key_risks": []}
