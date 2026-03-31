"""Tests for EmbeddingService."""

import pytest
from unittest.mock import patch

from shared.knowledge.embedding import EmbeddingService


class TestEmbeddingService:
    def test_auto_detects_provider_with_voyage_key(self):
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "test-key"}, clear=True):
            svc = EmbeddingService()
            assert svc.provider == "voyage"
            assert svc._model == "voyage-3-lite"
            assert svc.dimensions == 1024

    def test_auto_detects_provider_with_openai_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            svc = EmbeddingService()
            assert svc.provider == "openai"
            assert svc._model == "text-embedding-3-small"
            assert svc.dimensions == 1536

    def test_custom_model(self):
        svc = EmbeddingService(model="custom-model", dimensions=768)
        assert svc._model == "custom-model"
        assert svc.dimensions == 768

    def test_unavailable_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            svc = EmbeddingService()
            assert svc.is_available is False
            assert svc.provider is None

    @pytest.mark.asyncio
    async def test_embed_returns_none_when_unavailable(self):
        svc = EmbeddingService()
        svc._available = False
        result = await svc.embed("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_embed_batch_returns_nones_when_unavailable(self):
        svc = EmbeddingService()
        svc._available = False
        results = await svc.embed_batch(["text1", "text2"])
        assert results == [None, None]
