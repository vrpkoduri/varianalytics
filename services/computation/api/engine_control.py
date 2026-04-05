"""Engine Control API — run engine, track progress, estimate costs.

Endpoints for the Admin Engine Control panel. Runs in the computation
service (port 8001) where the EngineRunner lives.

Phase 3D.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from shared.engine.cost_estimator import estimate_process_b_cost

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/engine", tags=["engine"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EngineEstimateRequest(BaseModel):
    period_id: str = "2026-06"
    process: str = "full"  # a, b, full
    mode: str = "template"  # llm, template
    multi_period: bool = False


class EngineRunRequest(BaseModel):
    period_id: str = "2026-06"
    process: str = "full"
    mode: str = "template"
    multi_period: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/estimate", summary="Estimate engine run cost")
async def engine_estimate(body: EngineEstimateRequest) -> dict:
    """Preview cost/time estimate before running engine."""
    periods_count = 12 if body.multi_period else 1

    if body.process == "a":
        return {
            "estimated_calls": 0,
            "estimated_cost_usd": 0.0,
            "estimated_time_minutes": round(0.3 * periods_count, 1),
            "mode": "deterministic",
            "process": "a",
            "periods": periods_count,
            "note": "Process A is pure math — no AI Agent charges.",
        }

    # Estimate material count from data
    material_per_period = 10000
    try:
        from shared.data.loader import DataLoader
        loader = DataLoader("data/output")
        if loader.table_exists("fact_variance_material"):
            df = loader.load_table("fact_variance_material")
            if "period_id" in df.columns:
                material_per_period = int(len(df) / max(df["period_id"].nunique(), 1))
    except Exception:
        pass

    est = estimate_process_b_cost(
        material_per_period * periods_count,
        mode=body.mode,
    )
    est["process"] = body.process
    est["periods"] = periods_count
    return est


@router.post("/run", summary="Queue an engine run")
async def engine_run(body: EngineRunRequest, request: Request) -> dict:
    """Submit a new engine task to the background queue."""
    queue = getattr(request.app.state, "engine_task_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Engine task queue not initialized")

    task = await queue.submit({
        "period_id": body.period_id,
        "process": body.process,
        "mode": body.mode,
        "multi_period": body.multi_period,
    })
    return task.to_dict()


@router.get("/tasks", summary="List engine tasks")
async def engine_tasks(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
) -> list:
    """List recent engine tasks, newest first."""
    queue = getattr(request.app.state, "engine_task_queue", None)
    if queue is None:
        return []
    return [t.to_dict() for t in queue.list_tasks(limit=limit)]


@router.get("/tasks/{task_id}", summary="Get engine task details")
async def engine_task_detail(task_id: str, request: Request) -> dict:
    """Get status, progress, and result for a specific engine task."""
    queue = getattr(request.app.state, "engine_task_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Engine task queue not initialized")

    task = queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.to_dict()


@router.post("/tasks/{task_id}/cancel", summary="Cancel an engine task")
async def engine_task_cancel(task_id: str, request: Request) -> dict:
    """Cancel a running or queued engine task."""
    queue = getattr(request.app.state, "engine_task_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Engine task queue not initialized")

    success = await queue.cancel(task_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Task {task_id} cannot be cancelled")
    return {"task_id": task_id, "status": "cancelled"}


@router.post("/reload", summary="Reload data from disk")
async def reload_data(request: Request) -> dict:
    """Force DataService to reload all tables from parquet files.

    Use after running the engine via CLI to refresh in-memory data
    without restarting the service.
    """
    ds = getattr(request.app.state, "data_service", None)
    if ds is None:
        raise HTTPException(status_code=503, detail="DataService not initialized")

    ds._load_all_tables()
    ds._build_account_metadata()
    ds.invalidate_graph_cache()

    table_counts = {name: len(df) for name, df in ds._tables.items() if not df.empty}

    return {
        "status": "reloaded",
        "tables": table_counts,
    }
