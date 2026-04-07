"""Multi-provider embedding service via LiteLLM.

Generates vector embeddings for text content (narratives, variance context).
Auto-detects the best available provider based on configured API keys:

1. Voyage AI (voyage-3-lite) — when VOYAGE_API_KEY set (Anthropic partner)
2. OpenAI (text-embedding-3-small) — when OPENAI_API_KEY set
3. Azure OpenAI (azure/text-embedding-3-small) — when AZURE_OPENAI_API_KEY + AZURE_API_BASE set
4. Skip — when no embedding provider available (RAG degrades gracefully)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Provider configs: (env_key_required, model, dimensions, extra_check)
_PROVIDERS = [
    {
        "name": "voyage",
        "env_key": "VOYAGE_API_KEY",
        "model": "voyage-3-lite",
        "dimensions": 1024,
        "extra_check": None,
    },
    {
        "name": "openai",
        "env_key": "OPENAI_API_KEY",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "extra_check": None,
    },
    {
        "name": "azure",
        "env_key": "AZURE_OPENAI_API_KEY",
        "model": "azure/mmc-tech-text-embedding-3-small",
        "dimensions": 1536,
        "extra_check": "AZURE_API_BASE",  # Also requires API base
    },
]


class EmbeddingService:
    """Multi-provider embedding service with auto-detection.

    Automatically selects the best available embedding provider:
    - Voyage AI when using Anthropic/Claude (recommended partner)
    - OpenAI text-embedding-3-small (direct)
    - Azure OpenAI text-embedding-3-small (enterprise)
    - Skip when no provider available

    Follows same patterns as shared.llm.client.LLMClient:
    - Lazy litellm import for testability
    - Graceful fallback when API unavailable
    - Config-driven with auto-detection override
    """

    def __init__(
        self,
        model: Optional[str] = None,
        dimensions: int = 0,
        provider: Optional[str] = None,
    ) -> None:
        """Initialize embedding service.

        Args:
            model: Override model name. If None, auto-detect from available keys.
            dimensions: Override dimensions. If 0, use provider default.
            provider: Force a specific provider ('voyage', 'openai', 'azure').
        """
        self._model = model
        self._dimensions = dimensions
        self._provider_name: Optional[str] = provider
        self._available: Optional[bool] = None
        self._checked = False

        if not model:
            self._auto_detect()

    def _auto_detect(self) -> None:
        """Auto-detect the best available embedding provider."""
        # First try config file for explicit override
        config = self._load_config()
        if config and config.get("provider"):
            forced = config["provider"]
            providers = config.get("providers", {})
            if forced in providers:
                p = providers[forced]
                self._model = p.get("model")
                self._dimensions = p.get("dimensions", 1536)
                self._provider_name = forced
                logger.info("Embedding: using configured provider '%s' (%s)", forced, self._model)
                return

        # Auto-detect from available API keys
        for p in _PROVIDERS:
            key = os.environ.get(p["env_key"])
            if key:
                # Check extra requirement (e.g., Azure needs API base too)
                if p["extra_check"] and not os.environ.get(p["extra_check"]):
                    continue
                self._model = p["model"]
                self._dimensions = p["dimensions"]
                self._provider_name = p["name"]
                logger.info(
                    "Embedding: auto-detected provider '%s' (%s, %dd)",
                    p["name"], p["model"], p["dimensions"],
                )
                return

        # No provider available
        self._model = None
        self._dimensions = 0
        self._provider_name = None
        self._available = False
        logger.info("Embedding: no provider available (set VOYAGE_API_KEY, OPENAI_API_KEY, or AZURE_OPENAI_API_KEY)")

    def _load_config(self) -> Optional[dict[str, Any]]:
        """Load embedding config from model_routing.yaml."""
        config_paths = [
            Path(__file__).parent.parent / "config" / "model_routing.yaml",
            Path("shared/config/model_routing.yaml"),
        ]
        for p in config_paths:
            if p.exists():
                with open(p) as f:
                    config = yaml.safe_load(f)
                return config.get("embedding", {})
        return None

    @property
    def is_available(self) -> bool:
        """Check if embedding API is available."""
        if self._available is not None:
            return self._available
        self._available = self._model is not None
        return self._available

    @property
    def dimensions(self) -> int:
        """Vector dimensions for the selected model."""
        return self._dimensions or 1536

    @property
    def provider(self) -> Optional[str]:
        """Name of the active embedding provider."""
        return self._provider_name

    @property
    def model(self) -> Optional[str]:
        """Model identifier for the active provider."""
        return self._model

    def _get_extra_kwargs(self) -> dict[str, Any]:
        """Return extra kwargs for litellm embedding calls (e.g., api_base for Azure)."""
        kwargs: dict[str, Any] = {}
        if self._provider_name == "azure":
            api_base = os.environ.get("AZURE_API_BASE") or os.environ.get("AZURE_OPENAI_ENDPOINT")
            if api_base:
                kwargs["api_base"] = api_base
            api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
            kwargs["api_version"] = api_version
        return kwargs

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
                **self._get_extra_kwargs(),
            )
            return response.data[0]["embedding"]
        except Exception as exc:
            logger.warning("Embedding failed (%s): %s", self._provider_name, exc)
            return None

    async def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts.

        Returns list of embeddings (None for failures).
        Chunks into batches of 100 for rate limit safety.
        """
        if not self.is_available or not texts:
            return [None] * len(texts)
        try:
            import litellm

            extra = self._get_extra_kwargs()
            results: list[Optional[list[float]]] = []
            for i in range(0, len(texts), 100):
                chunk = texts[i : i + 100]
                response = await litellm.aembedding(
                    model=self._model,
                    input=chunk,
                    **extra,
                )
                for item in response.data:
                    results.append(item["embedding"])
            return results
        except Exception as exc:
            logger.warning("Batch embedding failed (%s): %s", self._provider_name, exc)
            return [None] * len(texts)
