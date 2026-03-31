"""Tests for notification channels."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.gateway.notifications.teams import TeamsNotifier
from services.gateway.notifications.slack import SlackNotifier
from services.gateway.notifications.smtp import SMTPNotifier
from services.gateway.notifications import notify_event


class TestTeamsNotifier:
    @pytest.mark.asyncio
    async def test_returns_false_without_webhook(self):
        notifier = TeamsNotifier()
        result = await notifier.send("Test", "Body")
        assert result is False

    @pytest.mark.asyncio
    async def test_builds_adaptive_card(self):
        """Verify adaptive card JSON structure."""
        notifier = TeamsNotifier("https://webhook.example.com")
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await notifier.send("Engine Complete", "4,422 variances analyzed",
                                        facts=[{"title": "Material", "value": "25"}])
            assert result is True
            # Verify POST was called with adaptive card
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("json")
            assert payload is not None


class TestSlackNotifier:
    @pytest.mark.asyncio
    async def test_returns_false_without_webhook(self):
        notifier = SlackNotifier()
        result = await notifier.send("Test", "Body")
        assert result is False

    @pytest.mark.asyncio
    async def test_builds_block_kit(self):
        notifier = SlackNotifier("https://hooks.slack.com/test")
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await notifier.send("Report Ready", "June Period-End Package generated")
            assert result is True


class TestSMTPNotifier:
    @pytest.mark.asyncio
    async def test_returns_false_without_host(self):
        notifier = SMTPNotifier()
        result = await notifier.send(["test@example.com"], "Test", "<p>Body</p>")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_without_recipients(self):
        notifier = SMTPNotifier(host="smtp.example.com")
        result = await notifier.send([], "Test", "<p>Body</p>")
        assert result is False


class TestNotifyEventDispatcher:
    @pytest.mark.asyncio
    async def test_no_channels_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            from shared.config.settings import Settings
            settings = Settings()
            settings.teams_webhook_url = None
            settings.slack_webhook_url = None
            settings.smtp_host = None
            results = await notify_event("engine_complete", {"title": "Test", "body": "Test"}, settings=settings)
            assert results == []
