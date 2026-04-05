"""Model-agnostic LLM client wrapping LiteLLM.

Supports Claude (Anthropic) and Azure OpenAI. Config-driven model routing.
Graceful fallback when no API key is configured.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import yaml

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around LiteLLM with config-driven model routing.

    The client lazily imports ``litellm`` at call time so tests can mock
    it without installing the full dependency.  When no API key is present
    every method returns a deterministic fallback so the rest of the
    application can operate in template-only mode.
    """

    def __init__(self, settings: Optional[Any] = None) -> None:
        self._settings = settings
        self._routing = self._load_routing()
        self._routing_mtime: float = self._get_routing_mtime()
        self._available = self._check_availability()
        self._provider = os.environ.get("LLM_PROVIDER", self._routing.get("default_provider", "anthropic"))

        if self._available:
            logger.info("LLM client initialised — provider=%s", self._provider)
        else:
            logger.warning(
                "LLM client initialised in fallback mode — no API key configured. "
                "Set ANTHROPIC_API_KEY or AZURE_OPENAI_API_KEY to enable LLM features."
            )

    def reload_routing(self) -> None:
        """Reload model routing config from YAML.

        Called after admin updates model routing via the API.
        Re-reads the YAML file and updates provider + model mappings
        without restarting the service.
        """
        self._routing = self._load_routing()
        self._provider = os.environ.get(
            "LLM_PROVIDER",
            self._routing.get("default_provider", "anthropic"),
        )
        logger.info("AI Agent routing reloaded — provider=%s", self._provider)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when at least one LLM API key is configured."""
        return self._available

    @property
    def provider(self) -> str:
        """Active provider name (``anthropic`` or ``azure``)."""
        return self._provider

    # ------------------------------------------------------------------
    # Model / param lookup
    # ------------------------------------------------------------------

    def get_model(self, task: str) -> str:
        """Return the model identifier for *task* under the active provider.

        Falls back to the provider's ``chat_response`` model, then to a
        hard-coded default. Auto-reloads routing if YAML file changed on disk.
        """
        self._auto_reload_if_changed()
        provider_cfg = self._routing.get("providers", {}).get(self._provider, {})
        task_cfg = provider_cfg.get(task, {})
        if task_cfg.get("model"):
            return task_cfg["model"]

        # Fallback: provider default (chat_response) → hard-coded
        default_cfg = provider_cfg.get("chat_response", {})
        if default_cfg.get("model"):
            return default_cfg["model"]

        return f"{self._provider}/default"

    def get_params(self, task: str) -> dict[str, Any]:
        """Return ``{max_tokens, temperature}`` for the given *task*."""
        provider_cfg = self._routing.get("providers", {}).get(self._provider, {})
        task_cfg = provider_cfg.get(task, {})
        return {
            "max_tokens": task_cfg.get("max_tokens", 1000),
            "temperature": task_cfg.get("temperature", 0.5),
        }

    # ------------------------------------------------------------------
    # Completion (non-streaming)
    # ------------------------------------------------------------------

    async def complete(
        self,
        task: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> Any:
        """Send a chat completion request with retry on rate limits.

        Retries up to ``max_retries`` times with exponential backoff when
        rate-limited (HTTP 429). Returns the raw ``litellm`` response object
        on success, or a dict with ``{"fallback": True, "content": ...}``
        when the LLM is unavailable or all retries are exhausted.
        """
        if not self._available:
            return {"fallback": True, "content": "AI Agent not configured"}

        import asyncio

        for attempt in range(max_retries + 1):
            try:
                import litellm

                kwargs: dict[str, Any] = {
                    "model": self.get_model(task),
                    "messages": messages,
                    **self.get_params(task),
                }
                if tools is not None:
                    kwargs["tools"] = tools
                if tool_choice is not None:
                    kwargs["tool_choice"] = tool_choice

                response = await litellm.acompletion(**kwargs)

                # Log token usage when present
                usage = getattr(response, "usage", None)
                if usage:
                    logger.debug(
                        "LLM usage — task=%s prompt=%s completion=%s total=%s",
                        task,
                        getattr(usage, "prompt_tokens", "?"),
                        getattr(usage, "completion_tokens", "?"),
                        getattr(usage, "total_tokens", "?"),
                    )

                return response

            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = "rate_limit" in exc_str or "429" in exc_str or "rate limit" in exc_str

                if is_rate_limit and attempt < max_retries:
                    wait = 2 ** attempt + 1  # 2s, 3s, 5s
                    logger.warning(
                        "Rate limited (attempt %d/%d) — retrying in %ds",
                        attempt + 1, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                logger.error("LLM completion failed for task=%s: %s", task, exc)
                return {"fallback": True, "content": f"LLM error: {exc}"}

    # ------------------------------------------------------------------
    # Streaming completion
    # ------------------------------------------------------------------

    async def stream(
        self,
        task: str,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        """Yield text chunks from a streaming completion.

        Yields a single fallback message when the client is unavailable or
        an error occurs.
        """
        if not self._available:
            yield "AI Agent not configured. Using template response."
            return

        try:
            import litellm

            response = await litellm.acompletion(
                model=self.get_model(task),
                messages=messages,
                stream=True,
                **self.get_params(task),
            )

            async for chunk in response:
                if not chunk.choices:
                    continue  # Guard: skip empty choices
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content

        except asyncio.TimeoutError:
            logger.error("LLM streaming timed out for task=%s model=%s", task, self.get_model(task))
            yield "\n\n[Response timed out. Please try again.]"
        except Exception as exc:
            logger.error("LLM streaming failed for task=%s: %s", task, exc)
            yield f"\n\n[Error generating response: {exc}]"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auto_reload_if_changed(self) -> None:
        """Check if model_routing.yaml was modified and reload if so."""
        current_mtime = self._get_routing_mtime()
        if current_mtime > self._routing_mtime:
            self.reload_routing()
            self._routing_mtime = current_mtime

    def _get_routing_mtime(self) -> float:
        """Get the modification time of model_routing.yaml."""
        candidates = [
            Path(__file__).resolve().parent.parent / "config" / "model_routing.yaml",
            Path("shared/config/model_routing.yaml"),
        ]
        for path in candidates:
            if path.exists():
                return path.stat().st_mtime
        return 0.0

    def _load_routing(self) -> dict[str, Any]:
        """Load model routing from ``shared/config/model_routing.yaml``."""
        # Try several candidate paths so the file is found regardless of CWD
        candidates = [
            Path(__file__).resolve().parent.parent / "config" / "model_routing.yaml",
            Path("shared/config/model_routing.yaml"),
        ]
        for path in candidates:
            if path.exists():
                with open(path) as fh:
                    return yaml.safe_load(fh) or {}
        logger.warning("model_routing.yaml not found — using empty config")
        return {}

    @staticmethod
    def _check_availability() -> bool:
        """Return ``True`` if at least one LLM API key is present."""
        return bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("AZURE_OPENAI_API_KEY")
        )
