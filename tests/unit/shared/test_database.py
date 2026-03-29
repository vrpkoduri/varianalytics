"""Unit tests for the shared database layer.

Uses SQLite (aiosqlite) as an in-memory backend so no PostgreSQL is needed.
"""

from __future__ import annotations

import datetime
import uuid

import pytest
import pytest_asyncio

from shared.database.engine import (
    dispose_engine,
    get_engine,
    get_session_factory,
    init_db,
    init_engine,
)
from shared.database.models import (
    AuditLogRecord,
    Base,
    ChatMessageRecord,
    ConversationRecord,
    ReviewStatusRecord,
)

SQLITE_URL = "sqlite+aiosqlite://"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def _setup_teardown():
    """Initialise a fresh in-memory SQLite engine before each test."""
    init_engine(SQLITE_URL, echo=False)
    await init_db()
    yield
    await dispose_engine()


# ---------------------------------------------------------------------------
# Model creation tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_review_status_model_creation():
    """Create a ReviewStatusRecord, persist it, and read it back."""
    factory = get_session_factory()
    vid = f"VAR-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        async with session.begin():
            record = ReviewStatusRecord(
                variance_id=vid,
                status="AI_DRAFT",
                assigned_analyst="analyst@co.com",
                original_narrative="Revenue rose 12% due to volume.",
                hypothesis_feedback={"thumbs_up": True},
            )
            session.add(record)

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(ReviewStatusRecord).where(ReviewStatusRecord.variance_id == vid)
        )
        row = result.scalar_one()

        assert row.variance_id == vid
        assert row.status == "AI_DRAFT"
        assert row.assigned_analyst == "analyst@co.com"
        assert row.original_narrative == "Revenue rose 12% due to volume."
        assert row.hypothesis_feedback == {"thumbs_up": True}
        assert row.reviewer is None
        assert row.approved_at is None
        assert isinstance(row.id, int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_model_creation():
    """Create a ConversationRecord, persist it, and read it back."""
    factory = get_session_factory()
    cid = f"conv-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        async with session.begin():
            record = ConversationRecord(
                conversation_id=cid,
                user_id="user-001",
                title="Q4 Revenue Discussion",
            )
            session.add(record)

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(ConversationRecord).where(ConversationRecord.conversation_id == cid)
        )
        row = result.scalar_one()

        assert row.conversation_id == cid
        assert row.user_id == "user-001"
        assert row.title == "Q4 Revenue Discussion"
        assert isinstance(row.id, int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_message_model_creation():
    """Create a ChatMessageRecord, persist it, and read it back."""
    factory = get_session_factory()
    cid = f"conv-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        async with session.begin():
            session.add(ConversationRecord(conversation_id=cid, user_id="user-001"))
            session.add(
                ChatMessageRecord(
                    conversation_id=cid,
                    role="user",
                    content="Why did COGS spike in March?",
                    metadata_json={"tokens": 12},
                )
            )

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(ChatMessageRecord).where(ChatMessageRecord.conversation_id == cid)
        )
        row = result.scalar_one()

        assert row.role == "user"
        assert row.content == "Why did COGS spike in March?"
        assert row.metadata_json == {"tokens": 12}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audit_log_model_creation():
    """Create an AuditLogRecord, persist it, and read it back."""
    factory = get_session_factory()
    aid = f"audit-{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        async with session.begin():
            record = AuditLogRecord(
                audit_id=aid,
                event_type="engine_run",
                user_id="system",
                service="computation",
                action="run_passes",
                details={"passes": 5, "duration_s": 3.2},
                ip_address="127.0.0.1",
            )
            session.add(record)

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(AuditLogRecord).where(AuditLogRecord.audit_id == aid)
        )
        row = result.scalar_one()

        assert row.audit_id == aid
        assert row.event_type == "engine_run"
        assert row.service == "computation"
        assert row.details["passes"] == 5
        assert row.ip_address == "127.0.0.1"


# ---------------------------------------------------------------------------
# Engine / infrastructure tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_engine_sqlite():
    """Verify that the engine is properly initialised with SQLite."""
    engine = get_engine()
    assert engine is not None
    assert "sqlite" in str(engine.url)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """Verify that init_db creates all expected tables."""
    engine = get_engine()

    from sqlalchemy import inspect as sa_inspect

    async with engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: sa_inspect(sync_conn).get_table_names()
        )

    expected = {"review_status", "conversations", "chat_messages", "audit_log"}
    assert expected.issubset(set(table_names)), f"Missing tables: {expected - set(table_names)}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_engine_raises_before_init():
    """get_engine should raise RuntimeError when engine is not initialised."""
    await dispose_engine()

    with pytest.raises(RuntimeError, match="not initialised"):
        get_engine()

    # Re-init for autouse teardown
    init_engine(SQLITE_URL)
    await init_db()


# ---------------------------------------------------------------------------
# Seed test
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_review_status(tmp_path):
    """seed_review_status should populate the table from a parquet file."""
    import pandas as pd

    from shared.database.seed import seed_review_status

    # Create a small parquet file
    df = pd.DataFrame(
        {
            "variance_id": ["VAR-001", "VAR-002", "VAR-003"],
            "status": ["AI_DRAFT", "ANALYST_REVIEWED", "APPROVED"],
            "assigned_analyst": ["alice@co.com", "bob@co.com", None],
            "reviewer": [None, "bob@co.com", "carol@co.com"],
            "approver": [None, None, "dave@co.com"],
            "original_narrative": ["Rev up", "COGS flat", "OpEx down"],
            "edited_narrative": [None, "COGS stable", "OpEx decreased"],
            "edit_diff": [None, "flat->stable", None],
            "hypothesis_feedback": [None, None, None],
            "review_notes": [None, "Looks good", "Approved for Q4"],
            "created_at": pd.Timestamp("2024-01-15"),
            "reviewed_at": [pd.NaT, pd.Timestamp("2024-01-16"), pd.Timestamp("2024-01-16")],
            "approved_at": [pd.NaT, pd.NaT, pd.Timestamp("2024-01-17")],
        }
    )
    parquet_path = tmp_path / "fact_review_status.parquet"
    df.to_parquet(parquet_path)

    factory = get_session_factory()

    # First call should seed
    count = await seed_review_status(factory, data_dir=str(tmp_path))
    assert count == 3

    # Second call should be a no-op
    count2 = await seed_review_status(factory, data_dir=str(tmp_path))
    assert count2 == 0

    # Verify data
    from sqlalchemy import select

    async with factory() as session:
        result = await session.execute(
            select(ReviewStatusRecord).order_by(ReviewStatusRecord.variance_id)
        )
        rows = result.scalars().all()

    assert len(rows) == 3
    assert rows[0].variance_id == "VAR-001"
    assert rows[1].status == "ANALYST_REVIEWED"
    assert rows[2].approver == "dave@co.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_review_status_missing_file(tmp_path):
    """seed_review_status returns 0 when the parquet file does not exist."""
    from shared.database.seed import seed_review_status

    factory = get_session_factory()
    count = await seed_review_status(factory, data_dir=str(tmp_path / "nonexistent"))
    assert count == 0
