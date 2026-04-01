"""Integration tests for RBAC enforcement across gateway endpoints.

Tests that each endpoint group properly enforces role-based access:
- Public endpoints (auth) require no token
- Protected endpoints require valid JWT
- Role-specific endpoints reject unauthorized roles
- Admin endpoints require admin role
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from shared.auth.jwt import JWTService
from shared.auth.middleware import UserContext, get_current_user, require_role, require_admin


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key="rbac-enforcement-test-secret")


def _token(jwt_service: JWTService, roles: list[str], **kwargs) -> str:
    """Create a test JWT for a specific role set."""
    return jwt_service.create_access_token(
        user_id=kwargs.get("user_id", "test-user"),
        email=kwargs.get("email", "test@test.com"),
        display_name=kwargs.get("display_name", "Test"),
        roles=roles,
        bu_scope=kwargs.get("bu_scope", ["ALL"]),
        persona=kwargs.get("persona", "analyst"),
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test app simulating the gateway's endpoint protection pattern
# ---------------------------------------------------------------------------

def _create_protected_app(jwt_service: JWTService) -> FastAPI:
    """Create a minimal app mimicking gateway auth patterns."""
    app = FastAPI()
    app.state.jwt_service = jwt_service
    app.state.environment = "production"  # No dev fallback

    # Auth (public)
    @app.post("/api/v1/auth/login")
    async def login():
        return {"status": "ok"}

    # Dimensions (any authenticated)
    @app.get("/api/v1/dimensions/hierarchies")
    async def get_hierarchies(user: UserContext = Depends(get_current_user)):
        return {"user": user.user_id}

    # Chat (any authenticated)
    @app.post("/api/v1/chat/messages")
    async def send_message(user: UserContext = Depends(get_current_user)):
        return {"user": user.user_id}

    # Review (analyst or admin)
    @app.get("/api/v1/review/queue")
    async def review_queue(user: UserContext = Depends(require_role("analyst", "admin"))):
        return {"user": user.user_id, "roles": user.roles}

    # Approval (director, cfo, admin)
    @app.get("/api/v1/approval/queue")
    async def approval_queue(user: UserContext = Depends(require_role("director", "cfo", "admin"))):
        return {"user": user.user_id, "roles": user.roles}

    # Config read (any authenticated)
    @app.get("/api/v1/config/thresholds")
    async def get_thresholds(user: UserContext = Depends(get_current_user)):
        return {"thresholds": {}}

    # Config write (admin only)
    @app.put("/api/v1/config/thresholds")
    async def update_thresholds(user: UserContext = Depends(require_admin())):
        return {"updated": True}

    # Notifications (admin only)
    @app.post("/api/v1/notifications/test")
    async def test_notification(user: UserContext = Depends(require_admin())):
        return {"sent": True}

    return app


@pytest.fixture
def client(jwt_service) -> TestClient:
    return TestClient(_create_protected_app(jwt_service))


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    """Auth endpoints should be accessible without a token."""

    def test_login_no_token(self, client):
        """Login endpoint requires no auth."""
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Any-authenticated endpoints
# ---------------------------------------------------------------------------

class TestAuthenticatedEndpoints:
    """Endpoints that require any valid JWT."""

    def test_dimensions_no_token_401(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies")
        assert resp.status_code == 401

    def test_dimensions_valid_token_200(self, client, jwt_service):
        token = _token(jwt_service, ["analyst"])
        resp = client.get("/api/v1/dimensions/hierarchies", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_chat_no_token_401(self, client):
        resp = client.post("/api/v1/chat/messages")
        assert resp.status_code == 401

    def test_chat_any_role_200(self, client, jwt_service):
        """Any role can use chat."""
        for role in ["analyst", "cfo", "board_viewer"]:
            token = _token(jwt_service, [role])
            resp = client.post("/api/v1/chat/messages", headers=_auth_header(token))
            assert resp.status_code == 200, f"Role {role} should access chat"

    def test_config_read_any_role(self, client, jwt_service):
        """Config read is accessible to any authenticated user."""
        token = _token(jwt_service, ["board_viewer"])
        resp = client.get("/api/v1/config/thresholds", headers=_auth_header(token))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Role-specific: Review (analyst, admin)
# ---------------------------------------------------------------------------

class TestReviewEndpoints:
    """Review queue requires analyst or admin role."""

    def test_review_analyst_allowed(self, client, jwt_service):
        token = _token(jwt_service, ["analyst"])
        resp = client.get("/api/v1/review/queue", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_review_admin_allowed(self, client, jwt_service):
        token = _token(jwt_service, ["admin"])
        resp = client.get("/api/v1/review/queue", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_review_cfo_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["cfo"])
        resp = client.get("/api/v1/review/queue", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_review_board_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["board_viewer"])
        resp = client.get("/api/v1/review/queue", headers=_auth_header(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Role-specific: Approval (director, cfo, admin)
# ---------------------------------------------------------------------------

class TestApprovalEndpoints:
    """Approval queue requires director, cfo, or admin role."""

    def test_approval_director_allowed(self, client, jwt_service):
        token = _token(jwt_service, ["director"])
        resp = client.get("/api/v1/approval/queue", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_approval_cfo_allowed(self, client, jwt_service):
        token = _token(jwt_service, ["cfo"])
        resp = client.get("/api/v1/approval/queue", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_approval_analyst_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["analyst"])
        resp = client.get("/api/v1/approval/queue", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_approval_bu_leader_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["bu_leader"])
        resp = client.get("/api/v1/approval/queue", headers=_auth_header(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------

class TestAdminEndpoints:
    """Admin endpoints require admin role."""

    def test_config_write_admin_allowed(self, client, jwt_service):
        token = _token(jwt_service, ["admin"])
        resp = client.put("/api/v1/config/thresholds", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_config_write_analyst_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["analyst"])
        resp = client.put("/api/v1/config/thresholds", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_notification_test_admin_only(self, client, jwt_service):
        token = _token(jwt_service, ["admin"])
        resp = client.post("/api/v1/notifications/test", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_notification_test_analyst_forbidden(self, client, jwt_service):
        token = _token(jwt_service, ["analyst"])
        resp = client.post("/api/v1/notifications/test", headers=_auth_header(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cross-cutting: token issues
# ---------------------------------------------------------------------------

class TestTokenEdgeCases:
    """Edge cases for auth tokens."""

    def test_malformed_auth_header(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies", headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    def test_empty_bearer_token(self, client):
        resp = client.get("/api/v1/dimensions/hierarchies", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_wrong_secret_key(self, client):
        wrong_svc = JWTService(secret_key="wrong-secret")
        token = _token(wrong_svc, ["admin"])
        resp = client.get("/api/v1/dimensions/hierarchies", headers=_auth_header(token))
        assert resp.status_code == 401
