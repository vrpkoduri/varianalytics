"""Report distribution endpoints.

Handles sending generated reports to recipients via email, Teams/Slack
webhooks, and managing reusable distribution lists.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/distribution", tags=["distribution"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DistributionChannel(BaseModel):
    """A single delivery channel (email, Teams, Slack, etc.)."""

    channel_type: str = Field(..., description="email | teams | slack")
    target: str = Field(..., description="Email address or webhook URL.")


class DistributionListCreate(BaseModel):
    """Payload to create a named distribution list."""

    name: str
    description: str | None = None
    channels: list[DistributionChannel] = Field(default_factory=list)


class DistributionListResponse(BaseModel):
    """Full distribution list record."""

    list_id: str
    name: str
    description: str | None = None
    channels: list[DistributionChannel]


class SendReportRequest(BaseModel):
    """Payload to distribute a completed report."""

    job_id: str = Field(..., description="ID of the completed report generation job.")
    distribution_list_ids: list[str] = Field(
        default_factory=list,
        description="IDs of saved distribution lists to send to.",
    )
    ad_hoc_channels: list[DistributionChannel] = Field(
        default_factory=list,
        description="Additional one-off recipients.",
    )
    message: str | None = Field(
        default=None,
        description="Optional cover note included with the report.",
    )


class SendReportResponse(BaseModel):
    """Acknowledgement of a distribution request."""

    distribution_id: str
    recipients_count: int
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/send", response_model=SendReportResponse)
async def send_report(payload: SendReportRequest) -> SendReportResponse:
    """Distribute a completed report to the specified recipients.

    Only reports with status APPROVED are eligible for distribution.
    """
    distribution_id = str(uuid.uuid4())
    total = len(payload.distribution_list_ids) + len(payload.ad_hoc_channels)
    # TODO: resolve list members, enqueue delivery tasks
    return SendReportResponse(
        distribution_id=distribution_id,
        recipients_count=total,
        status="queued",
    )


@router.get("/recipients", response_model=list[DistributionListResponse])
async def list_distribution_lists(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DistributionListResponse]:
    """List saved distribution lists."""
    # TODO: query persistence
    return []


@router.post("/recipients", response_model=DistributionListResponse, status_code=201)
async def create_distribution_list(
    payload: DistributionListCreate,
) -> DistributionListResponse:
    """Create a new distribution list."""
    list_id = str(uuid.uuid4())
    return DistributionListResponse(
        list_id=list_id,
        name=payload.name,
        description=payload.description,
        channels=payload.channels,
    )
