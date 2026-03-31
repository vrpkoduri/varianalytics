"""Report distribution endpoints.

Handles sending generated reports to recipients via email, Teams/Slack
webhooks, and managing reusable distribution lists.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request
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
# In-memory store
# ---------------------------------------------------------------------------

_distribution_lists: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/send", response_model=SendReportResponse)
async def send_report(body: SendReportRequest, request: Request) -> SendReportResponse:
    """Distribute a completed report to the specified recipients.

    Only reports with status COMPLETED are eligible for distribution.
    """
    # Get report job status
    from services.reports.api.reports import _jobs
    job = _jobs.get(body.job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(400, f"Report {body.job_id} not ready for distribution")

    # Collect channels from ad-hoc + distribution lists
    channels: list[DistributionChannel] = list(body.ad_hoc_channels or [])
    for list_id in (body.distribution_list_ids or []):
        dl = _distribution_lists.get(list_id)
        if dl:
            channels.extend(
                DistributionChannel(**c) if isinstance(c, dict) else c
                for c in dl.get("channels", [])
            )

    # Send via notification dispatcher
    results: list[tuple[str, bool]] = []
    try:
        from services.gateway.notifications import notify_event
        results = await notify_event("report_ready", {
            "title": f"Report Ready: {job.get('period_id', '')} {job.get('format', '')}",
            "body": body.message or "A new report has been generated and is ready for download.",
            "action_url": "http://localhost:3000/reports",
            "recipients": [c.target for c in channels if c.channel_type == "email"],
        })
    except Exception:
        # Notification dispatch is best-effort
        pass

    return SendReportResponse(
        distribution_id=str(uuid.uuid4()),
        recipients_count=len(channels),
        status="sent" if results and any(s for _, s in results) else "queued",
    )


@router.get("/recipients", response_model=list[DistributionListResponse])
async def list_distribution_lists(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DistributionListResponse]:
    """List saved distribution lists."""
    items = list(_distribution_lists.values())[offset:offset + limit]
    return [DistributionListResponse(**dl) for dl in items]


@router.post("/recipients", response_model=DistributionListResponse, status_code=201)
async def create_distribution_list(
    payload: DistributionListCreate,
) -> DistributionListResponse:
    """Create a new distribution list."""
    list_id = str(uuid.uuid4())
    dl = {
        "list_id": list_id,
        "name": payload.name,
        "description": payload.description,
        "channels": [c.model_dump() for c in payload.channels],
    }
    _distribution_lists[list_id] = dl
    return DistributionListResponse(
        list_id=list_id,
        name=payload.name,
        description=payload.description,
        channels=payload.channels,
    )
