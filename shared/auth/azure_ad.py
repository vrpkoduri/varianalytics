"""Azure AD (Entra ID) OAuth 2.0 provider.

Handles authorization code exchange, user profile retrieval via
Microsoft Graph API, and token refresh. Only activates when
``AZURE_AD_TENANT_ID`` is configured in environment variables.

When Azure AD is not configured, the gateway falls back to local
email/password authentication with JWT.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AzureADTokens:
    """Tokens returned from Azure AD OAuth code exchange."""

    access_token: str
    id_token: str
    refresh_token: str
    expires_in: int = 3600
    token_type: str = "Bearer"


@dataclass
class AzureADUser:
    """User profile from Microsoft Graph API."""

    oid: str  # Azure AD object ID
    email: str
    display_name: str
    given_name: str = ""
    surname: str = ""
    job_title: str = ""
    groups: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class AzureADError(Exception):
    """Raised when Azure AD operations fail."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


# ---------------------------------------------------------------------------
# AzureADProvider
# ---------------------------------------------------------------------------

class AzureADProvider:
    """Azure AD OAuth 2.0 integration via Microsoft identity platform.

    Args:
        tenant_id: Azure AD tenant ID.
        client_id: Application (client) ID registered in Azure AD.
        client_secret: Client secret for the registered application.
    """

    AUTHORITY_BASE = "https://login.microsoftonline.com"
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_url = f"{self.AUTHORITY_BASE}/{tenant_id}/oauth2/v2.0/token"
        self._authorize_url = f"{self.AUTHORITY_BASE}/{tenant_id}/oauth2/v2.0/authorize"

    @property
    def is_configured(self) -> bool:
        """Return True if all required Azure AD settings are present."""
        return bool(self.tenant_id and self.client_id and self.client_secret)

    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str:
        """Build the Azure AD authorization URL for browser redirect.

        Args:
            redirect_uri: OAuth callback URL.
            state: CSRF state parameter.

        Returns:
            Full authorization URL.
        """
        params = (
            f"client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope=openid+profile+email+User.Read"
            f"&response_mode=query"
        )
        if state:
            params += f"&state={state}"
        return f"{self._authorize_url}?{params}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> AzureADTokens:
        """Exchange an authorization code for tokens.

        Args:
            code: Authorization code from Azure AD callback.
            redirect_uri: Must match the redirect_uri used in the authorize request.

        Returns:
            :class:`AzureADTokens` with access, id, and refresh tokens.

        Raises:
            AzureADError: If the exchange fails.
        """
        import httpx

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": "openid profile email User.Read",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._token_url, data=data)

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = error_data.get("error_description", resp.text[:200])
            logger.error("Azure AD token exchange failed: %s", error_desc)
            raise AzureADError(
                f"Token exchange failed: {error_desc}",
                status_code=resp.status_code,
            )

        body = resp.json()
        return AzureADTokens(
            access_token=body["access_token"],
            id_token=body.get("id_token", ""),
            refresh_token=body.get("refresh_token", ""),
            expires_in=body.get("expires_in", 3600),
        )

    async def get_user_info(self, access_token: str) -> AzureADUser:
        """Retrieve user profile from Microsoft Graph API.

        Args:
            access_token: Valid Azure AD access token with User.Read scope.

        Returns:
            :class:`AzureADUser` with profile information.

        Raises:
            AzureADError: If the Graph API call fails.
        """
        import httpx

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.GRAPH_BASE}/me", headers=headers)

        if resp.status_code != 200:
            logger.error("Microsoft Graph /me failed: %s", resp.text[:200])
            raise AzureADError(
                f"Failed to get user info: {resp.status_code}",
                status_code=resp.status_code,
            )

        data = resp.json()

        # Fetch group memberships
        groups: list[str] = []
        try:
            async with httpx.AsyncClient() as client:
                groups_resp = await client.get(
                    f"{self.GRAPH_BASE}/me/memberOf",
                    headers=headers,
                )
            if groups_resp.status_code == 200:
                groups_data = groups_resp.json()
                groups = [
                    g.get("displayName", "")
                    for g in groups_data.get("value", [])
                    if g.get("@odata.type") == "#microsoft.graph.group"
                ]
        except Exception as exc:
            logger.warning("Failed to fetch group memberships: %s", exc)

        return AzureADUser(
            oid=data.get("id", ""),
            email=data.get("mail") or data.get("userPrincipalName", ""),
            display_name=data.get("displayName", ""),
            given_name=data.get("givenName", ""),
            surname=data.get("surname", ""),
            job_title=data.get("jobTitle", ""),
            groups=groups,
            raw=data,
        )

    async def refresh_token(self, refresh_token: str) -> AzureADTokens:
        """Refresh an Azure AD token pair.

        Args:
            refresh_token: Valid refresh token from a previous exchange.

        Returns:
            New :class:`AzureADTokens`.

        Raises:
            AzureADError: If the refresh fails.
        """
        import httpx

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "openid profile email User.Read",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._token_url, data=data)

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = error_data.get("error_description", resp.text[:200])
            raise AzureADError(
                f"Token refresh failed: {error_desc}",
                status_code=resp.status_code,
            )

        body = resp.json()
        return AzureADTokens(
            access_token=body["access_token"],
            id_token=body.get("id_token", ""),
            refresh_token=body.get("refresh_token", refresh_token),
            expires_in=body.get("expires_in", 3600),
        )


def create_azure_ad_provider(
    tenant_id: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
) -> Optional[AzureADProvider]:
    """Factory: create an AzureADProvider if all credentials are available.

    Returns None if Azure AD is not configured, allowing fallback to
    local authentication.
    """
    if not all([tenant_id, client_id, client_secret]):
        logger.info("Azure AD not configured — using local authentication")
        return None

    provider = AzureADProvider(
        tenant_id=tenant_id,  # type: ignore[arg-type]
        client_id=client_id,  # type: ignore[arg-type]
        client_secret=client_secret,  # type: ignore[arg-type]
    )
    logger.info("Azure AD provider configured for tenant %s", tenant_id)
    return provider
