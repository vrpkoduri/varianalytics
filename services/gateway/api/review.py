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
