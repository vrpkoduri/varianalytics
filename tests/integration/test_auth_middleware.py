"""Integration tests for auth middleware (shared/auth/middleware.py).

Tests JWT validation, role checking, BU scope enforcement,
and dev-mode fallback using a real FastAPI application.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from shared.auth.jwt import JWTService
from shared.auth.middleware import (
    UserContext,
    get_current_user,
    require_role,
    require_admin,
    require_bu_access,
    get_optional_user,
)


# ---------------------------------------------------------------------------
# Test app with various protected endpoints
# ---------------------------------------------------------------------------

def _create_test_app(jwt_service: JWTService, environment: str = "production") -> FastAPI:
    """Create a FastAPI app with protected routes for testing."""
    app = FastAPI()
    app.state.jwt_service = jwt_service
    app.state.environment = environment

    @app.get("/public")
    async def public():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected(user: UserContext = Depends(get_current_user)):
        return {"user_id": user.user_id, "roles": user.roles}

    @app.get("/analyst-only")
    async def analyst_only(user: UserContext = Depends(require_role("analyst"))):
        return {"user_id": user.user_id}

    @app.get("/admin-only")
    async def admin_only(user: UserContext = Depends(require_admin())):
        return {"user_id": user.user_id}

    @app.get("/multi-role")
    async def multi_role(user: UserContext = Depends(require_role("analyst", "director"))):
        return {"user_id": user.user_id}

    @app.get("/optional-auth")
    async def optional_auth(user=Depends(get_optional_user)):
        return {"user_id": user.user_id if user else None}

    return app


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key="middleware-test-secret")


def _make_token(jwt_service: JWTService, roles: list[str], **kwargs) -> str:
    """Helper to create a test access token."""
    defaults = {
        "user_id": "test-user",
        "email": "test@test.com",
        "display_name": "Test User",
        "roles": roles,
        "bu_scope": kwargs.get("bu_scope", ["ALL"]),
        "persona": kwargs.get("persona", "analyst"),
    }
    return jwt_service.create_access_token(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    """Tests for get_current_user dependency."""

    def test_valid_token_accepted(self, jwt_service):
        """Request with valid JWT is accepted."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["analyst"])

        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "test-user"

    def test_missing_token_production_401(self, jwt_service):
        """Missing token in production mode returns 401."""
        app = _create_test_app(jwt_service, environment="production")
        client = TestClient(app)

        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_missing_token_dev_mode_fallback(self, jwt_service):
        """Missing token in development mode returns dev user."""
        app = _create_test_app(jwt_service, environment="development")
        client = TestClient(app)

        resp = client.get("/protected")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "dev-user-001"

    def test_invalid_token_401(self, jwt_service):
        """Invalid token returns 401."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)

        resp = client.get("/protected", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_expired_token_401(self):
        """Expired token returns 401."""
        svc = JWTService(secret_key="test", access_token_expire_minutes=0)
        app = _create_test_app(svc)
        client = TestClient(app)

        import time
        token = _make_token(svc, ["analyst"])
        time.sleep(1)

        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_refresh_token_rejected_as_access(self, jwt_service):
        """Refresh token used as access token is rejected."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        refresh = jwt_service.create_refresh_token(user_id="test-user")

        resp = client.get("/protected", headers={"Authorization": f"Bearer {refresh}"})
        assert resp.status_code == 401


class TestRoleChecks:
    """Tests for require_role dependency."""

    def test_correct_role_allowed(self, jwt_service):
        """User with required role is allowed."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["analyst"])

        resp = client.get("/analyst-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_wrong_role_forbidden(self, jwt_service):
        """User without required role gets 403."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["board_viewer"])

        resp = client.get("/analyst-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_bypasses_role_check(self, jwt_service):
        """Admin role can access any role-protected endpoint."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["admin"])

        resp = client.get("/analyst-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_multi_role_any_match(self, jwt_service):
        """Endpoint requiring analyst OR director — director passes."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["director"])

        resp = client.get("/multi-role", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_only_endpoint(self, jwt_service):
        """Only admin role can access admin-only endpoint."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)

        # Non-admin
        token = _make_token(jwt_service, ["analyst"])
        resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

        # Admin
        token = _make_token(jwt_service, ["admin"])
        resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestOptionalAuth:
    """Tests for get_optional_user dependency."""

    def test_optional_with_token(self, jwt_service):
        """Optional auth returns user when token present."""
        app = _create_test_app(jwt_service)
        client = TestClient(app)
        token = _make_token(jwt_service, ["analyst"])

        resp = client.get("/optional-auth", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "test-user"

    def test_optional_without_token_production(self, jwt_service):
        """Optional auth returns None when no token (production)."""
        app = _create_test_app(jwt_service, environment="production")
        client = TestClient(app)

        resp = client.get("/optional-auth")
        assert resp.status_code == 200
        assert resp.json()["user_id"] is None


class TestUserContext:
    """Tests for UserContext helper methods."""

    def test_has_role(self):
        user = UserContext(user_id="u1", email="e", display_name="d", roles=["analyst"])
        assert user.has_role("analyst") is True
        assert user.has_role("cfo") is False

    def test_admin_has_all_roles(self):
        user = UserContext(user_id="u1", email="e", display_name="d", roles=["admin"])
        assert user.has_role("analyst") is True  # admin bypasses
        assert user.has_role("anything") is True

    def test_has_bu_access_all(self):
        user = UserContext(user_id="u1", email="e", display_name="d", bu_scope=["ALL"])
        assert user.has_bu_access("BU001") is True

    def test_has_bu_access_specific(self):
        user = UserContext(user_id="u1", email="e", display_name="d", bu_scope=["BU001"])
        assert user.has_bu_access("BU001") is True
        assert user.has_bu_access("BU002") is False

    def test_is_admin(self):
        admin = UserContext(user_id="u1", email="e", display_name="d", roles=["admin"])
        non_admin = UserContext(user_id="u2", email="e", display_name="d", roles=["analyst"])
        assert admin.is_admin is True
        assert non_admin.is_admin is False
