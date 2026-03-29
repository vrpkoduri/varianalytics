"""Pydantic schemas for review/approval workflow API payloads."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.models.enums import ReviewStatus


class ReviewAction(BaseModel):
    """Analyst review action on a variance."""

    variance_id: str
    action: str = Field(..., description="confirm, edit, dismiss, escalate")
    edited_narrative: Optional[str] = None
    hypothesis_feedback: Optional[dict[str, bool]] = Field(
        None, description="hypothesis_id -> thumbs_up"
    )
    notes: Optional[str] = None


class ApprovalAction(BaseModel):
    """Director approval action."""

    variance_ids: list[str] = Field(..., description="One or more variance IDs to approve")
    action: str = Field(..., description="approve, hold, escalate")
    notes: Optional[str] = None


class ReviewQueueItem(BaseModel):
    """Single item in the review queue."""

    variance_id: str
    account_name: str
    bu_name: str
    period_id: str
    variance_amount: float
    variance_pct: Optional[float]
    status: ReviewStatus
    assigned_analyst: Optional[str]
    narrative_preview: str = Field(..., description="First 100 chars of narrative")
    created_at: datetime
    sla_hours_remaining: Optional[float] = Field(
        None, description="Hours until SLA breach"
    )
    impact_rank: int = Field(..., description="Rank by absolute variance amount")


class ReviewQueueResponse(BaseModel):
    """Response for review queue endpoint."""

    items: list[ReviewQueueItem]
    total_count: int
    pending_count: int
    overdue_count: int
    stats: dict[str, Any] = Field(default_factory=dict)
