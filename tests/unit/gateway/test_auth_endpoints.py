"""Unit tests for auth API endpoints (services/gateway/api/auth.py).

Tests login, logout, refresh, registration, and /me endpoint
using FastAPI TestClient with an in-memory SQLite database.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from shared.auth.jwt import JWTService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key="test-secret-key-auth-endpoints")


@pytest_asyncio.fixture
async def db_session_factory():
    """In-memory SQLite DB with auth tables and seeded data."""
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
    """Create a FastAPI TestClient with auth services wired up."""
    from fastapi import FastAPI
    from services.gateway.api.auth import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Wire up app state
    app.state.jwt_service = jwt_service
    app.state.environment = "development"

    from shared.auth.user_store import UserStore
    import asyncio

    # We need to create the user store with the async session factory
    # TestClient handles the async setup
    app.state.user_store = UserStore(db_session_factory)
    app.state.azure_ad_provider = None

    return TestClient(app)


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for POST /auth/login."""

    def test_login_success(self, app_client):
        """Successful login returns JWT tokens."""
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "analyst@variance-agent.dev",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, app_client):
        """Wrong password returns 401."""
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "analyst@variance-agent.dev",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, app_client):
        """Nonexistent email returns 401."""
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_token_is_decodable(self, app_client, jwt_service):
        """Returned access token can be decoded."""
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "analyst@variance-agent.dev",
            "password": "password123",
        })
        token = resp.json()["access_token"]
        payload = jwt_service.decode_token(token)
        assert payload.email == "analyst@variance-agent.dev"
        assert "analyst" in payload.roles


# ---------------------------------------------------------------------------
# /me tests
# ---------------------------------------------------------------------------

class TestGetMe:
    """Tests for GET /auth/me."""

    def test_me_with_valid_token(self, app_client, jwt_service):
        """Authenticated /me returns user profile."""
        # Login first
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "admin@variance-agent.dev",
            "password": "password123",
        })
        token = resp.json()["access_token"]

        # Call /me
        resp = app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@variance-agent.dev"
        assert "admin" in data["roles"]

    def test_me_dev_mode_no_token(self, app_client):
        """In dev mode, /me without token returns dev user."""
        resp = app_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "dev-user-001"


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

class TestRegister:
    """Tests for POST /auth/register."""

    def test_register_new_user(self, app_client):
        """Register a new user in dev mode."""
        resp = app_client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "password123",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert "analyst" in data["roles"]  # default role

    def test_register_duplicate_email(self, app_client):
        """Registering with existing email returns 409."""
        app_client.post("/api/v1/auth/register", json={
            "email": "dup_register@example.com",
            "password": "password123",
            "display_name": "First",
        })
        resp = app_client.post("/api/v1/auth/register", json={
            "email": "dup_register@example.com",
            "password": "password123",
            "display_name": "Second",
        })
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Refresh tests
# ---------------------------------------------------------------------------

class TestRefresh:
    """Tests for POST /auth/refresh."""

    def test_refresh_token(self, app_client):
        """Valid refresh token returns new token pair."""
        # Login to get refresh token
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "analyst@variance-agent.dev",
            "password": "password123",
        })
        refresh = resp.json()["refresh_token"]

        # Refresh
        resp = app_client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_fails(self, app_client):
        """Using access token as refresh token fails."""
        resp = app_client.post("/api/v1/auth/login", json={
            "email": "analyst@variance-agent.dev",
            "password": "password123",
        })
        access = resp.json()["access_token"]

        resp = app_client.post("/api/v1/auth/refresh", json={
            "refresh_token": access,
        })
        assert resp.status_code == 401

    def test_refresh_with_invalid_token(self, app_client):
        """Invalid refresh token returns 401."""
        resp = app_client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not-a-valid-token",
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Azure AD config
# ---------------------------------------------------------------------------

class TestAzureADConfig:
    """Tests for GET /auth/azure-ad/config."""

    def test_azure_ad_not_configured(self, app_client):
        """When Azure AD is not configured, returns configured=false."""
        resp = app_client.get("/api/v1/auth/azure-ad/config")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False
