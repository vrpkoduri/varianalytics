"""Report scheduling endpoints.

Manages recurring and one-off report generation schedules so that
reports can be automatically produced at period close.
"""

from __future__ import annotations

import uuid
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    frequency: ScheduleFrequency
    cron_expression: str | None = None
    report_format: str
    template_id: str | None = None
    period_key_pattern: str
    comparison_base: str
    view: str
    enabled: bool
    last_run_at: str | None = None
    next_run_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules() -> list[ScheduleResponse]:
    """List all configured report schedules."""
    # TODO: query persistence
    return []


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(payload: ScheduleCreate) -> ScheduleResponse:
    """Create a new report schedule."""
    schedule_id = str(uuid.uuid4())
    return ScheduleResponse(
        schedule_id=schedule_id,
        name=payload.name,
        description=payload.description,
        frequency=payload.frequency,
        cron_expression=payload.cron_expression,
        report_format=payload.report_format,
        template_id=payload.template_id,
        period_key_pattern=payload.period_key_pattern,
        comparison_base=payload.comparison_base,
        view=payload.view,
        enabled=payload.enabled,
    )


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
) -> ScheduleResponse:
    """Update an existing report schedule."""
    # TODO: fetch existing, apply partial update
    raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found.")


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str) -> None:
    """Delete a report schedule."""
    # TODO: remove from persistence
    raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found.")
