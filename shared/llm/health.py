"""LLM Health Checker — cached status + connectivity testing.

Provides health status (provider, models, key configured) and a
connectivity test that sends a cheap test prompt and measures latency.
Results are cached for 5 minutes to avoid unnecessary API calls.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Tasks defined in model_routing.yaml
_TASKS = [
    "chat_intent",
    "chat_response",
    "narrative_generation",
    "hypothesis_generation",
    "oneliner_generation",
]

_TEST_PROMPT = (
    "Summarize in exactly one sentence: "
    "Revenue increased by $50K (5%) vs Budget due to strong consulting demand."
)


class LLMHealthChecker:
    """Cached LLM health status and connectivity testing."""

    _CACHE_TTL = 300  # 5 minutes

    def __init__(self, llm_client: Any) -> None:
        self._client = llm_client
        self._cache: Optional[dict[str, Any]] = None
        self._cache_time: float = 0

    def get_health_status(self) -> dict[str, Any]:
        """Return cached health status for the LLM provider.

        Returns:
            Dict with: status, provider, endpoint, api_key_configured,
            models (per task with model name and cost).
        """
        now = time.time()
        if self._cache and (now - self._cache_time) < self._CACHE_TTL:
            return self._cache

        available = self._client.is_available
        provider = self._client.provider if available else "none"
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", os.environ.get("AZURE_API_BASE", ""))

        models: list[dict[str, Any]] = []
        for task in _TASKS:
            try:
                model = self._client.get_model(task)
                cost = self._client.get_cost(task)
                models.append({
                    "task": task,
                    "model": model,
                    "cost_input_per_1m": cost.get("cost_input_per_1m", 0),
                    "cost_output_per_1m": cost.get("cost_output_per_1m", 0),
                })
            except Exception:
                models.append({
                    "task": task,
                    "model": "unknown",
                    "cost_input_per_1m": 0,
                    "cost_output_per_1m": 0,
                })

        status = "healthy" if available else "unavailable"

        result = {
            "status": status,
            "provider": provider,
            "endpoint": endpoint,
            "api_key_configured": available,
            "models": models,
            "checked_at": time.time(),
        }

        self._cache = result
        self._cache_time = now
        return result

    async def test_connectivity(self) -> dict[str, Any]:
        """Send a cheap test prompt and measure latency.

        Returns:
            Dict with: success, provider, model, response_text, latency_ms, tokens.
        """
        if not self._client.is_available:
            return {
                "success": False,
                "provider": "none",
                "model": "none",
                "response_text": "LLM not configured — set AZURE_OPENAI_API_KEY in .env",
                "latency_ms": 0,
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        task = "oneliner_generation"  # Cheapest model
        model = self._client.get_model(task)

        start = time.monotonic()
        try:
            response = await self._client.complete(
                task=task,
                messages=[{"role": "user", "content": _TEST_PROMPT}],
                max_retries=1,
            )

            latency_ms = int((time.monotonic() - start) * 1000)

            # Handle fallback response (LLM unavailable)
            if isinstance(response, dict) and response.get("fallback"):
                return {
                    "success": False,
                    "provider": self._client.provider,
                    "model": model,
                    "response_text": response.get("content", "Fallback — LLM unavailable"),
                    "latency_ms": latency_ms,
                    "tokens": {"prompt": 0, "completion": 0, "total": 0},
                }

            # Extract response text
            choice = response.choices[0] if response.choices else None
            text = choice.message.content if choice else "No response"

            # Extract token usage
            usage = getattr(response, "usage", None)
            tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completion": getattr(usage, "completion_tokens", 0) if usage else 0,
                "total": getattr(usage, "total_tokens", 0) if usage else 0,
            }

            # Invalidate cache so next health check reflects connectivity
            self._cache = None

            return {
                "success": True,
                "provider": self._client.provider,
                "model": model,
                "response_text": text,
                "latency_ms": latency_ms,
                "tokens": tokens,
            }

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning("LLM connectivity test failed: %s", exc)
            return {
                "success": False,
                "provider": self._client.provider,
                "model": model,
                "response_text": f"Error: {exc}",
                "latency_ms": latency_ms,
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }
