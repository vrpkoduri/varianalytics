"""Seed mutable database tables from parquet files on first boot.

Only inserts data when the target table is empty, making it safe to call
on every startup.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database.models import ReviewStatusRecord

logger = logging.getLogger(__name__)


async def seed_review_status(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str = "data/output",
) -> int:
    """Seed the ``review_status`` table from ``fact_review_status.parquet``.

    Only inserts when the table is empty.

    Args:
        session_factory: Async session maker bound to the target database.
        data_dir: Directory containing the parquet output files.

    Returns:
        Number of rows seeded (0 if the table already had data or the file
        was not found).
    """
    parquet_path = Path(data_dir) / "fact_review_status.parquet"

    if not parquet_path.exists():
        logger.warning("Parquet file not found at %s — skipping review_status seed.", parquet_path)
        return 0

    async with session_factory() as session:
        row_count = await session.scalar(select(func.count()).select_from(ReviewStatusRecord))
        if row_count and row_count > 0:
            logger.info("review_status table already has %d rows — skipping seed.", row_count)
            return 0

    # Read parquet — pandas is already a project dependency
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    logger.info("Loaded %d rows from %s", len(df), parquet_path)

    # Map parquet columns to model fields.
    # The parquet schema may use slightly different names; normalise here.
    column_map = {
        "variance_id": "variance_id",
        "status": "status",
        "assigned_analyst": "assigned_analyst",
        "reviewer": "reviewer",
        "approver": "approver",
        "original_narrative": "original_narrative",
        "edited_narrative": "edited_narrative",
        "edit_diff": "edit_diff",
        "hypothesis_feedback": "hypothesis_feedback",
        "review_notes": "review_notes",
        "created_at": "created_at",
        "reviewed_at": "reviewed_at",
        "approved_at": "approved_at",
    }

    records: list[ReviewStatusRecord] = []
    for _, row in df.iterrows():
        kwargs = {}
        for parquet_col, model_field in column_map.items():
            if parquet_col in df.columns:
                value = row[parquet_col]
                # Convert NaN / NaT to None
                if pd.isna(value) if not isinstance(value, dict) else False:
                    value = None
                kwargs[model_field] = value
        records.append(ReviewStatusRecord(**kwargs))

    async with session_factory() as session:
        async with session.begin():
            session.add_all(records)

    logger.info("Seeded %d rows into review_status.", len(records))
    return len(records)
