"""Unit tests for narrative version history table and model.

Validates the NarrativeVersionRecord model, ReviewStatusRecord
new columns (version_count, locked_by, period_id, fiscal_year),
and the append-only version tracking behavior.
"""

import pytest
import pytest_asyncio
from datetime import datetime, UTC, timedelta

from shared.database.models import NarrativeVersionRecord, ReviewStatusRecord


@pytest_asyncio.fixture
async def db_session_factory():
    """In-memory SQLite DB with all tables including version history."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from shared.database.models import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield sf
    await engine.dispose()


@pytest.mark.asyncio
class TestNarrativeVersionRecord:
    """Tests for the version history table."""

    async def test_create_version_entry(self, db_session_factory):
        """Can create a version history entry."""
        async with db_session_factory() as session:
            async with session.begin():
                entry = NarrativeVersionRecord(
                    variance_id="abc123",
                    entity_type="variance",
                    version_number=1,
                    narrative_text="AI-generated narrative for revenue.",
                    changed_by="engine",
                    change_type="ai_generated",
                )
                session.add(entry)

        async with db_session_factory() as session:
            from sqlalchemy import select
            result = await session.scalars(
                select(NarrativeVersionRecord).where(
                    NarrativeVersionRecord.variance_id == "abc123"
                )
            )
            rows = result.all()
            assert len(rows) == 1
            assert rows[0].version_number == 1
            assert rows[0].change_type == "ai_generated"

    async def test_append_multiple_versions(self, db_session_factory):
        """Can append multiple versions for the same variance."""
        async with db_session_factory() as session:
            async with session.begin():
                for v in range(1, 4):
                    session.add(NarrativeVersionRecord(
                        variance_id="def456",
                        entity_type="variance",
                        version_number=v,
                        narrative_text=f"Version {v} text",
                        changed_by="engine" if v == 1 else "analyst-001",
                        change_type="ai_generated" if v == 1 else "analyst_edit",
                        change_reason=None if v == 1 else "added_context",
                    ))

        async with db_session_factory() as session:
            from sqlalchemy import select, func
            count = await session.scalar(
                select(func.count()).select_from(NarrativeVersionRecord).where(
                    NarrativeVersionRecord.variance_id == "def456"
                )
            )
            assert count == 3

    async def test_version_has_change_reason(self, db_session_factory):
        """Edit versions should include change_reason."""
        async with db_session_factory() as session:
            async with session.begin():
                session.add(NarrativeVersionRecord(
                    variance_id="ghi789",
                    entity_type="variance",
                    version_number=2,
                    narrative_text="Corrected narrative.",
                    changed_by="analyst-001",
                    change_type="analyst_edit",
                    change_reason="factual_correction",
                ))

        async with db_session_factory() as session:
            from sqlalchemy import select
            result = await session.scalar(
                select(NarrativeVersionRecord).where(
                    NarrativeVersionRecord.variance_id == "ghi789"
                )
            )
            assert result.change_reason == "factual_correction"


@pytest.mark.asyncio
class TestReviewStatusNewColumns:
    """Tests for new columns on ReviewStatusRecord."""

    async def test_version_count_column(self, db_session_factory):
        """ReviewStatusRecord has version_count column."""
        async with db_session_factory() as session:
            async with session.begin():
                record = ReviewStatusRecord(
                    variance_id="test-version-count",
                    status="AI_DRAFT",
                    version_count=1,
                )
                session.add(record)

        async with db_session_factory() as session:
            from sqlalchemy import select
            r = await session.scalar(
                select(ReviewStatusRecord).where(ReviewStatusRecord.variance_id == "test-version-count")
            )
            assert r.version_count == 1

    async def test_locked_by_columns(self, db_session_factory):
        """ReviewStatusRecord has locked_by and locked_until columns."""
        now = datetime.now(UTC)
        async with db_session_factory() as session:
            async with session.begin():
                record = ReviewStatusRecord(
                    variance_id="test-locking",
                    status="AI_DRAFT",
                    locked_by="analyst-001",
                    locked_until=now + timedelta(minutes=30),
                )
                session.add(record)

        async with db_session_factory() as session:
            from sqlalchemy import select
            r = await session.scalar(
                select(ReviewStatusRecord).where(ReviewStatusRecord.variance_id == "test-locking")
            )
            assert r.locked_by == "analyst-001"
            assert r.locked_until is not None

    async def test_period_and_fiscal_year_columns(self, db_session_factory):
        """ReviewStatusRecord has period_id and fiscal_year columns."""
        async with db_session_factory() as session:
            async with session.begin():
                record = ReviewStatusRecord(
                    variance_id="test-period",
                    status="AI_DRAFT",
                    period_id="2026-05",
                    fiscal_year=2026,
                )
                session.add(record)

        async with db_session_factory() as session:
            from sqlalchemy import select
            r = await session.scalar(
                select(ReviewStatusRecord).where(ReviewStatusRecord.variance_id == "test-period")
            )
            assert r.period_id == "2026-05"
            assert r.fiscal_year == 2026
