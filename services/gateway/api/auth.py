"""Authentication endpoints.

Handles login (local dev + Azure AD OAuth 2.0), logout, token refresh,
user registration (dev mode), and current-user lookup. Auth state is
managed via JWT tokens signed by the gateway.

Two auth modes:
- **Dev mode** (default): Email + password against local DB users.
- **Azure AD mode**: OAuth 2.0 code exchange when AZURE_AD_TENANT_ID is set.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from shared.auth.middleware import UserContext, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Login credentials (dev mode: email + password)."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AzureADLoginRequest(BaseModel):
    """OAuth 2.0 authorization code exchange (Azure AD mode)."""

    code: str = Field(..., description="Authorization code from Azure AD")
    redirect_uri: str = Field(..., description="OAuth callback URL")


class RegisterRequest(BaseModel):
    """User registration (dev mode only)."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    display_name: str = Field(..., description="Display name")


class TokenResponse(BaseModel):
    """JWT token pair returned on login / refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(3600, description="Access token lifetime in seconds")


class UserProfile(BaseModel):
    """Current user profile with roles and permissions."""

    user_id: str
    email: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    bu_scope: list[str] = Field(default_factory=list, description="Accessible BU IDs")
    persona: str = "analyst"
    is_admin: bool = False


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_jwt_service(request: Request):
    """Get JWTService from app state."""
    svc = getattr(request.app.state, "jwt_service", None)
    if not svc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not initialised",
        )
    return svc


def _get_user_store(request: Request):
    """Get UserStore from app state."""
    store = getattr(request.app.state, "user_store", None)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialised",
        )
    return store


async def _issue_tokens(request: Request, user_dto) -> TokenResponse:
    """Issue access + refresh token pair for a user."""
    jwt_service = _get_jwt_service(request)
    from shared.auth.rbac import RBACService
    rbac = RBACService()

    role_names = user_dto.role_names
    persona = rbac.resolve_persona(role_names)

    access_token = jwt_service.create_access_token(
        user_id=user_dto.user_id,
        email=user_dto.email,
        display_name=user_dto.display_name,
        roles=role_names,
        bu_scope=user_dto.bu_scope,
        persona=persona,
    )
    refresh_token = jwt_service.create_refresh_token(user_id=user_dto.user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=jwt_service.access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    """Authenticate with email + password (dev mode).

    Returns access + refresh JWT tokens on success.
    """
    user_store = _get_user_store(request)

    user = await user_store.verify_password(body.email, body.password)
    if not user:
        logger.warning("Failed login attempt for email: %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    logger.info("User logged in: %s (%s)", user.user_id, user.email)
    return await _issue_tokens(request, user)


@router.post(
    "/login/azure-ad",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login via Azure AD OAuth 2.0",
)
async def login_azure_ad(body: AzureADLoginRequest, request: Request) -> TokenResponse:
    """Exchange an Azure AD authorization code for JWT tokens.

    Only available when AZURE_AD_TENANT_ID is configured.
    """
    azure_provider = getattr(request.app.state, "azure_ad_provider", None)
    if not azure_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Azure AD authentication not configured",
        )

    user_store = _get_user_store(request)

    try:
        # Exchange code for Azure AD tokens
        ad_tokens = await azure_provider.exchange_code(body.code, body.redirect_uri)

        # Get user profile from Microsoft Graph
        ad_user = await azure_provider.get_user_info(ad_tokens.access_token)

        # Upsert user in our DB
        user = await user_store.upsert_azure_ad_user(
            oid=ad_user.oid,
            email=ad_user.email,
            display_name=ad_user.display_name,
        )

        logger.info("Azure AD login: %s (%s)", user.user_id, user.email)
        return await _issue_tokens(request, user)

    except Exception as exc:
        logger.error("Azure AD login failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Azure AD authentication failed: {exc}",
        )


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (dev mode only)",
)
async def register(body: RegisterRequest, request: Request) -> UserProfile:
    """Create a new local user account.

    Only available in development mode.
    """
    environment = getattr(request.app.state, "environment", "development")
    if environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration only available in development mode",
        )

    user_store = _get_user_store(request)

    try:
        user = await user_store.create_user(
            email=body.email,
            display_name=body.display_name,
            password=body.password,
        )

        # Assign default analyst role
        await user_store.assign_role(user.user_id, "analyst")

        # Refresh user to include roles
        user = await user_store.get_user_by_id(user.user_id)
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")

        logger.info("New user registered: %s (%s)", user.user_id, user.email)
        return UserProfile(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            roles=user.role_names,
            bu_scope=user.bu_scope,
            persona=user.persona,
            is_admin="admin" in user.role_names,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current session",
)
async def logout(
    user: UserContext = Depends(get_current_user),
) -> None:
    """Revoke the current session.

    In production, the refresh token would be blacklisted in Redis.
    For MVP, the client simply discards its tokens.
    """
    logger.info("User logged out: %s", user.user_id)
    # TODO: Add refresh token to Redis blacklist for production
    return None


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_me(
    user: UserContext = Depends(get_current_user),
) -> UserProfile:
    """Return the authenticated user's profile and role assignments."""
    return UserProfile(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        roles=user.roles,
        bu_scope=user.bu_scope,
        persona=user.persona,
        is_admin=user.is_admin,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(body: RefreshRequest, request: Request) -> TokenResponse:
    """Issue a new access token using a valid refresh token."""
    jwt_service = _get_jwt_service(request)
    user_store = _get_user_store(request)

    from shared.auth.jwt import InvalidTokenError, TokenExpiredError

    try:
        payload = jwt_service.decode_token(body.refresh_token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired — please login again",
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
        )

    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required",
        )

    # Look up user to get current roles (in case they changed)
    user = await user_store.get_user_by_id(payload.sub)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    logger.info("Token refreshed for user: %s", user.user_id)
    return await _issue_tokens(request, user)


@router.get(
    "/azure-ad/config",
    summary="Get Azure AD configuration for frontend",
)
async def get_azure_ad_config(request: Request) -> dict[str, Any]:
    """Return Azure AD client config for frontend MSAL integration.

    Returns empty object if Azure AD is not configured.
    """
    azure_provider = getattr(request.app.state, "azure_ad_provider", None)
    if not azure_provider:
        return {"configured": False}

    return {
        "configured": True,
        "client_id": azure_provider.client_id,
        "tenant_id": azure_provider.tenant_id,
        "authority": f"{azure_provider.AUTHORITY_BASE}/{azure_provider.tenant_id}",
        "scopes": ["openid", "profile", "email", "User.Read"],
    }
