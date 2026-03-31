"""Report scheduler — evaluates schedules and triggers report generation."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ReportScheduler:
    """In-memory report scheduler using asyncio.

    Evaluates schedules every 60 seconds and triggers report generation
    for any schedules that are due.
    """

    def __init__(self, reports_url: str = "http://localhost:8002") -> None:
        self._schedules: dict[str, dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._reports_url = reports_url

    @property
    def schedules(self) -> dict[str, dict[str, Any]]:
        return self._schedules

    def add_schedule(self, schedule_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Add a schedule and return the stored record."""
        now = datetime.now(timezone.utc)
        schedule = {
            **config,
            "schedule_id": schedule_id,
            "name": config.get("name", "Unnamed"),
            "frequency": config.get("frequency", "WEEKLY"),
            "cron_expression": config.get("cron_expression"),
            "report_format": config.get("report_format", "PDF"),
            "period_key_pattern": config.get("period_key_pattern", "latest"),
            "comparison_base": config.get("comparison_base", "BUDGET"),
            "view": config.get("view", "MTD"),
            "enabled": config.get("enabled", True),
            "last_run_at": None,
            "next_run_at": self._compute_next_run(config),
            "created_at": now.isoformat(),
        }
        self._schedules[schedule_id] = schedule
        logger.info("Schedule added: %s (%s)", schedule_id, config.get("name", ""))
        return schedule

    def remove_schedule(self, schedule_id: str) -> bool:
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            logger.info("Schedule removed: %s", schedule_id)
            return True
        return False

    def update_schedule(self, schedule_id: str, updates: dict[str, Any]) -> Optional[dict]:
        if schedule_id not in self._schedules:
            return None
        for key, value in updates.items():
            if value is not None and key in self._schedules[schedule_id]:
                self._schedules[schedule_id][key] = value
        if "frequency" in updates or "cron_expression" in updates:
            self._schedules[schedule_id]["next_run_at"] = self._compute_next_run(
                self._schedules[schedule_id]
            )
        return self._schedules[schedule_id]

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        return self._schedules.get(schedule_id)

    def list_schedules(self) -> list[dict]:
        return list(self._schedules.values())

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("Report scheduler started (%d schedules)", len(self._schedules))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Report scheduler stopped")

    async def _tick_loop(self) -> None:
        while self._running:
            try:
                await self._evaluate_schedules()
            except Exception as exc:
                logger.error("Scheduler tick error: %s", exc)
            await asyncio.sleep(60)  # Check every 60 seconds

    async def _evaluate_schedules(self) -> list[str]:
        """Check for due schedules and trigger reports."""
        now = datetime.now(timezone.utc)
        triggered = []
        for sid, schedule in list(self._schedules.items()):
            if not schedule.get("enabled", True):
                continue
            next_run = schedule.get("next_run_at")
            if next_run and now.isoformat() >= next_run:
                await self._trigger_report(sid, schedule)
                schedule["last_run_at"] = now.isoformat()
                schedule["next_run_at"] = self._compute_next_run(schedule)
                triggered.append(sid)
        return triggered

    async def _trigger_report(self, schedule_id: str, config: dict) -> None:
        logger.info("Triggering scheduled report: %s", config.get("name", schedule_id))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{self._reports_url}/api/v1/reports/generate",
                    json={
                        "format": config.get("report_format", "PDF"),
                        "period_key": config.get("period_key_pattern", "2026-06"),
                        "comparison_base": config.get("comparison_base", "BUDGET"),
                        "view": config.get("view", "MTD"),
                    },
                )
        except Exception as exc:
            logger.error(
                "Failed to trigger report for schedule %s: %s", schedule_id, exc
            )

    @staticmethod
    def _compute_next_run(config: dict) -> str:
        """Compute next run time based on frequency. Simple interval-based for MVP."""
        now = datetime.now(timezone.utc)
        freq = str(config.get("frequency", "WEEKLY")).upper()
        intervals = {
            "DAILY": timedelta(days=1),
            "WEEKLY": timedelta(weeks=1),
            "MONTHLY": timedelta(days=30),
            "QUARTERLY": timedelta(days=90),
            "ON_DEMAND": timedelta(days=365 * 10),
        }
        delta = intervals.get(freq, timedelta(weeks=1))
        return (now + delta).isoformat()
