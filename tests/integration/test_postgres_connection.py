"""PostgreSQL integration tests.

Verifies real database connection, table creation, seeding,
and basic CRUD operations. Skips if PostgreSQL is not available.
"""

import os

import pytest
import pytest_asyncio

# Skip entire module if PostgreSQL is not reachable
pytestmark = [
    pytest.mark.integration,
]


def _postgres_available() -> bool:
    """Check if PostgreSQL is reachable."""
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine

        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/variance_agent",
        )
        if "sqlite" in url:
            return False

        engine = create_async_engine(url, pool_pre_ping=True)

        async def _check():
            try:
                async with engine.connect() as conn:
                    await conn.execute(
                        __import__("sqlalchemy").text("SELECT 1")
                    )
                return True
            except Exception:
                return False
            finally:
                await engine.dispose()

        return asyncio.get_event_loop().run_until_complete(_check())
    except Exception:
        return False


POSTGRES_AVAILABLE = _postgres_available()
skip_no_postgres = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL not available at localhost:5432",
)


@skip_no_postgres
@pytest.mark.asyncio
class TestPostgresConnection:
    """Tests that require a real PostgreSQL instance."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_db(self):
        """Initialize engine and create tables."""
        from shared.database.engine import init_engine, init_db, get_session_factory, dispose_engine

        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/variance_agent",
        )
        init_engine(url)
        await init_db()
        self.session_factory = get_session_factory()
        yield
        await dispose_engine()

    async def test_tables_created(self):
        """All expected tables exist after init_db."""
        from sqlalchemy import inspect, text

        async with self.session_factory() as session:
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = {row[0] for row in result.fetchall()}

        expected = {
            "users", "roles", "user_roles", "permissions",
            "review_status", "audit_log", "conversations",
            "chat_messages", "knowledge_commentary",
        }
        for table in expected:
            assert table in tables, f"Table '{table}' not found in PostgreSQL"

    async def test_seed_roles(self):
        """System roles are seeded correctly."""
        from shared.database.seed import seed_roles_and_permissions
        from shared.database.models import RoleRecord
        from sqlalchemy import select, func

        await seed_roles_and_permissions(self.session_factory)

        async with self.session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(RoleRecord)
            )
            assert count >= 7, f"Expected >= 7 roles, got {count}"

    async def test_seed_demo_users(self):
        """Demo users are seeded correctly."""
        from shared.database.seed import seed_roles_and_permissions, seed_demo_users
        from shared.database.models import UserRecord
        from sqlalchemy import select, func

        await seed_roles_and_permissions(self.session_factory)
        await seed_demo_users(self.session_factory)

        async with self.session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(UserRecord)
            )
            assert count >= 6, f"Expected >= 6 users, got {count}"

    async def test_user_store_crud(self):
        """UserStore CRUD works against real PostgreSQL."""
        from shared.database.seed import seed_roles_and_permissions, seed_demo_users
        from shared.auth.user_store import UserStore

        await seed_roles_and_permissions(self.session_factory)
        await seed_demo_users(self.session_factory)

        store = UserStore(self.session_factory)

        # Verify demo user exists
        user = await store.get_user_by_email("admin@variance-agent.dev")
        assert user is not None
        assert user.display_name == "System Admin"

        # Verify roles
        roles = await store.get_user_roles(user.user_id)
        role_names = [r["role_name"] for r in roles]
        assert "admin" in role_names

    async def test_login_flow_against_postgres(self):
        """Full login flow works against real PostgreSQL."""
        from shared.database.seed import seed_roles_and_permissions, seed_demo_users
        from shared.auth.user_store import UserStore
        from shared.auth.jwt import JWTService

        await seed_roles_and_permissions(self.session_factory)
        await seed_demo_users(self.session_factory)

        store = UserStore(self.session_factory)
        jwt = JWTService(secret_key="postgres-test-secret")

        # Login with demo credentials
        user = await store.verify_password("analyst@variance-agent.dev", "password123")
        assert user is not None

        # Issue token
        token = jwt.create_access_token(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            roles=user.role_names,
            bu_scope=user.bu_scope,
            persona=user.persona,
        )

        # Decode and verify
        payload = jwt.decode_token(token)
        assert payload.email == "analyst@variance-agent.dev"
        assert "analyst" in payload.roles
