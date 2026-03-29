"""Report generation endpoints.

Provides routes to trigger report generation, check status, download
completed reports, list available templates, and view generation history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportFormat(str, Enum):
    """Supported export formats."""

    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"
    XLSX = "xlsx"


class ReportStatus(str, Enum):
    """Job lifecycle states."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateReportRequest(BaseModel):
    """Payload to trigger report generation."""

    report_format: ReportFormat
    template_id: str | None = None
    period_key: str = Field(..., description="e.g. '2026-02'")
    comparison_base: str = Field(default="budget", description="budget | forecast | py")
    view: str = Field(default="MTD", description="MTD | QTD | YTD")
    filters: dict[str, Any] = Field(default_factory=dict)


class GenerateReportResponse(BaseModel):
    """Acknowledgement with tracking job_id."""

    job_id: str
    status: ReportStatus
    message: str


class ReportStatusResponse(BaseModel):
    """Current state of a generation job."""

    job_id: str
    status: ReportStatus
    progress_pct: float = 0.0
    created_at: str
    completed_at: str | None = None
    download_url: str | None = None
    error: str | None = None


class ReportTemplate(BaseModel):
    """Metadata for a report template."""

    template_id: str
    name: str
    description: str
    format: ReportFormat


class ReportHistoryItem(BaseModel):
    """Summary of a previously generated report."""

    job_id: str
    report_format: ReportFormat
    status: ReportStatus
    period_key: str
    created_at: str
    completed_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest) -> GenerateReportResponse:
    """Trigger asynchronous report generation.

    Returns a ``job_id`` that can be polled via ``GET /status/{job_id}``.
    """
    job_id = str(uuid.uuid4())
    return GenerateReportResponse(
        job_id=job_id,
        status=ReportStatus.QUEUED,
        message=f"Report generation queued for period {request.period_key} "
        f"in {request.report_format.value} format.",
    )


@router.get("/status/{job_id}", response_model=ReportStatusResponse)
async def get_report_status(job_id: str) -> ReportStatusResponse:
    """Check the current status of a report generation job."""
    # TODO: look up job from persistence / task queue
    return ReportStatusResponse(
        job_id=job_id,
        status=ReportStatus.QUEUED,
        progress_pct=0.0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/download/{job_id}")
async def download_report(job_id: str) -> dict[str, str]:
    """Download a completed report by job_id.

    Returns a pre-signed URL or streams the file directly.
    """
    # TODO: resolve artefact path, stream file / return signed URL
    raise HTTPException(
        status_code=404,
        detail=f"Report for job {job_id} not found or not yet completed.",
    )


@router.get("/templates", response_model=list[ReportTemplate])
async def list_templates() -> list[ReportTemplate]:
    """List available report templates (PPTX masters, XLSX layouts, etc.)."""
    # TODO: scan templates/ directory
    return [
        ReportTemplate(
            template_id="default-pdf",
            name="Standard Variance Report",
            description="Period-end variance analysis with waterfall charts.",
            format=ReportFormat.PDF,
        ),
        ReportTemplate(
            template_id="board-pptx",
            name="Board Package",
            description="Executive slide deck from slide master template.",
            format=ReportFormat.PPTX,
        ),
        ReportTemplate(
            template_id="detail-xlsx",
            name="Detailed Excel Export",
            description="Formatted workbook with narratives and drill-down tabs.",
            format=ReportFormat.XLSX,
        ),
    ]


@router.get("/history", response_model=list[ReportHistoryItem])
async def list_report_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ReportHistoryItem]:
    """Return previously generated reports (most recent first)."""
    # TODO: query persistence layer
    return []
