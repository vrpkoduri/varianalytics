"""JWT token creation and validation.

Uses python-jose (HS256) for signing. Supports access tokens (short-lived)
and refresh tokens (long-lived). Token payload carries user identity,
roles, BU scope, and persona type for downstream RBAC checks.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (overridden by Settings)
# ---------------------------------------------------------------------------
DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
DEFAULT_REFRESH_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


class InvalidTokenError(Exception):
    """Raised when a JWT cannot be decoded or is invalid."""

    def __init__(self, detail: str = "Invalid token") -> None:
        self.detail = detail
        super().__init__(detail)


class TokenExpiredError(InvalidTokenError):
    """Raised when a JWT has expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired")


# ---------------------------------------------------------------------------
# Token payload schema
# ---------------------------------------------------------------------------

class TokenPayload:
    """Parsed JWT claims."""

    def __init__(self, claims: dict[str, Any]) -> None:
        self.sub: str = claims.get("sub", "")
        self.email: str = claims.get("email", "")
        self.display_name: str = claims.get("display_name", "")
        self.roles: list[str] = claims.get("roles", [])
        self.bu_scope: list[str] = claims.get("bu_scope", ["ALL"])
        self.persona: str = claims.get("persona", "analyst")
        self.token_type: str = claims.get("token_type", "access")
        self.exp: Optional[datetime] = None
        self.iat: Optional[datetime] = None
        self.jti: str = claims.get("jti", "")

        # Parse timestamps
        if "exp" in claims:
            self.exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
        if "iat" in claims:
            self.iat = datetime.fromtimestamp(claims["iat"], tz=UTC)


# ---------------------------------------------------------------------------
# JWTService
# ---------------------------------------------------------------------------

class JWTService:
    """Manages JWT creation and validation.

    Args:
        secret_key: HMAC signing key. Must be kept secret.
        algorithm: JWT algorithm (default HS256).
        access_token_expire_minutes: Access token lifetime.
        refresh_token_expire_minutes: Refresh token lifetime.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = DEFAULT_ALGORITHM,
        access_token_expire_minutes: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_minutes: int = DEFAULT_REFRESH_TOKEN_EXPIRE_MINUTES,
    ) -> None:
        if not secret_key or secret_key == "change-me-in-production":
            logger.warning(
                "JWT secret_key is using default value. "
                "Set SECRET_KEY environment variable for production."
            )
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_minutes = refresh_token_expire_minutes

    def create_access_token(
        self,
        user_id: str,
        email: str,
        display_name: str,
        roles: list[str],
        bu_scope: list[str],
        persona: str,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a short-lived access token.

        Args:
            user_id: Unique user identifier (sub claim).
            email: User email address.
            display_name: User display name.
            roles: List of role names.
            bu_scope: List of accessible BU IDs (or ["ALL"]).
            persona: Primary persona type.
            extra_claims: Additional claims to include.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": user_id,
            "email": email,
            "display_name": display_name,
            "roles": roles,
            "bu_scope": bu_scope,
            "persona": persona,
            "token_type": "access",
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a long-lived refresh token.

        Args:
            user_id: Unique user identifier (sub claim).
            extra_claims: Additional claims to include.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.refresh_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": user_id,
            "token_type": "refresh",
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT.

        Args:
            token: Encoded JWT string.

        Returns:
            Parsed :class:`TokenPayload`.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is malformed or signature invalid.
        """
        try:
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return TokenPayload(claims)
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError as exc:
            raise InvalidTokenError(f"Could not validate token: {exc}")

    def decode_token_unverified(self, token: str) -> dict[str, Any]:
        """Decode a JWT without verification (for debugging/inspection).

        Args:
            token: Encoded JWT string.

        Returns:
            Raw claims dictionary.
        """
        return jwt.get_unverified_claims(token)

    def is_token_expired(self, token: str) -> bool:
        """Check whether a token has expired without raising.

        Args:
            token: Encoded JWT string.

        Returns:
            True if expired, False if still valid.
        """
        try:
            self.decode_token(token)
            return False
        except TokenExpiredError:
            return True
        except InvalidTokenError:
            return True
