"""Unit tests for JWT service (shared/auth/jwt.py).

Tests token creation, validation, expiry, refresh tokens,
invalid tokens, and payload extraction.
"""

import time
import pytest
from shared.auth.jwt import (
    JWTService,
    TokenPayload,
    InvalidTokenError,
    TokenExpiredError,
)


@pytest.fixture
def jwt_service() -> JWTService:
    """Create a JWT service with a test secret key."""
    return JWTService(
        secret_key="test-secret-key-for-unit-tests",
        access_token_expire_minutes=60,
        refresh_token_expire_minutes=1440,
    )


@pytest.fixture
def sample_claims() -> dict:
    """Sample user claims for token creation."""
    return {
        "user_id": "user-001",
        "email": "analyst@test.com",
        "display_name": "Test Analyst",
        "roles": ["analyst"],
        "bu_scope": ["ALL"],
        "persona": "analyst",
    }


class TestJWTCreation:
    """Tests for token creation."""

    def test_create_access_token(self, jwt_service: JWTService, sample_claims: dict):
        """Access token is a non-empty string."""
        token = jwt_service.create_access_token(**sample_claims)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_service: JWTService):
        """Refresh token is a non-empty string."""
        token = jwt_service.create_refresh_token(user_id="user-001")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_and_refresh_are_different(self, jwt_service: JWTService, sample_claims: dict):
        """Access and refresh tokens are distinct."""
        access = jwt_service.create_access_token(**sample_claims)
        refresh = jwt_service.create_refresh_token(user_id="user-001")
        assert access != refresh


class TestJWTValidation:
    """Tests for token validation and decoding."""

    def test_decode_access_token_payload(self, jwt_service: JWTService, sample_claims: dict):
        """Decoded access token contains correct claims."""
        token = jwt_service.create_access_token(**sample_claims)
        payload = jwt_service.decode_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == "user-001"
        assert payload.email == "analyst@test.com"
        assert payload.display_name == "Test Analyst"
        assert payload.roles == ["analyst"]
        assert payload.bu_scope == ["ALL"]
        assert payload.persona == "analyst"
        assert payload.token_type == "access"
        assert payload.jti  # JTI should be set

    def test_decode_refresh_token_type(self, jwt_service: JWTService):
        """Refresh token has token_type='refresh'."""
        token = jwt_service.create_refresh_token(user_id="user-001")
        payload = jwt_service.decode_token(token)
        assert payload.token_type == "refresh"
        assert payload.sub == "user-001"

    def test_decode_token_with_extra_claims(self, jwt_service: JWTService, sample_claims: dict):
        """Extra claims are included in the token."""
        token = jwt_service.create_access_token(
            **sample_claims,
            extra_claims={"custom_field": "custom_value"},
        )
        # Decode raw claims to check custom field
        raw = jwt_service.decode_token_unverified(token)
        assert raw["custom_field"] == "custom_value"

    def test_multiple_roles(self, jwt_service: JWTService):
        """Token with multiple roles preserves all roles."""
        token = jwt_service.create_access_token(
            user_id="admin-001",
            email="admin@test.com",
            display_name="Admin User",
            roles=["admin", "analyst", "director"],
            bu_scope=["ALL"],
            persona="analyst",
        )
        payload = jwt_service.decode_token(token)
        assert set(payload.roles) == {"admin", "analyst", "director"}

    def test_bu_scope_preserved(self, jwt_service: JWTService, sample_claims: dict):
        """BU scope with specific BUs is preserved."""
        claims = {**sample_claims, "bu_scope": ["BU001", "BU002"]}
        token = jwt_service.create_access_token(**claims)
        payload = jwt_service.decode_token(token)
        assert payload.bu_scope == ["BU001", "BU002"]


class TestJWTExpiry:
    """Tests for token expiration."""

    def test_expired_access_token(self):
        """Expired access token raises TokenExpiredError."""
        svc = JWTService(
            secret_key="test-secret",
            access_token_expire_minutes=0,  # immediate expiry
        )
        token = svc.create_access_token(
            user_id="user-001",
            email="test@test.com",
            display_name="Test",
            roles=["analyst"],
            bu_scope=["ALL"],
            persona="analyst",
        )
        # Token created with 0-minute expiry is already expired (or about to be)
        time.sleep(1)
        with pytest.raises(TokenExpiredError):
            svc.decode_token(token)

    def test_is_token_expired_helper(self):
        """is_token_expired returns True for expired tokens."""
        svc = JWTService(secret_key="test-secret", access_token_expire_minutes=0)
        token = svc.create_access_token(
            user_id="user-001",
            email="test@test.com",
            display_name="Test",
            roles=[],
            bu_scope=["ALL"],
            persona="analyst",
        )
        time.sleep(1)
        assert svc.is_token_expired(token) is True

    def test_valid_token_not_expired(self, jwt_service: JWTService, sample_claims: dict):
        """Valid token is not expired."""
        token = jwt_service.create_access_token(**sample_claims)
        assert jwt_service.is_token_expired(token) is False


class TestJWTInvalid:
    """Tests for invalid tokens."""

    def test_invalid_token_string(self, jwt_service: JWTService):
        """Garbage token string raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token("not-a-valid-jwt-token")

    def test_wrong_secret_key(self, sample_claims: dict):
        """Token signed with different key is rejected."""
        svc1 = JWTService(secret_key="secret-1")
        svc2 = JWTService(secret_key="secret-2")
        token = svc1.create_access_token(**sample_claims)
        with pytest.raises(InvalidTokenError):
            svc2.decode_token(token)

    def test_empty_token(self, jwt_service: JWTService):
        """Empty string raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token("")

    def test_decode_unverified(self, jwt_service: JWTService, sample_claims: dict):
        """Unverified decode returns raw claims dict."""
        token = jwt_service.create_access_token(**sample_claims)
        raw = jwt_service.decode_token_unverified(token)
        assert isinstance(raw, dict)
        assert raw["sub"] == "user-001"
        assert raw["email"] == "analyst@test.com"
