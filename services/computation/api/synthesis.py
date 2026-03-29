"""Synthesis endpoints — trigger and monitor narrative synthesis.

Prefix: /synthesis

Synthesis runs OUTSIDE the main engine pipeline. It is triggered
when an analyst approves a variance, aggregating approved child
commentaries bottom-up into parent summary narratives.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


# ---------------------------------------------------------------------------
# POST /synthesis/trigger/{variance_id}
# ---------------------------------------------------------------------------

@router.post("/trigger/{variance_id}")
async def trigger_synthesis(variance_id: str) -> dict[str, Any]:
    """Trigger bottom-up narrative synthesis for an approved variance.

    Preconditions:
    - The variance must have review_status = APPROVED in fact_review_status.
    - All child variances in the hierarchy should be ANALYST_REVIEWED
      or APPROVED for complete synthesis.

    The synthesis process:
    1. Collect approved child commentaries from fact_review_status.
    2. Aggregate via LLM into parent midlevel/summary narratives.
    3. Update fact_variance_material with synthesized narratives.
    4. Log to audit_log.
    """
    # TODO: validate approval status, run synthesis pipeline
    return {
        "variance_id": variance_id,
        "status": "accepted",
        "message": "Synthesis queued",
    }


# ---------------------------------------------------------------------------
# GET /synthesis/status/{variance_id}
# ---------------------------------------------------------------------------

@router.get("/status/{variance_id}")
async def get_synthesis_status(variance_id: str) -> dict[str, Any]:
    """Check the synthesis status for a given variance.

    Returns current synthesis state: pending, in_progress, completed,
    or failed, along with timestamps and any error details.
    """
    # TODO: query synthesis job status
    return {
        "variance_id": variance_id,
        "synthesis_status": "not_started",
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
