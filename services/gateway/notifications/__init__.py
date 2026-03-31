"""Notification dispatchers for Teams, Slack, and Email."""
from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional

from shared.config.settings import Settings

from .teams import TeamsNotifier
from .slack import SlackNotifier
from .smtp import SMTPNotifier

__all__ = ["TeamsNotifier", "SlackNotifier", "SMTPNotifier", "notify_event"]

logger = logging.getLogger(__name__)


async def notify_event(
    event_type: str,
    context: dict[str, Any],
    settings: Optional[Settings] = None,
) -> list[tuple[str, bool]]:
    """Dispatch notification to all configured channels.

    Args:
        event_type: One of 'engine_complete', 'review_needed', 'approval_needed', 'report_ready'
        context: Event-specific data (title, body, facts, etc.)
        settings: App settings. If None, loads from environment.

    Returns:
        List of (channel_name, success) tuples.
    """
    if settings is None:
        settings = Settings()

    title = context.get("title", f"Vantage: {event_type}")
    body = context.get("body", "")
    action_url = context.get("action_url")

    tasks = []
    channel_names = []

    # Teams
    if settings.teams_webhook_url:
        notifier = TeamsNotifier(settings.teams_webhook_url)
        tasks.append(notifier.send(
            title, body,
            facts=context.get("facts"),
            action_url=action_url,
        ))
        channel_names.append("teams")

    # Slack
    if settings.slack_webhook_url:
        notifier = SlackNotifier(settings.slack_webhook_url)
        tasks.append(notifier.send(
            title, body,
            fields=context.get("fields", context.get("facts")),
            action_url=action_url,
        ))
        channel_names.append("slack")

    # Email
    if settings.smtp_host and context.get("recipients"):
        notifier = SMTPNotifier(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_address=settings.notification_from_email,
        )
        tasks.append(notifier.send(
            to=context["recipients"],
            subject=title,
            html_body=f"<h2>{title}</h2><p>{body}</p>",
            attachments=context.get("attachments"),
        ))
        channel_names.append("email")

    if not tasks:
        logger.info("No notification channels configured for event: %s", event_type)
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    outcome = []
    for name, result in zip(channel_names, results):
        success = result is True
        if isinstance(result, Exception):
            logger.error("Notification failed for %s: %s", name, result)
            success = False
        outcome.append((name, success))
        logger.info("Notification %s via %s: %s", event_type, name, "sent" if success else "failed")

    return outcome
