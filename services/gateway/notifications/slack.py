"""Slack notification via incoming webhook."""
from __future__ import annotations
import logging
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Sends Block Kit messages to Slack."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url

    async def send(
        self, title: str, body: str, *,
        webhook_url: Optional[str] = None,
        fields: Optional[list[dict[str, str]]] = None,
        action_url: Optional[str] = None,
    ) -> bool:
        url = webhook_url or self.webhook_url
        if not url:
            logger.warning("Slack: no webhook URL configured")
            return False

        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": body[:3000]}},
        ]

        if fields:
            field_blocks = [
                {"type": "mrkdwn", "text": f"*{f.get('title', '')}*\n{f.get('value', '')}"}
                for f in fields[:10]
            ]
            blocks.append({"type": "section", "fields": field_blocks})

        if action_url:
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View in Vantage"},
                    "url": action_url,
                    "style": "primary",
                }],
            })

        payload = {"blocks": blocks}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                # Slack returns "ok" as plain text on success
                success = resp.status_code == 200
                if not success:
                    logger.warning("Slack webhook returned %d: %s", resp.status_code, resp.text[:200])
                return success
        except Exception as exc:
            logger.error("Slack notification failed: %s", exc)
            return False
