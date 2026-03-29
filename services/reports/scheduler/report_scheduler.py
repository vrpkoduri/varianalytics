"""Report scheduler.

Manages periodic and event-driven report generation triggers.
Evaluates configured schedules, resolves the target period, and
enqueues generation jobs via the reports API.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Evaluate and execute report schedules.

    Responsible for:
    - Polling active schedules on a configurable tick interval.
    - Resolving ``period_key_pattern`` to the concrete target period.
    - Enqueuing report generation jobs (delegates to report generators).
    - Recording last/next run timestamps.
    - Handling failures with retry and alerting.
    """

    def __init__(self) -> None:
        self._running: bool = False

    async def start(self) -> None:
        """Start the scheduler loop."""
        logger.info("Report scheduler started.")
        self._running = True
        # TODO: implement tick loop

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        logger.info("Report scheduler stopping.")
        self._running = False

    async def evaluate_schedules(self) -> list[dict[str, Any]]:
        """Check all active schedules and enqueue due jobs.

        Returns:
            List of enqueued job descriptors.
        """
        # TODO: query schedules, compare next_run_at, enqueue
        return []
