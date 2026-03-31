"""Report scheduling endpoints.

Manages recurring and one-off report generation schedules so that
reports can be automatically produced at period close.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from enum import Enum

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScheduleFrequency(str, Enum):
    """Recurrence options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_DEMAND = "on_demand"


class ScheduleCreate(BaseModel):
    """Payload to create a new schedule."""

    name: str
    description: str | None = None
    frequency: ScheduleFrequency
    cron_expression: str | None = Field(
        default=None,
        description="Optional cron for fine-grained scheduling.",
    )
    report_format: str = "pdf"
    template_id: str | None = None
    period_key_pattern: str = Field(
        default="latest",
        description="'latest' or explicit pattern e.g. '{YYYY}-{MM}'.",
    )
    comparison_base: str = "budget"
    view: str = "MTD"
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    """Partial update for an existing schedule."""

    name: str | None = None
    description: str | None = None
    frequency: ScheduleFrequency | None = None
    cron_expression: str | None = None
    report_format: str | None = None
    template_id: str | None = None
    period_key_pattern: str | None = None
    comparison_base: str | None = None
    view: str | None = None
    enabled: bool | None = None


class ScheduleResponse(BaseModel):
    """Full schedule record returned to callers."""

    schedule_id: str
    name: str
    description: str | None = None
    frequency: str | None = None
    cron_expression: str | None = None
    report_format: str = "pdf"
    template_id: str | None = None
    period_key_pattern: str = "latest"
    comparison_base: str = "budget"
    view: str = "MTD"
    enabled: bool = True
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/schedules")
async def list_schedules(request: Request):
    """List all configured report schedules."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        return []
    return scheduler.list_schedules()


@router.post("/schedules")
async def create_schedule(body: ScheduleCreate, request: Request):
    """Create a new report schedule."""
    scheduler = getattr(request.app.state, "scheduler", None)
    schedule_id = str(uuid4())
    config = body.model_dump()
    if scheduler:
        result = scheduler.add_schedule(schedule_id, config)
        return ScheduleResponse(**result)
    return ScheduleResponse(schedule_id=schedule_id, **config)


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, body: ScheduleUpdate, request: Request):
    """Update an existing report schedule."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(404, "Scheduler not initialized")
    result = scheduler.update_schedule(schedule_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, f"Schedule {schedule_id} not found")
    return ScheduleResponse(**result)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str, request: Request):
    """Delete a report schedule."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler or not scheduler.remove_schedule(schedule_id):
        raise HTTPException(404, f"Schedule {schedule_id} not found")
