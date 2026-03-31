"""Async wrapper that adds database persistence to the in-memory ReviewStore.

Read path: delegates to sync ReviewStore (fast, in-memory pandas).
Write path: writes to both in-memory store AND PostgreSQL.
If session_factory is None, operates in memory-only mode (graceful degradation).
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.data.review_store import ReviewStore

logger = logging.getLogger(__name__)


class AsyncReviewStore:
    """Dual-write review store: in-memory DataFrame + PostgreSQL persistence."""

    def __init__(
        self,
        store: ReviewStore,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        self._store = store
        self._session_factory = session_factory
        self._db_available = session_factory is not None

    # --- Read methods (sync, delegate to inner store) ---

    def get_review_queue(self, **kwargs: Any) -> Any:
        return self._store.get_review_queue(**kwargs)

    def get_review_stats(self) -> Any:
        return self._store.get_review_stats()

    def get_approval_queue(self, **kwargs: Any) -> Any:
        return self._store.get_approval_queue(**kwargs)

    def get_approval_stats(self) -> Any:
        return self._store.get_approval_stats()

    # --- Write methods (async, dual-write) ---

    async def submit_review_action(
        self,
        variance_id: str,
        action: str,
        edited_narrative: Optional[str] = None,
        hypothesis_feedback: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> dict[str, str]:
        """Submit review action: update in-memory + persist to DB."""
        # 1. In-memory update (fast, always works)
        result = self._store.submit_review_action(
            variance_id=variance_id,
            action=action,
            edited_narrative=edited_narrative,
            hypothesis_feedback=hypothesis_feedback,
            comment=comment,
        )

        # 2. Database persistence (async, graceful failure)
        if self._db_available:
            await self._persist_review_action(
                variance_id=variance_id,
                new_status=result.get("new_status", ""),
                edited_narrative=edited_narrative,
                hypothesis_feedback=hypothesis_feedback,
                comment=comment,
            )

        return result

    async def submit_bulk_approval(
        self,
        variance_ids: list[str],
        action: str = "director_approve",
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        """Bulk approval: update in-memory + persist each to DB."""
        result = self._store.submit_bulk_approval(
            variance_ids=variance_ids,
            action=action,
            comment=comment,
        )

        # Persist each approval
        if self._db_available:
            for vid in variance_ids:
                await self._persist_review_action(
                    variance_id=vid,
                    new_status="APPROVED",
                    comment=comment,
                )

        return result

    async def _persist_review_action(
        self,
        variance_id: str,
        new_status: str,
        edited_narrative: Optional[str] = None,
        hypothesis_feedback: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> None:
        """Persist a single review action to PostgreSQL."""
        try:
            from shared.database.models import ReviewStatusRecord

            async with self._session_factory() as session:
                async with session.begin():
                    stmt = select(ReviewStatusRecord).where(
                        ReviewStatusRecord.variance_id == variance_id
                    )
                    record = (await session.execute(stmt)).scalar_one_or_none()
                    if not record:
                        logger.warning("Variance %s not found in database", variance_id)
                        return

                    record.status = new_status
                    now = datetime.datetime.now(datetime.timezone.utc)

                    if new_status == "ANALYST_REVIEWED":
                        record.reviewed_at = now
                        record.reviewer = "analyst"
                    elif new_status == "APPROVED":
                        record.approved_at = now
                        record.approver = "director"

                    if edited_narrative:
                        record.edited_narrative = edited_narrative
                    if hypothesis_feedback:
                        record.hypothesis_feedback = {"value": hypothesis_feedback}
                    if comment:
                        record.review_notes = comment

        except Exception as exc:
            logger.warning("Failed to persist review action to DB: %s", exc)
            # Don't raise -- in-memory update already succeeded
