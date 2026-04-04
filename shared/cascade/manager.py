"""Cascade Manager — debounced auto-cascade on narrative edits.

Manages the lifecycle of cascade regeneration:
- Receives events when narratives are edited/approved
- Debounces rapid edits (60s window per period)
- Executes cascade via CascadeRegenerator
- Tracks pending cascades and history

In-process asyncio implementation (no external task queue).

Usage::

    manager = CascadeManager(data_service, graph)

    # Auto-triggered by review workflow
    await manager.on_narrative_changed("v_leaf_001", "2026-06")
    # → debounces 60s, then runs cascade

    # Manual trigger (skip debounce)
    result = await manager.execute_now("v_leaf_001", "2026-06")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from shared.cascade.regenerator import CascadeRegenerator, CascadeResult

logger = logging.getLogger("cascade.manager")

# Default debounce window in seconds
DEFAULT_DEBOUNCE_SECONDS = 60

# Max history entries to keep
MAX_HISTORY = 50


class CascadeManager:
    """Manages debounced cascade regeneration.

    When a narrative is edited, schedules a cascade after a debounce
    window. If another edit arrives within the window, the timer resets.
    Only one cascade runs per period at a time.

    Args:
        data_service: DataService instance for data access.
        graph: VarianceGraph instance (or None — will use DataService.get_graph).
        llm_client: Optional LLM client for narrative generation.
        debounce_seconds: Debounce window (default 60s).
    """

    def __init__(
        self,
        data_service: Any,
        graph: Any = None,
        llm_client: Any = None,
        debounce_seconds: int = DEFAULT_DEBOUNCE_SECONDS,
    ) -> None:
        self._ds = data_service
        self._graph = graph
        self._llm_client = llm_client
        self._debounce_seconds = debounce_seconds
        self._pending: dict[str, asyncio.Task] = {}  # period_id → debounce task
        self._pending_triggers: dict[str, str] = {}  # period_id → trigger variance_id
        self._history: list[CascadeResult] = []
        self._running: set[str] = set()  # period_ids currently running

    def _get_regenerator(self, period_id: str) -> CascadeRegenerator:
        """Create a CascadeRegenerator for the given period."""
        graph = self._graph or self._ds.get_graph(period_id)
        return CascadeRegenerator(self._ds, graph, self._llm_client)

    async def on_narrative_changed(
        self, variance_id: str, period_id: str
    ) -> None:
        """Called when a narrative is edited or approved.

        Debounces: if another edit arrives within the window,
        the timer resets. Only the last trigger variance_id is used.

        Args:
            variance_id: The variance that was edited.
            period_id: The period of the variance.
        """
        key = period_id

        # Cancel existing pending task for this period
        if key in self._pending:
            self._pending[key].cancel()
            logger.debug(
                "Cascade debounce reset for period %s (new trigger: %s)",
                period_id, variance_id,
            )

        self._pending_triggers[key] = variance_id

        # Schedule new debounced cascade
        task = asyncio.create_task(
            self._debounced_cascade(variance_id, period_id)
        )
        self._pending[key] = task

        logger.info(
            "Cascade scheduled for period %s in %ds (trigger: %s)",
            period_id, self._debounce_seconds, variance_id,
        )

    async def _debounced_cascade(
        self, variance_id: str, period_id: str
    ) -> None:
        """Wait for debounce window, then execute cascade."""
        try:
            await asyncio.sleep(self._debounce_seconds)
        except asyncio.CancelledError:
            return  # Another edit arrived, this task was cancelled

        key = period_id
        # Use the most recent trigger variance_id
        trigger_vid = self._pending_triggers.pop(key, variance_id)
        self._pending.pop(key, None)

        # Don't run if another cascade is already running for this period
        if key in self._running:
            logger.warning(
                "Cascade already running for period %s — skipping",
                period_id,
            )
            return

        self._running.add(key)
        try:
            regen = self._get_regenerator(period_id)
            result = await regen.regenerate_chain(trigger_vid, period_id)
            self._add_to_history(result)
            logger.info(
                "Cascade %s completed: %d regenerated, %.1f s",
                result.cascade_id,
                len(result.regenerated),
                result.total_seconds,
            )
        except Exception:
            logger.exception("Cascade failed for period %s", period_id)
        finally:
            self._running.discard(key)

    async def execute_now(
        self,
        variance_id: str,
        period_id: str,
    ) -> CascadeResult:
        """Execute cascade immediately, skipping debounce.

        Used for manual triggers (e.g. from API endpoint).

        Args:
            variance_id: The variance to cascade from.
            period_id: The period.

        Returns:
            CascadeResult with audit trail.
        """
        # Cancel any pending debounced cascade for this period
        key = period_id
        if key in self._pending:
            self._pending[key].cancel()
            self._pending.pop(key, None)
            self._pending_triggers.pop(key, None)

        regen = self._get_regenerator(period_id)
        result = await regen.regenerate_chain(variance_id, period_id)
        self._add_to_history(result)
        return result

    def get_pending(self) -> list[dict[str, str]]:
        """Return list of pending (debouncing) cascades.

        Returns:
            List of dicts with period_id and trigger_variance_id.
        """
        return [
            {
                "period_id": pid,
                "trigger_variance_id": self._pending_triggers.get(pid, ""),
                "status": "debouncing",
            }
            for pid in self._pending
        ]

    def get_running(self) -> list[str]:
        """Return period_ids with currently running cascades."""
        return list(self._running)

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent cascade results.

        Args:
            limit: Max results to return (default 10).

        Returns:
            List of cascade result dicts (most recent first).
        """
        recent = self._history[-limit:]
        recent.reverse()
        return [
            {
                "cascade_id": r.cascade_id,
                "trigger_variance_id": r.trigger_variance_id,
                "period_id": r.period_id,
                "regenerated_count": len(r.regenerated),
                "skipped_count": len(r.skipped),
                "error_count": len(r.errors),
                "total_seconds": r.total_seconds,
            }
            for r in recent
        ]

    def _add_to_history(self, result: CascadeResult) -> None:
        """Add a cascade result to history, trimming if needed."""
        self._history.append(result)
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
