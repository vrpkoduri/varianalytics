"""Database query performance benchmark tests.

Validates that UserStore queries respond within SLA thresholds.
Uses in-memory SQLite with seeded data for consistent benchmarks.

SLAs:
- Single user lookup: < 50ms
- Role query: < 50ms
- User list (100): < 100ms
- Role assignment: < 50ms
"""

import asyncio
import time

import pytest
import pytest_asyncio

from shared.auth.user_store import UserStore


@pytest_asyncio.fixture(scope="module")
async def seeded_store():
    """In-memory SQLite DB with seeded auth tables."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from shared.database.models import Base
    from shared.database.seed import seed_roles_and_permissions, seed_demo_users

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_roles_and_permissions(sf)
    await seed_demo_users(sf)

    store = UserStore(sf)
    yield store
    await engine.dispose()


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabaseQueryPerformance:
    """Database query SLA tests."""

    async def test_user_lookup_under_50ms(self, seeded_store: UserStore):
        """Single user lookup by email completes in < 50ms."""
        start = time.monotonic()
        user = await seeded_store.get_user_by_email("analyst@variance-agent.dev")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert user is not None, "User not found"
        assert elapsed_ms < 50, f"User lookup took {elapsed_ms:.1f}ms (SLA: <50ms)"

    async def test_role_query_under_50ms(self, seeded_store: UserStore):
        """User role query completes in < 50ms."""
        start = time.monotonic()
        roles = await seeded_store.get_user_roles("analyst-001")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert len(roles) > 0, "No roles found"
        assert elapsed_ms < 50, f"Role query took {elapsed_ms:.1f}ms (SLA: <50ms)"

    async def test_user_list_under_100ms(self, seeded_store: UserStore):
        """User list query (100 limit) completes in < 100ms."""
        start = time.monotonic()
        users = await seeded_store.list_users(limit=100)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert len(users) >= 6, "Expected at least 6 demo users"
        assert elapsed_ms < 100, f"User list took {elapsed_ms:.1f}ms (SLA: <100ms)"

    async def test_role_assignment_under_50ms(self, seeded_store: UserStore):
        """Role assignment completes in < 50ms."""
        # Create a test user first
        user = await seeded_store.create_user(
            email="perf-test@example.com",
            display_name="Perf Test",
            password="test123",
        )
        start = time.monotonic()
        result = await seeded_store.assign_role(user.user_id, "director")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert result is True, "Role assignment failed"
        assert elapsed_ms < 50, f"Role assignment took {elapsed_ms:.1f}ms (SLA: <50ms)"
