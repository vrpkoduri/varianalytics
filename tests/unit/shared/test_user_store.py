"""Unit tests for UserStore (shared/auth/user_store.py).

Tests user CRUD, role assignment, password verification,
and BU scope merging using an in-memory SQLite database.
"""

import pytest
import pytest_asyncio

from shared.auth.user_store import UserStore, _hash_password, _verify_password


# ---------------------------------------------------------------------------
# Fixtures: in-memory SQLite database
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session_factory():
    """Create an in-memory SQLite database with auth tables."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from shared.database.models import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed system roles
    from shared.database.seed import seed_roles_and_permissions
    await seed_roles_and_permissions(session_factory)

    yield session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def user_store(db_session_factory) -> UserStore:
    """Create a UserStore backed by the test database."""
    return UserStore(db_session_factory)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    """Tests for password hash/verify utilities."""

    def test_hash_produces_hex_string(self):
        """Hash is a 64-char hex string (SHA-256)."""
        h = _hash_password("test123")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_same_password_same_hash(self):
        """Same password produces same hash (deterministic)."""
        assert _hash_password("test123") == _hash_password("test123")

    def test_different_password_different_hash(self):
        """Different passwords produce different hashes."""
        assert _hash_password("test123") != _hash_password("test456")

    def test_verify_correct_password(self):
        """Correct password verifies successfully."""
        h = _hash_password("mypassword")
        assert _verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        """Wrong password fails verification."""
        h = _hash_password("mypassword")
        assert _verify_password("wrongpassword", h) is False


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUserCRUD:
    """Tests for user create/read/update/deactivate."""

    async def test_create_user(self, user_store: UserStore):
        """Create a user and retrieve by ID."""
        user = await user_store.create_user(
            email="test@example.com",
            display_name="Test User",
            password="password123",
        )
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.user_id  # auto-generated

    async def test_get_user_by_email(self, user_store: UserStore):
        """Retrieve user by email."""
        await user_store.create_user(
            email="findme@example.com",
            display_name="Find Me",
            password="password123",
        )
        found = await user_store.get_user_by_email("findme@example.com")
        assert found is not None
        assert found.display_name == "Find Me"

    async def test_get_nonexistent_user(self, user_store: UserStore):
        """Nonexistent user returns None."""
        found = await user_store.get_user_by_id("nonexistent-id")
        assert found is None

    async def test_duplicate_email_raises(self, user_store: UserStore):
        """Creating a user with duplicate email raises ValueError."""
        await user_store.create_user(email="dup@example.com", display_name="First", password="pass")
        with pytest.raises(ValueError, match="already exists"):
            await user_store.create_user(email="dup@example.com", display_name="Second", password="pass")

    async def test_update_user_display_name(self, user_store: UserStore):
        """Update user's display name."""
        user = await user_store.create_user(email="update@example.com", display_name="Old Name", password="pass")
        updated = await user_store.update_user(user.user_id, display_name="New Name")
        assert updated is not None
        assert updated.display_name == "New Name"

    async def test_deactivate_user(self, user_store: UserStore):
        """Deactivated user is no longer active."""
        user = await user_store.create_user(email="deact@example.com", display_name="Deactivate Me", password="pass")
        result = await user_store.deactivate_user(user.user_id)
        assert result is True
        deactivated = await user_store.get_user_by_id(user.user_id)
        assert deactivated is not None
        assert deactivated.is_active is False

    async def test_verify_password_correct(self, user_store: UserStore):
        """Correct password returns user."""
        await user_store.create_user(email="auth@example.com", display_name="Auth User", password="secret123")
        user = await user_store.verify_password("auth@example.com", "secret123")
        assert user is not None
        assert user.email == "auth@example.com"

    async def test_verify_password_wrong(self, user_store: UserStore):
        """Wrong password returns None."""
        await user_store.create_user(email="authwrong@example.com", display_name="Wrong", password="secret123")
        user = await user_store.verify_password("authwrong@example.com", "wrongpassword")
        assert user is None

    async def test_list_users(self, user_store: UserStore):
        """List users returns created users."""
        await user_store.create_user(email="list1@example.com", display_name="User 1", password="pass")
        await user_store.create_user(email="list2@example.com", display_name="User 2", password="pass")
        users = await user_store.list_users()
        emails = {u.email for u in users}
        assert "list1@example.com" in emails
        assert "list2@example.com" in emails


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRoleManagement:
    """Tests for role assignment and removal."""

    async def test_assign_role(self, user_store: UserStore):
        """Assign a role to a user."""
        user = await user_store.create_user(email="role@example.com", display_name="Role User", password="pass")
        assigned = await user_store.assign_role(user.user_id, "analyst")
        assert assigned is True

        roles = await user_store.get_user_roles(user.user_id)
        role_names = [r["role_name"] for r in roles]
        assert "analyst" in role_names

    async def test_assign_nonexistent_role(self, user_store: UserStore):
        """Assigning a nonexistent role returns False."""
        user = await user_store.create_user(email="norole@example.com", display_name="No Role", password="pass")
        result = await user_store.assign_role(user.user_id, "nonexistent_role")
        assert result is False

    async def test_duplicate_role_assignment(self, user_store: UserStore):
        """Assigning the same role twice returns False."""
        user = await user_store.create_user(email="dup_role@example.com", display_name="Dup Role", password="pass")
        await user_store.assign_role(user.user_id, "analyst")
        result = await user_store.assign_role(user.user_id, "analyst")
        assert result is False

    async def test_remove_role(self, user_store: UserStore):
        """Remove a role from a user."""
        user = await user_store.create_user(email="remove_role@example.com", display_name="Remove Role", password="pass")
        await user_store.assign_role(user.user_id, "analyst")
        removed = await user_store.remove_role(user.user_id, "analyst")
        assert removed is True

        roles = await user_store.get_user_roles(user.user_id)
        assert len(roles) == 0

    async def test_bu_scope_in_role(self, user_store: UserStore):
        """Role assignment preserves BU scope."""
        user = await user_store.create_user(email="bu_scope@example.com", display_name="BU Scope", password="pass")
        await user_store.assign_role(user.user_id, "bu_leader", bu_scope=["BU001"])

        roles = await user_store.get_user_roles(user.user_id)
        assert roles[0]["bu_scope"] == ["BU001"]

    async def test_get_user_bu_scope_merged(self, user_store: UserStore):
        """Merged BU scope across multiple roles."""
        user = await user_store.create_user(email="merge@example.com", display_name="Merge", password="pass")
        await user_store.assign_role(user.user_id, "analyst", bu_scope=["BU001"])
        await user_store.assign_role(user.user_id, "bu_leader", bu_scope=["BU002"])

        scope = await user_store.get_user_bu_scope(user.user_id)
        assert "BU001" in scope
        assert "BU002" in scope

    async def test_all_scope_trumps_specific(self, user_store: UserStore):
        """If any role has ALL scope, merged scope is ALL."""
        user = await user_store.create_user(email="all_scope@example.com", display_name="All Scope", password="pass")
        await user_store.assign_role(user.user_id, "analyst", bu_scope=["ALL"])
        await user_store.assign_role(user.user_id, "bu_leader", bu_scope=["BU001"])

        scope = await user_store.get_user_bu_scope(user.user_id)
        assert scope == ["ALL"]


# ---------------------------------------------------------------------------
# Role listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRoleListing:
    """Tests for role listing."""

    async def test_list_system_roles(self, user_store: UserStore):
        """System roles are seeded and listable."""
        roles = await user_store.list_roles()
        role_names = {r["role_name"] for r in roles}
        assert "admin" in role_names
        assert "analyst" in role_names
        assert "cfo" in role_names
        assert "director" in role_names
        assert "bu_leader" in role_names
        assert "board_viewer" in role_names
        assert "hr_finance" in role_names

    async def test_get_role_by_name(self, user_store: UserStore):
        """Get a specific role by name."""
        role = await user_store.get_role("analyst")
        assert role is not None
        assert role["role_name"] == "analyst"
        assert role["persona_type"] == "analyst"
        assert role["is_system"] is True
