"""Authentication endpoints.

Handles login (Azure AD OAuth 2.0), logout, token refresh, and current-user
lookup. All auth state is managed via JWT tokens signed by the gateway.
"""

from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    """OAuth 2.0 authorization code exchange."""

    code: str = Field(..., description="Authorization code from Azure AD")
    redirect_uri: str


class TokenResponse(BaseModel):
    """JWT token pair returned on login / refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(3600, description="Access token lifetime in seconds")


class UserProfile(BaseModel):
    """Current user profile."""

    user_id: str
    email: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    bu_ids: list[str] = Field(default_factory=list, description="Accessible BU IDs")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange auth code for tokens",
)
async def login(body: LoginRequest) -> TokenResponse:
    """Exchange an Azure AD authorization code for access + refresh tokens."""
    # TODO: validate code with Azure AD, issue JWT
    return TokenResponse(
        access_token="stub-access-token",
        refresh_token="stub-refresh-token",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current session",
)
async def logout() -> None:
    """Revoke the current session / refresh token."""
    # TODO: invalidate refresh token in Redis
    return None


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_current_user() -> UserProfile:
    """Return the authenticated user's profile and role assignments."""
    # TODO: decode JWT, look up user in directory
    return UserProfile(
        user_id="stub-user-001",
        email="analyst@contoso.com",
        display_name="Stub User",
        roles=["analyst"],
        bu_ids=["BU001"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Issue a new access token using a valid refresh token."""
    # TODO: validate refresh token, issue new pair
    return TokenResponse(
        access_token="stub-access-token-refreshed",
        refresh_token="stub-refresh-token-refreshed",
    )
