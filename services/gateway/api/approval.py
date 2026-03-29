"""Approval workflow endpoints.

Directors and BU leaders use these endpoints for bulk approval of
analyst-reviewed variances. Only ANALYST_REVIEWED items appear here.
Report distribution is gated on APPROVED status.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approval", tags=["approval"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ApprovalQueueItem(BaseModel):
    """Single item in the director approval queue."""

    variance_id: str
    account_name: str
    period_label: str
    variance_amount: float
    variance_pct: Optional[float] = None
    analyst_name: str = ""
    reviewed_narrative: str = ""


class ApprovalQueueResponse(BaseModel):
    """Paginated approval queue."""

    items: list[ApprovalQueueItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class BulkApprovalAction(BaseModel):
    """Bulk approval action payload."""

    variance_ids: list[str] = Field(..., min_length=1)
    action: str = Field("approve", description="approve | reject")
    comment: Optional[str] = None


class BulkApprovalResponse(BaseModel):
    """Result of a bulk approval action."""

    approved_count: int = 0
    rejected_count: int = 0
    errors: list[str] = Field(default_factory=list)


class ApprovalStats(BaseModel):
    """Aggregate approval queue statistics."""

    pending_approval: int = 0
    approved_today: int = 0
    rejected_today: int = 0
    total_approved: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/queue",
    response_model=ApprovalQueueResponse,
    summary="Get approval queue",
)
async def get_approval_queue(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> ApprovalQueueResponse:
    """Return items pending director approval (status = ANALYST_REVIEWED)."""
    store = request.app.state.review_store
    result = store.get_approval_queue(page=page, page_size=page_size)
    return ApprovalQueueResponse(
        items=[ApprovalQueueItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post(
    "/actions",
    response_model=BulkApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk approve or reject variances",
)
async def submit_bulk_approval(body: BulkApprovalAction, request: Request) -> BulkApprovalResponse:
    """Approve or reject multiple analyst-reviewed variances in one action.

    Approved items become eligible for report distribution.
    """
    store = request.app.state.review_store
    result = store.submit_bulk_approval(
        variance_ids=body.variance_ids,
        action=body.action,
        comment=body.comment,
    )
    return BulkApprovalResponse(**result)


@router.get(
    "/stats",
    response_model=ApprovalStats,
    summary="Get approval statistics",
)
async def get_approval_stats(request: Request) -> ApprovalStats:
    """Return aggregate approval counts and metrics."""
    store = request.app.state.review_store
    stats = store.get_approval_stats()
    return ApprovalStats(**stats)
