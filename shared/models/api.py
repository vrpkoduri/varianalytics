"""Pydantic schemas for API request/response payloads."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.models.enums import ComparisonBase, ViewType


class HealthResponse(BaseModel):
    """Health check response — shared across all services."""

    status: str = "ok"
    service: str
    version: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: str


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class FilterParams(BaseModel):
    """Standard filter parameters for variance queries."""

    period_id: Optional[str] = None
    bu_id: Optional[str] = None
    account_id: Optional[str] = None
    geo_node_id: Optional[str] = None
    segment_node_id: Optional[str] = None
    lob_node_id: Optional[str] = None
    costcenter_node_id: Optional[str] = None
    view: ViewType = ViewType.MTD
    base: ComparisonBase = ComparisonBase.BUDGET


class DashboardSummary(BaseModel):
    """Dashboard summary card data."""

    metric_name: str
    actual: float
    comparator: float
    variance: float
    variance_pct: Optional[float]
    trend_direction: Optional[str] = None
    review_status_counts: dict[str, int] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message payload."""

    message: str
    context: Optional[dict[str, Any]] = Field(
        None, description="Current filter context from UI"
    )
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response metadata (actual content streamed via SSE)."""

    conversation_id: str
    stream_url: str
