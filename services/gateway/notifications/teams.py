"""Microsoft Teams notification via incoming webhook."""
from __future__ import annotations
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)


class TeamsNotifier:
    """Sends adaptive card messages to Microsoft Teams."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url

    async def send(
        self, title: str, body: str, *,
        webhook_url: Optional[str] = None,
        facts: Optional[list[dict[str, str]]] = None,
        action_url: Optional[str] = None,
    ) -> bool:
        url = webhook_url or self.webhook_url
        if not url:
            logger.warning("Teams: no webhook URL configured")
            return False

        # Build Adaptive Card v1.4
        card_body: list[dict[str, Any]] = [
            {"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Medium", "color": "Accent"},
            {"type": "TextBlock", "text": body, "wrap": True},
        ]

        if facts:
            card_body.append({
                "type": "FactSet",
                "facts": [{"title": f.get("title", ""), "value": f.get("value", "")} for f in facts],
            })

        actions = []
        if action_url:
            actions.append({"type": "Action.OpenUrl", "title": "View in Vantage", "url": action_url})

        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": card_body,
                    "actions": actions,
                },
            }],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                success = resp.status_code in (200, 202)
                if not success:
                    logger.warning("Teams webhook returned %d: %s", resp.status_code, resp.text[:200])
                return success
        except Exception as exc:
            logger.error("Teams notification failed: %s", exc)
            return False
