"""Embedding service via LiteLLM.

Generates vector embeddings for text content (narratives, variance context).
Used by RAG pipeline and knowledge base for similarity search.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings using LiteLLM.

    Follows same patterns as shared.llm.client.LLMClient:
    - Lazy litellm import for testability
    - Graceful fallback when API unavailable
    - Config-driven model selection
    """

    def __init__(self, model: Optional[str] = None, dimensions: int = 1536) -> None:
        self._model = model
        self._dimensions = dimensions
        self._available: Optional[bool] = None

        if not model:
            self._load_config()

    def _load_config(self) -> None:
        """Load embedding config from model_routing.yaml."""
        config_paths = [
            Path(__file__).parent.parent / "config" / "model_routing.yaml",
            Path("shared/config/model_routing.yaml"),
        ]
        for p in config_paths:
            if p.exists():
                with open(p) as f:
                    config = yaml.safe_load(f)
                emb = config.get("embedding", {})
                self._model = emb.get("model", "text-embedding-3-small")
                self._dimensions = emb.get("dimensions", 1536)
                return
        self._model = "text-embedding-3-small"

    @property
    def is_available(self) -> bool:
        """Check if embedding API is available."""
        if self._available is not None:
            return self._available
        import os

        has_key = bool(
            os.environ.get("AZURE_OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        self._available = has_key
        return has_key

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> Optional[list[float]]:
        """Generate embedding for a single text string.

        Returns None if service unavailable or on error.
        """
        if not self.is_available or not text:
            return None
        try:
            import litellm

            response = await litellm.aembedding(
                model=self._model,
                input=[text],
            )
            return response.data[0]["embedding"]
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return None

    async def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts.

        Returns list of embeddings (None for failures).
        """
        if not self.is_available or not texts:
            return [None] * len(texts)
        try:
            import litellm

            # Chunk into batches of 100 for rate limit safety
            results: list[Optional[list[float]]] = []
            for i in range(0, len(texts), 100):
                chunk = texts[i : i + 100]
                response = await litellm.aembedding(
                    model=self._model,
                    input=chunk,
                )
                for item in response.data:
                    results.append(item["embedding"])
            return results
        except Exception as exc:
            logger.warning("Batch embedding failed: %s", exc)
            return [None] * len(texts)
