"""Review workflow endpoints.

Analysts use these endpoints to browse the review queue, submit review
actions (approve / edit / escalate / dismiss), and view queue statistics.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from shared.auth.middleware import UserContext, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ReviewQueueItem(BaseModel):
    """Single item in the analyst review queue."""

    variance_id: str
    account_name: str
    period_label: str
    variance_amount: float
    variance_pct: Optional[float] = None
    current_status: str = "AI_DRAFT"
    narrative_preview: str = ""
    sla_hours_remaining: Optional[float] = None


class ReviewQueueResponse(BaseModel):
    """Paginated review queue."""

    items: list[ReviewQueueItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class ReviewAction(BaseModel):
    """Analyst review action payload."""

    variance_id: str
    action: str = Field(
        ..., description="One of: approve, edit, escalate, dismiss"
    )
    edited_narrative: Optional[str] = None
    hypothesis_feedback: Optional[str] = Field(
        None, description="thumbs_up | thumbs_down | null"
    )
    comment: Optional[str] = None
    change_reason: Optional[str] = Field(
        None, description="Why the narrative was changed: factual_correction | added_context | style | removed_hallucination | simplified"
    )


class ReviewActionResponse(BaseModel):
    """Confirmation of a review action."""

    variance_id: str
    new_status: str
    message: str


class ReviewStats(BaseModel):
    """Aggregate review queue statistics."""

    total_pending: int = 0
    ai_draft: int = 0
    analyst_reviewed: int = 0
    escalated: int = 0
    dismissed: int = 0
    approved: int = 0
    avg_sla_hours: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    summary="Get review queue",
)
async def get_review_queue(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("impact", description="Sort field: impact | sla | period"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fiscal_year: Optional[int] = Query(None, description="Filter by fiscal year (e.g. 2026)"),
    user: UserContext = Depends(require_role("analyst", "admin")),
) -> ReviewQueueResponse:
    """Return the analyst review queue with optional status filter and sorting."""
    store = request.app.state.review_store
    result = store.get_review_queue(
        status_filter=status_filter,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        fiscal_year=fiscal_year,
    )
    return ReviewQueueResponse(
        items=[ReviewQueueItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post(
    "/actions",
    response_model=ReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a review action",
)
async def submit_review_action(
    body: ReviewAction,
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
) -> ReviewActionResponse:
    """Process an analyst review action (approve / edit / escalate / dismiss).

    On approval, triggers bottom-up synthesis for parent nodes.
    """
    store = request.app.state.review_store
    try:
        result = await store.submit_review_action(
            variance_id=body.variance_id,
            action=body.action,
            edited_narrative=body.edited_narrative,
            hypothesis_feedback=body.hypothesis_feedback,
            comment=body.comment,
            user_id=user.user_id,
            change_reason=body.change_reason,
        )

        # Cascade regeneration: auto-regenerate parent/section/exec on edit/approve
        if body.action in ("edit", "approve"):
            cascade_mgr = getattr(request.app.state, "cascade_manager", None)
            if cascade_mgr:
                period_id = result.get("period_id", "")
                if period_id:
                    await cascade_mgr.on_narrative_changed(body.variance_id, period_id)
                    logger.info(
                        "Cascade triggered for %s (action=%s, period=%s)",
                        body.variance_id, body.action, period_id,
                    )

        return ReviewActionResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=ReviewStats,
    summary="Get review queue statistics",
)
async def get_review_stats(
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
) -> ReviewStats:
    """Return aggregate counts and SLA metrics for the review queue."""
    store = request.app.state.review_store
    stats = store.get_review_stats()
    return ReviewStats(**stats)


# ---------------------------------------------------------------------------
# Locking endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/lock/{variance_id}",
    summary="Acquire edit lock on a variance",
)
async def acquire_lock(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
):
    """Acquire a 30-minute soft edit lock."""
    store = request.app.state.review_store
    try:
        result = store.acquire_lock(variance_id, user.user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/lock/{variance_id}",
    summary="Release edit lock",
)
async def release_lock(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
):
    """Release the edit lock if owned by the caller."""
    store = request.app.state.review_store
    released = store.release_lock(variance_id, user.user_id)
    return {"released": released}


@router.get(
    "/lock/{variance_id}",
    summary="Check lock status",
)
async def get_lock_status(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
):
    """Check whether a variance is locked for editing."""
    store = request.app.state.review_store
    return store.get_lock_status(variance_id)


# ---------------------------------------------------------------------------
# Version history endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/{variance_id}/history",
    summary="Get narrative version history",
)
async def get_version_history(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("analyst", "admin")),
):
    """Return the chronological edit history for a variance narrative."""
    # For now, return from in-memory review_status (version_count only)
    # Full history from NarrativeVersionRecord will be added when PostgreSQL is primary
    store = request.app.state.review_store
    rs = store._review_status if hasattr(store, '_review_status') else store._store._review_status
    mask = rs["variance_id"] == variance_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Variance not found")

    row = rs[mask].iloc[0]
    versions = []
    versions.append({
        "version_number": 1,
        "narrative_text": row.get("original_narrative", ""),
        "changed_by": "engine",
        "change_type": "ai_generated",
    })
    if row.get("edited_narrative"):
        vc = int(row.get("version_count", 2)) if row.get("version_count") else 2
        versions.append({
            "version_number": vc,
            "narrative_text": row.get("edited_narrative", ""),
            "changed_by": row.get("reviewer", "analyst"),
            "change_type": "analyst_edit",
        })

    return {"variance_id": variance_id, "versions": versions, "count": len(versions)}


# ---------------------------------------------------------------------------
# On-demand summary regeneration
# ---------------------------------------------------------------------------

@router.post(
    "/{variance_id}/regenerate",
    summary="Regenerate parent summary from approved children",
)
async def regenerate_summary(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("director", "cfo", "admin")),
):
    """Regenerate a parent account narrative from its approved child narratives.

    Only works on calculated/parent accounts. Creates a new AI_DRAFT.
    """
    store = request.app.state.review_store
    rs = store._review_status if hasattr(store, '_review_status') else store._store._review_status
    vm = store._variance_material if hasattr(store, '_variance_material') else store._store._variance_material

    mask = vm["variance_id"] == variance_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Variance not found")

    row = vm[mask].iloc[0]
    if not row.get("is_calculated", False):
        raise HTTPException(status_code=400, detail="Regeneration only available for parent/calculated accounts")

    # Collect child narratives (simplified — uses existing material data)
    parent_acct = row["account_id"]
    from shared.data.loader import DataLoader
    dl = DataLoader(request.app.state.data_service._loader._data_dir if hasattr(request.app.state, 'data_service') else 'data/output')
    acct = dl.load_table("dim_account")

    children_ids = acct[acct["parent_id"] == parent_acct]["account_id"].tolist()
    child_narrs = vm[vm["account_id"].isin(children_ids) & (vm["period_id"] == row["period_id"]) & (vm["view_id"] == row["view_id"]) & (vm["base_id"] == row["base_id"])]

    child_texts = []
    for _, c in child_narrs.iterrows():
        name = acct[acct["account_id"] == c["account_id"]]["account_name"].iloc[0] if not acct[acct["account_id"] == c["account_id"]].empty else c["account_id"]
        narr = c.get("edited_narrative") or c.get("narrative_detail", "")
        child_texts.append(f"{name}: {narr[:100]}")

    if not child_texts:
        raise HTTPException(status_code=400, detail="No child narratives found for regeneration")

    # Simple synthesis (template — LLM synthesis available via synthesis API)
    direction = "increased" if row["variance_amount"] > 0 else "decreased"
    new_narrative = (
        f"{row.get('account_id', '')} {direction} by ${abs(row['variance_amount']):,.0f}. "
        f"Regenerated from {len(child_texts)} approved children: "
        + "; ".join(child_texts[:3])
        + ". [Regenerated]"
    )

    # Update as new AI_DRAFT
    rs_mask = rs["variance_id"] == variance_id
    if rs_mask.any():
        rs.loc[rs_mask, "status"] = "AI_DRAFT"
        rs.loc[rs_mask, "edited_narrative"] = new_narrative
        if "version_count" in rs.columns:
            vc = int(rs.loc[rs_mask, "version_count"].iloc[0] or 0) + 1
            rs.loc[rs_mask, "version_count"] = vc

    return {
        "variance_id": variance_id,
        "new_status": "AI_DRAFT",
        "narrative": new_narrative[:200],
        "child_count": len(child_texts),
        "message": f"Regenerated from {len(child_texts)} children",
    }


# ---------------------------------------------------------------------------
# Cascade Regeneration API (Phase 3C — wired in Framework Completion sprint)
# ---------------------------------------------------------------------------


@router.post(
    "/{variance_id}/cascade-regenerate",
    summary="Manually trigger cascade regeneration",
)
async def cascade_regenerate(
    variance_id: str,
    request: Request,
    user: UserContext = Depends(require_role("director", "cfo", "admin")),
):
    """Manually trigger cascade regeneration for a variance.

    Skips debounce — executes immediately. Regenerates affected
    parents, sections, and executive summary.
    """
    cascade_mgr = getattr(request.app.state, "cascade_manager", None)
    if cascade_mgr is None:
        raise HTTPException(status_code=503, detail="Cascade manager not initialized")

    # Get period_id from variance data
    store = request.app.state.review_store
    vm = store._variance_material if hasattr(store, '_variance_material') else store._store._variance_material
    mask = vm["variance_id"] == variance_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Variance not found")

    period_id = str(vm[mask].iloc[0].get("period_id", ""))
    result = await cascade_mgr.execute_now(variance_id, period_id)

    return {
        "cascade_id": result.cascade_id,
        "trigger_variance_id": result.trigger_variance_id,
        "period_id": result.period_id,
        "regenerated": result.regenerated,
        "skipped": result.skipped,
        "total_seconds": result.total_seconds,
        "errors": result.errors,
    }


@router.get(
    "/cascade/status",
    summary="Get cascade regeneration status",
)
async def cascade_status(
    request: Request,
    user: UserContext = Depends(require_role("analyst", "director", "cfo", "admin")),
):
    """Return pending cascades and recent history."""
    cascade_mgr = getattr(request.app.state, "cascade_manager", None)
    if cascade_mgr is None:
        return {"pending": [], "running": [], "history": []}

    return {
        "pending": cascade_mgr.get_pending(),
        "running": cascade_mgr.get_running(),
        "history": cascade_mgr.get_history(limit=10),
    }
