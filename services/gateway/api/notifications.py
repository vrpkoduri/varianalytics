"""Notification configuration and testing endpoints.

Manage Teams, Slack, and SMTP notification channels. Supports sending
test notifications to verify connectivity before production use.
"""

from typing import Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from services.gateway.notifications.teams import TeamsNotifier
from services.gateway.notifications.slack import SlackNotifier
from services.gateway.notifications.smtp import SMTPNotifier

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
    from shared.config.settings import Settings
    settings = Settings()

    success = False
    detail = ""

    if body.channel == "teams":
        notifier = TeamsNotifier(settings.teams_webhook_url)
        success = await notifier.send(body.message or "Test notification", "This is a test from Marsh Vantage", webhook_url=body.recipient)
        detail = "Sent to Teams" if success else "Teams webhook failed or not configured"
    elif body.channel == "slack":
        notifier = SlackNotifier(settings.slack_webhook_url)
        success = await notifier.send(body.message or "Test notification", "This is a test from Marsh Vantage", webhook_url=body.recipient)
        detail = "Sent to Slack" if success else "Slack webhook failed or not configured"
    elif body.channel == "email":
        notifier = SMTPNotifier(host=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_user, password=settings.smtp_password, from_address=settings.notification_from_email)
        recipients = [body.recipient] if body.recipient else []
        success = await notifier.send(recipients, body.message or "Test", "<h2>Test</h2><p>This is a test from Marsh Vantage</p>") if recipients else False
        detail = "Sent via email" if success else "SMTP not configured or no recipient"

    return NotificationTestResponse(channel=body.channel, success=success, detail=detail)


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
