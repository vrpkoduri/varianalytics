"""Engine Task Queue — background engine run management.

In-process asyncio task queue for running the computation engine
from the Admin UI. Supports Process A, Process B, or Full pipeline.

Features:
- Max 1 concurrent engine run (protects resources)
- Progress tracking with current pass name
- Task cancellation
- Run history with results

Usage::

    queue = EngineTaskQueue(data_dir="data/output")
    task = await queue.submit({
        "period_id": "2026-06",
        "process": "full",
        "mode": "template",
    })
    # Poll: queue.get_task(task.task_id)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("engine.task_queue")

MAX_HISTORY = 100


@dataclass
class EngineTask:
    """Represents a queued or running engine task."""

    task_id: str = ""
    status: str = "queued"  # queued, running, completed, failed, cancelled
    process: str = "full"   # a, b, full
    mode: str = "template"  # llm, template
    period_id: str = ""
    periods: list[str] = field(default_factory=list)
    multi_period: bool = False
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    current_pass: str = ""
    cost_estimate: dict[str, Any] = field(default_factory=dict)
    actual_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "process": self.process,
            "mode": self.mode,
            "period_id": self.period_id,
            "periods": self.periods,
            "multi_period": self.multi_period,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "current_pass": self.current_pass,
            "cost_estimate": self.cost_estimate,
            "actual_result": self.actual_result,
            "error": self.error,
        }


class EngineTaskQueue:
    """In-process async task queue for engine runs.

    Args:
        data_dir: Path to data output directory.
        max_concurrent: Max concurrent engine runs (default 1).
    """

    def __init__(
        self,
        data_dir: str = "data/output",
        max_concurrent: int = 1,
    ) -> None:
        self._data_dir = data_dir
        self._max_concurrent = max_concurrent
        self._tasks: dict[str, EngineTask] = {}
        self._task_order: list[str] = []  # Ordered by creation
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def submit(self, config: dict[str, Any]) -> EngineTask:
        """Submit a new engine task.

        Args:
            config: Dict with period_id, process, mode, multi_period.

        Returns:
            EngineTask with status "queued" or "running".
        """
        task = EngineTask(
            task_id=str(uuid4())[:8],
            status="queued",
            process=config.get("process", "full"),
            mode=config.get("mode", "template"),
            period_id=config.get("period_id", "2026-06"),
            multi_period=config.get("multi_period", False),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Build periods list
        if task.multi_period:
            task.periods = self._generate_periods(task.period_id, 12)
        else:
            task.periods = [task.period_id]

        # Compute cost estimate
        from services.computation.engine.cost_estimator import estimate_process_b_cost
        material_count = self._estimate_material_count()
        if task.process in ("b", "full"):
            task.cost_estimate = estimate_process_b_cost(
                material_count * len(task.periods),
                mode=task.mode,
            )
        else:
            task.cost_estimate = {"estimated_cost_usd": 0.0, "estimated_calls": 0}

        self._tasks[task.task_id] = task
        self._task_order.append(task.task_id)

        # Trim old tasks
        if len(self._task_order) > MAX_HISTORY:
            old_id = self._task_order.pop(0)
            if old_id not in self._running_tasks:
                self._tasks.pop(old_id, None)

        # Start execution if under concurrency limit
        if len(self._running_tasks) < self._max_concurrent:
            self._start_task(task)
        else:
            logger.info(
                "Engine task %s queued (max concurrent %d reached)",
                task.task_id, self._max_concurrent,
            )

        return task

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running or queued task.

        Returns True if cancelled, False if not found or already complete.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in ("completed", "failed", "cancelled"):
            return False

        # Cancel asyncio task
        atask = self._running_tasks.pop(task_id, None)
        if atask:
            atask.cancel()

        task.status = "cancelled"
        task.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info("Engine task %s cancelled", task_id)
        return True

    def get_task(self, task_id: str) -> Optional[EngineTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list[EngineTask]:
        """List recent tasks, newest first."""
        ids = list(reversed(self._task_order[-limit:]))
        return [self._tasks[tid] for tid in ids if tid in self._tasks]

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _start_task(self, task: EngineTask) -> None:
        """Start task execution in background."""
        atask = asyncio.create_task(self._execute_task(task))
        self._running_tasks[task.task_id] = atask

        # Cleanup on completion
        def _on_done(fut: asyncio.Future) -> None:
            self._running_tasks.pop(task.task_id, None)
            # Check if there are queued tasks to start
            for tid in self._task_order:
                t = self._tasks.get(tid)
                if t and t.status == "queued":
                    self._start_task(t)
                    break

        atask.add_done_callback(_on_done)

    async def _execute_task(self, task: EngineTask) -> None:
        """Execute an engine task."""
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.progress = 0.0

        logger.info(
            "Engine task %s started: process=%s, mode=%s, periods=%d",
            task.task_id, task.process, task.mode, len(task.periods),
        )

        try:
            from services.computation.engine.runner import EngineRunner

            runner = EngineRunner()
            all_timings = []
            total_material = 0

            for i, period in enumerate(task.periods):
                task.current_pass = f"Period {period} ({i+1}/{len(task.periods)})"
                task.progress = i / len(task.periods)

                if task.process == "a":
                    result = await runner.run_process_a(
                        period_id=period,
                        data_dir=self._data_dir,
                        save_intermediate=True,
                    )
                    all_timings.extend(result.timings)
                    total_material += result.material_variances
                    task.current_pass = f"Process A complete for {period}"

                elif task.process == "b":
                    result = await runner.run_process_b(
                        data_dir=self._data_dir,
                        period_id=period,
                        llm_client=self._get_llm_client() if task.mode == "llm" else None,
                    )
                    all_timings.extend(result.timings)
                    task.current_pass = f"Process B complete for {period}"

                else:  # full
                    result = await runner.run_full_pipeline(
                        period_id=period,
                        data_dir=self._data_dir,
                        llm_client=self._get_llm_client() if task.mode == "llm" else None,
                    )
                    all_timings.extend(result.timings)
                    total_material += result.material_variances
                    task.current_pass = f"Full pipeline complete for {period}"

            task.progress = 1.0
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc).isoformat()
            task.actual_result = {
                "material_variances": total_material,
                "total_time_seconds": sum(t.elapsed_seconds for t in all_timings),
                "periods_processed": len(task.periods),
                "pass_timings": [
                    {"name": t.pass_name, "seconds": round(t.elapsed_seconds, 2)}
                    for t in all_timings
                ],
            }

            logger.info(
                "Engine task %s completed: %d material, %.1f s",
                task.task_id, total_material,
                task.actual_result["total_time_seconds"],
            )

        except asyncio.CancelledError:
            task.status = "cancelled"
            task.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info("Engine task %s was cancelled", task.task_id)

        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            logger.exception("Engine task %s failed: %s", task.task_id, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _estimate_material_count(self) -> int:
        """Estimate material variance count from current data."""
        try:
            from shared.data.loader import DataLoader
            loader = DataLoader(self._data_dir)
            if loader.table_exists("fact_variance_material"):
                df = loader.load_table("fact_variance_material")
                # Count per single period (approximate)
                if "period_id" in df.columns:
                    return int(len(df) / max(df["period_id"].nunique(), 1))
                return len(df)
        except Exception:
            pass
        return 10000  # Default estimate

    def _get_llm_client(self) -> Any:
        """Get LLM client if available."""
        try:
            from shared.llm.client import LLMClient
            client = LLMClient()
            return client if client.is_available else None
        except Exception:
            return None

    @staticmethod
    def _generate_periods(end_period: str, count: int) -> list[str]:
        """Generate trailing period list ending at end_period."""
        try:
            year, month = int(end_period[:4]), int(end_period[5:7])
            periods = []
            for i in range(count - 1, -1, -1):
                m = month - i
                y = year
                while m <= 0:
                    m += 12
                    y -= 1
                periods.append(f"{y}-{m:02d}")
            return periods
        except (ValueError, IndexError):
            return [end_period]
