"""Notification configuration and testing endpoints.

Manage Teams, Slack, and SMTP notification channels. Supports sending
test notifications to verify connectivity before production use.
"""

from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class NotificationTestRequest(BaseModel):
    """Send a test notification through a specific channel."""

    channel: str = Field(..., description="One of: teams, slack, smtp")
    recipient: Optional[str] = Field(
        None, description="Override recipient (email or webhook URL)"
    )
    message: str = "Test notification from Variance Agent"


class NotificationTestResponse(BaseModel):
    """Result of a test notification send."""

    channel: str
    success: bool
    detail: str = ""


class ChannelConfig(BaseModel):
    """Configuration for a single notification channel."""

    channel: str
    enabled: bool = False
    webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    from_address: Optional[str] = None


class NotificationConfig(BaseModel):
    """Full notification configuration across all channels."""

    channels: list[ChannelConfig] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/test",
    response_model=NotificationTestResponse,
    summary="Send a test notification",
)
async def send_test_notification(
    body: NotificationTestRequest,
) -> NotificationTestResponse:
    """Send a test notification through the specified channel to verify setup."""
    # TODO: dispatch via TeamsNotifier / SlackNotifier / SMTPNotifier
    return NotificationTestResponse(
        channel=body.channel,
        success=True,
        detail=f"Test notification sent via {body.channel} (stub)",
    )


@router.get(
    "/config",
    response_model=NotificationConfig,
    summary="Get notification configuration",
)
async def get_notification_config() -> NotificationConfig:
    """Return current notification channel configuration."""
    # TODO: read from config store
    return NotificationConfig(
        channels=[
            ChannelConfig(channel="teams", enabled=False),
            ChannelConfig(channel="slack", enabled=False),
            ChannelConfig(channel="smtp", enabled=False),
        ]
    )


@router.put(
    "/config",
    response_model=NotificationConfig,
    summary="Update notification configuration",
)
async def update_notification_config(body: NotificationConfig) -> NotificationConfig:
    """Update notification channel configuration."""
    # TODO: persist to config store, validate webhook URLs
    return body
