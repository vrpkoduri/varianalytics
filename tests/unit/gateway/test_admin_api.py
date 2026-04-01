"""Unit tests for admin API endpoints (services/gateway/api/admin.py).

Tests user CRUD, role management, and audit log endpoints
using FastAPI TestClient with an in-memory SQLite database.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from shared.auth.jwt import JWTService


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key="admin-api-test-secret")


@pytest_asyncio.fixture
async def db_session_factory():
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

    yield sf
    await engine.dispose()


@pytest.fixture
def app_client(jwt_service, db_session_factory):
    """FastAPI TestClient with admin API wired up."""
    from fastapi import FastAPI
    from services.gateway.api.admin import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    app.state.jwt_service = jwt_service
    app.state.environment = "production"

    from shared.auth.user_store import UserStore
    app.state.user_store = UserStore(db_session_factory)

    return TestClient(app)


def _admin_token(jwt_service: JWTService) -> dict:
    token = jwt_service.create_access_token(
        user_id="admin-001",
        email="admin@test.com",
        display_name="Admin",
        roles=["admin"],
        bu_scope=["ALL"],
        persona="analyst",
    )
    return {"Authorization": f"Bearer {token}"}


def _analyst_token(jwt_service: JWTService) -> dict:
    token = jwt_service.create_access_token(
        user_id="analyst-001",
        email="analyst@test.com",
        display_name="Analyst",
        roles=["analyst"],
        bu_scope=["ALL"],
        persona="analyst",
    )
    return {"Authorization": f"Bearer {token}"}


class TestUserList:
    """Tests for GET /admin/users."""

    def test_list_users_admin(self, app_client, jwt_service):
        resp = app_client.get("/api/v1/admin/users", headers=_admin_token(jwt_service))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 6  # 6 demo users
        assert len(data["users"]) >= 6

    def test_list_users_non_admin_forbidden(self, app_client, jwt_service):
        resp = app_client.get("/api/v1/admin/users", headers=_analyst_token(jwt_service))
        assert resp.status_code == 403


class TestUserCreate:
    """Tests for POST /admin/users."""

    def test_create_user(self, app_client, jwt_service):
        resp = app_client.post("/api/v1/admin/users", json={
            "email": "newuser@test.com",
            "display_name": "New User",
            "password": "securepass",
            "role_name": "analyst",
        }, headers=_admin_token(jwt_service))
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"

    def test_create_duplicate_email_409(self, app_client, jwt_service):
        # First create
        app_client.post("/api/v1/admin/users", json={
            "email": "dup@test.com",
            "display_name": "Dup",
            "password": "securepass",
        }, headers=_admin_token(jwt_service))
        # Duplicate
        resp = app_client.post("/api/v1/admin/users", json={
            "email": "dup@test.com",
            "display_name": "Dup2",
            "password": "securepass",
        }, headers=_admin_token(jwt_service))
        assert resp.status_code == 409


class TestUserDeactivate:
    """Tests for DELETE /admin/users/{user_id}."""

    def test_deactivate_user(self, app_client, jwt_service):
        # Create a user first
        resp = app_client.post("/api/v1/admin/users", json={
            "email": "deact@test.com",
            "display_name": "Deactivate Me",
            "password": "securepass",
        }, headers=_admin_token(jwt_service))
        uid = resp.json()["user_id"]

        # Deactivate
        resp = app_client.delete(f"/api/v1/admin/users/{uid}", headers=_admin_token(jwt_service))
        assert resp.status_code == 204

    def test_cannot_deactivate_self(self, app_client, jwt_service):
        """Admin cannot deactivate their own account."""
        resp = app_client.delete("/api/v1/admin/users/admin-001", headers=_admin_token(jwt_service))
        assert resp.status_code == 400


class TestRoleAssignment:
    """Tests for POST /admin/users/{user_id}/roles."""

    def test_assign_role(self, app_client, jwt_service):
        # Create user
        resp = app_client.post("/api/v1/admin/users", json={
            "email": "roletest@test.com",
            "display_name": "Role Test",
            "password": "securepass",
        }, headers=_admin_token(jwt_service))
        uid = resp.json()["user_id"]

        # Assign director role
        resp = app_client.post(f"/api/v1/admin/users/{uid}/roles", json={
            "role_name": "director",
            "bu_scope": ["ALL"],
        }, headers=_admin_token(jwt_service))
        assert resp.status_code == 200


class TestRolesList:
    """Tests for GET /admin/roles."""

    def test_list_roles(self, app_client, jwt_service):
        resp = app_client.get("/api/v1/admin/roles", headers=_admin_token(jwt_service))
        assert resp.status_code == 200
        roles = resp.json()
        role_names = {r["role_name"] for r in roles}
        assert "admin" in role_names
        assert "analyst" in role_names
        assert "cfo" in role_names


class TestAuditLog:
    """Tests for GET /admin/audit-log."""

    def test_get_audit_log(self, app_client, jwt_service):
        resp = app_client.get("/api/v1/admin/audit-log", headers=_admin_token(jwt_service))
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "total" in data

    def test_audit_log_non_admin_forbidden(self, app_client, jwt_service):
        resp = app_client.get("/api/v1/admin/audit-log", headers=_analyst_token(jwt_service))
        assert resp.status_code == 403
