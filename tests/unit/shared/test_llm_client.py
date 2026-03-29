"""Unit tests for LLM client wrapper."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def mock_streaming_response(chunks: list[str]):
    """Yield mock streaming chunks that mimic LiteLLM's async iterator."""
    for text in chunks:
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = text
        yield mock_chunk


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAvailability:
    """LLMClient.is_available depends on environment API keys."""

    @patch.dict(os.environ, {}, clear=True)
    def test_client_not_available_without_keys(self):
        client = LLMClient()
        assert client.is_available is False

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}, clear=True)
    def test_client_available_with_anthropic_key(self):
        client = LLMClient()
        assert client.is_available is True

    @patch.dict(os.environ, {"AZURE_OPENAI_API_KEY": "az-test-key"}, clear=True)
    def test_client_available_with_azure_key(self):
        client = LLMClient()
        assert client.is_available is True


# ---------------------------------------------------------------------------
# Model / param routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelRouting:
    """get_model and get_params read from the YAML routing config."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    def test_get_model_for_chat_intent(self):
        client = LLMClient()
        model = client.get_model("chat_intent")
        assert "haiku" in model or "claude" in model

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    def test_get_model_for_chat_response(self):
        client = LLMClient()
        model = client.get_model("chat_response")
        assert "sonnet" in model or "claude" in model

    @patch.dict(os.environ, {"AZURE_OPENAI_API_KEY": "az-test", "LLM_PROVIDER": "azure"}, clear=True)
    def test_get_model_azure_provider(self):
        client = LLMClient()
        model = client.get_model("chat_response")
        assert "azure/" in model

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    def test_get_params_for_task(self):
        client = LLMClient()
        params = client.get_params("chat_intent")
        assert "max_tokens" in params
        assert "temperature" in params
        assert params["max_tokens"] == 200
        assert params["temperature"] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# Completion (non-streaming)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComplete:
    """LLMClient.complete returns fallback or delegates to litellm."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_complete_returns_fallback_when_unavailable(self):
        client = LLMClient()
        result = await client.complete("chat_response", [{"role": "user", "content": "hi"}])
        assert isinstance(result, dict)
        assert result["fallback"] is True

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    @patch("litellm.acompletion")
    async def test_complete_calls_litellm(self, mock_acompletion):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_acompletion.return_value = mock_response

        client = LLMClient()
        messages = [{"role": "user", "content": "How did revenue perform?"}]
        result = await client.complete("chat_response", messages)

        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args
        assert call_kwargs.kwargs["model"] == client.get_model("chat_response")
        assert call_kwargs.kwargs["messages"] == messages
        assert result.choices[0].message.content == "Test response"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    @patch("litellm.acompletion", side_effect=Exception("API error"))
    async def test_complete_returns_fallback_on_error(self, _mock):
        client = LLMClient()
        result = await client.complete("chat_response", [{"role": "user", "content": "hi"}])
        assert isinstance(result, dict)
        assert result["fallback"] is True
        assert "error" in result["content"].lower()


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStream:
    """LLMClient.stream yields text chunks or fallback messages."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_stream_yields_fallback_when_unavailable(self):
        client = LLMClient()
        chunks = []
        async for chunk in client.stream("chat_response", [{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert "not configured" in chunks[0].lower()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    @patch("litellm.acompletion")
    async def test_stream_yields_tokens(self, mock_acompletion):
        expected_chunks = ["Hello", " ", "world", "!"]
        mock_acompletion.return_value = mock_streaming_response(expected_chunks)

        client = LLMClient()
        collected: list[str] = []
        async for chunk in client.stream("chat_response", [{"role": "user", "content": "hi"}]):
            collected.append(chunk)

        assert collected == expected_chunks

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "LLM_PROVIDER": "anthropic"}, clear=True)
    @patch("litellm.acompletion", side_effect=Exception("Stream error"))
    async def test_stream_yields_error_on_failure(self, _mock):
        client = LLMClient()
        chunks = []
        async for chunk in client.stream("chat_response", [{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert "error" in chunks[0].lower()
