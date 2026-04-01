"""FastAPI authentication dependencies (middleware).

Provides ``Depends``-based guards for JWT validation, role checking,
BU scope enforcement, and admin access. In development mode with no
token present, returns a default dev user for convenience.

Usage::

    from shared.auth.middleware import get_current_user, require_role

    @router.get("/protected")
    async def protected(user: UserContext = Depends(get_current_user)):
        ...

    @router.get("/admin-only")
    async def admin_only(user: UserContext = Depends(require_admin())):
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status

from shared.auth.jwt import InvalidTokenError, JWTService, TokenExpiredError, TokenPayload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User context (passed to route handlers)
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    """Authenticated user context extracted from JWT.

    Available in route handlers via ``Depends(get_current_user)``.
    """

    user_id: str
    email: str
    display_name: str
    roles: list[str] = field(default_factory=list)
    bu_scope: list[str] = field(default_factory=lambda: ["ALL"])
    persona: str = "analyst"
    token_payload: Optional[TokenPayload] = field(default=None, repr=False)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles or "admin" in self.roles

    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        return any(self.has_role(r) for r in roles)

    def has_bu_access(self, bu_id: str) -> bool:
        """Check if user can access a specific BU."""
        return "ALL" in self.bu_scope or bu_id in self.bu_scope

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles


# ---------------------------------------------------------------------------
# Default dev user (development mode fallback)
# ---------------------------------------------------------------------------

DEV_USER = UserContext(
    user_id="dev-user-001",
    email="admin@variance-agent.dev",
    display_name="Dev Admin",
    roles=["admin", "analyst", "director"],
    bu_scope=["ALL"],
    persona="analyst",
)


# ---------------------------------------------------------------------------
# JWT extraction helper
# ---------------------------------------------------------------------------

def _extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


# ---------------------------------------------------------------------------
# Core dependency: get_current_user
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> UserContext:
    """FastAPI dependency that extracts and validates the JWT.

    In development mode (ENVIRONMENT=development) with no Authorization
    header, returns a default dev user for convenience.

    Raises:
        HTTPException(401): If token is missing, invalid, or expired.
    """
    jwt_service: Optional[JWTService] = getattr(request.app.state, "jwt_service", None)
    environment: str = getattr(request.app.state, "environment", "development")

    token = _extract_token(request)

    # Dev mode fallback: no token → return dev user
    if not token:
        if environment == "development":
            return DEV_USER
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not jwt_service:
        # JWT service not initialised — should not happen in production
        if environment == "development":
            return DEV_USER
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not available",
        )

    try:
        payload = jwt_service.decode_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject refresh tokens used as access tokens
    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserContext(
        user_id=payload.sub,
        email=payload.email,
        display_name=payload.display_name,
        roles=payload.roles,
        bu_scope=payload.bu_scope,
        persona=payload.persona,
        token_payload=payload,
    )


# ---------------------------------------------------------------------------
# Role-checking dependencies
# ---------------------------------------------------------------------------

def require_role(*required_roles: str) -> Callable:
    """Factory that returns a dependency enforcing role membership.

    Usage::

        @router.get("/review")
        async def review_queue(
            user: UserContext = Depends(require_role("analyst", "admin"))
        ):
            ...
    """

    async def _check_role(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if not user.has_any_role(*required_roles):
            logger.warning(
                "RBAC denied: user=%s roles=%s required=%s",
                user.user_id,
                user.roles,
                required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {' or '.join(required_roles)}",
            )
        return user

    return _check_role


def require_admin() -> Callable:
    """Shorthand for ``require_role("admin")``."""
    return require_role("admin")


def require_bu_access(bu_id_param: str = "bu_id") -> Callable:
    """Factory that returns a dependency enforcing BU scope access.

    Extracts the BU ID from a path or query parameter and checks
    that the user has access.

    Args:
        bu_id_param: Name of the path/query parameter containing the BU ID.
    """

    async def _check_bu(
        request: Request,
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        bu_id = request.path_params.get(bu_id_param) or request.query_params.get(bu_id_param)
        if bu_id and not user.has_bu_access(bu_id):
            logger.warning(
                "BU access denied: user=%s bu_scope=%s requested_bu=%s",
                user.user_id,
                user.bu_scope,
                bu_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for business unit: {bu_id}",
            )
        return user

    return _check_bu


# ---------------------------------------------------------------------------
# Optional auth (for endpoints that work with or without auth)
# ---------------------------------------------------------------------------

async def get_optional_user(request: Request) -> Optional[UserContext]:
    """Like ``get_current_user`` but returns None instead of raising 401."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
