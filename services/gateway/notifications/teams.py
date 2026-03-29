"""Microsoft Teams notification integration.

Sends adaptive-card notifications to Teams channels via incoming webhooks.
Used for: variance alerts, review-needed, approval-needed, SLA warnings.
"""

from typing import Any, Optional


class TeamsNotifier:
    """Send notifications to Microsoft Teams channels.

    Uses incoming webhook URLs configured per channel. Messages are
    formatted as Teams adaptive cards with action buttons linking
    back to the variance agent UI.
    """

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        """Initialise with an optional default webhook URL.

        Args:
            webhook_url: Default Teams incoming webhook URL.
        """
        self.webhook_url = webhook_url

    async def send(
        self,
        title: str,
        body: str,
        *,
        webhook_url: Optional[str] = None,
        facts: Optional[list[dict[str, str]]] = None,
        action_url: Optional[str] = None,
    ) -> bool:
        """Send an adaptive-card message to Teams.

        Args:
            title: Card title / headline.
            body: Card body text.
            webhook_url: Override webhook URL for this message.
            facts: Key-value pairs displayed in the card.
            action_url: URL for the "Open in App" button.

        Returns:
            True if the webhook accepted the payload.
        """
        # TODO: build adaptive card JSON, POST to webhook via httpx
        raise NotImplementedError
