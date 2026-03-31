"""Report generation endpoints.

Provides routes to trigger report generation, check status, download
completed reports, list available templates, and view generation history.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.reports.generators.data_provider import ReportDataProvider
from services.reports.generators.storage import LocalReportStorage
from services.reports.generators.xlsx_generator import XLSXGenerator
from services.reports.generators.pdf_generator import PDFGenerator
from services.reports.generators.pptx_generator import PPTXGenerator
from services.reports.generators.docx_generator import DOCXGenerator

logger = logging.getLogger(__name__)

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
# In-memory job tracking
# ---------------------------------------------------------------------------

_jobs: dict[str, dict] = {}

_FORMAT_GENERATORS = {
    "xlsx": XLSXGenerator,
    "pdf": PDFGenerator,
    "pptx": PPTXGenerator,
    "docx": DOCXGenerator,
}

_CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def _run_generation(job_id: str, body: GenerateReportRequest, app_state: Any) -> None:
    """Background task: fetch data, generate report, save to storage."""
    _jobs[job_id]["status"] = "in_progress"
    try:
        # Fetch data from computation service
        provider: ReportDataProvider = app_state.data_provider
        ctx = await provider.fetch_context(
            body.period_key, body.comparison_base, body.view,
        )

        # Pick generator
        gen_cls = _FORMAT_GENERATORS.get(body.report_format.value)
        if not gen_cls:
            raise ValueError(f"Unknown format: {body.report_format}")
        gen = gen_cls()

        # Generate report bytes
        data = await gen.generate(ctx)

        # Save to storage
        ext = body.report_format.value
        storage: LocalReportStorage = app_state.storage
        await storage.save(job_id, f"report.{ext}", data)

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _jobs[job_id]["download_url"] = f"/api/v1/reports/download/{job_id}"
        logger.info("Report %s completed (%s, %d bytes)", job_id, ext, len(data))
    except Exception as exc:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(exc)
        logger.error("Report %s failed: %s", job_id, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> GenerateReportResponse:
    """Trigger asynchronous report generation.

    Returns a ``job_id`` that can be polled via ``GET /status/{job_id}``.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "format": body.report_format.value,
        "period_key": body.period_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "download_url": None,
        "error": None,
    }
    background_tasks.add_task(_run_generation, job_id, body, request.app.state)
    return GenerateReportResponse(
        job_id=job_id,
        status=ReportStatus.QUEUED,
        message=f"Report generation queued for period {body.period_key} "
        f"in {body.report_format.value} format.",
    )


@router.get("/status/{job_id}", response_model=ReportStatusResponse)
async def get_report_status(job_id: str) -> ReportStatusResponse:
    """Check the current status of a report generation job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return ReportStatusResponse(
        job_id=job["job_id"],
        status=ReportStatus(job["status"]),
        progress_pct=100.0 if job["status"] == "completed" else 0.0,
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        download_url=job.get("download_url"),
        error=job.get("error"),
    )


@router.get("/download/{job_id}")
async def download_report(job_id: str, request: Request):
    """Download a completed report by job_id."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409, detail=f"Report not ready. Status: {job['status']}",
        )

    storage: LocalReportStorage = request.app.state.storage
    path = await storage.get_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="Report file not found on disk.")

    fmt = job.get("format", "xlsx")
    content_type = _CONTENT_TYPES.get(fmt, "application/octet-stream")
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=f"variance_report_{job.get('period_key', 'unknown')}.{fmt}",
    )


@router.get("/templates", response_model=list[ReportTemplate])
async def list_templates() -> list[ReportTemplate]:
    """List available report templates (PPTX masters, XLSX layouts, etc.)."""
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
    items = []
    sorted_jobs = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)
    for job in sorted_jobs[offset:offset + limit]:
        items.append(ReportHistoryItem(
            job_id=job["job_id"],
            report_format=ReportFormat(job["format"]),
            status=ReportStatus(job["status"]),
            period_key=job["period_key"],
            created_at=job["created_at"],
            completed_at=job.get("completed_at"),
        ))
    return items
