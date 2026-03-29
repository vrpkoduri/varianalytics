"""LLM-powered narrative generation for FP&A variance analysis.

Takes real financial data from the Computation Service and generates
professional narratives streamed token-by-token via SSE.
Falls back to templates when the LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from services.gateway.agents.intent import Intent
from services.gateway.agents.templates import format_response
from services.gateway.streaming.context import StreamingContext
from shared.llm.client import LLMClient

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generate financial narratives via LLM with template fallback."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client
        self._prompts = self._load_prompts()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the underlying LLM client is available."""
        return self._llm.is_available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_streaming(
        self,
        agent_type: str,
        intent: Intent,
        data_context: dict[str, Any],
        streaming_ctx: StreamingContext,
    ) -> None:
        """Stream a narrative into *streaming_ctx* token-by-token.

        Falls back to the template system when the LLM is unavailable,
        emitting the entire template response as a single token event.
        """
        if not self.is_available:
            fallback_text = format_response(intent, data_context)
            await streaming_ctx.emit_token(fallback_text)
            return

        messages = self._build_messages(agent_type, intent, data_context)
        async for chunk in self._llm.stream(task="chat_response", messages=messages):
            await streaming_ctx.emit_token(chunk)

    async def generate_complete(
        self,
        agent_type: str,
        intent: Intent,
        data_context: dict[str, Any],
    ) -> str:
        """Return a complete narrative string (non-streaming).

        Falls back to the template system when the LLM is unavailable.
        """
        if not self.is_available:
            return format_response(intent, data_context)

        messages = self._build_messages(agent_type, intent, data_context)
        response = await self._llm.complete(task="chat_response", messages=messages)

        if isinstance(response, dict) and response.get("fallback"):
            return format_response(intent, data_context)

        # Extract content from litellm response
        try:
            return response.choices[0].message.content
        except (AttributeError, IndexError):
            return format_response(intent, data_context)

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        agent_type: str,
        intent: Intent,
        data_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Build the message list for an LLM call."""
        system_content = self._get_system_prompt(agent_type)
        data_text = self._format_data_context(intent, data_context)

        return [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": (
                    f"Based on the following financial data, provide a concise "
                    f"{intent.value.replace('_', ' ')} analysis:\n\n{data_text}"
                ),
            },
        ]

    def _get_system_prompt(self, agent_type: str) -> str:
        """Retrieve the system prompt for *agent_type* from the YAML config."""
        prompt_entry = self._prompts.get(agent_type, self._prompts.get("pl_agent", {}))
        return prompt_entry.get("content", "You are a senior FP&A analyst AI assistant.")

    @staticmethod
    def _format_data_context(intent: Intent, data: dict[str, Any]) -> str:
        """Convert a raw data dict into LLM-friendly text.

        Each intent type gets its own formatting logic so the prompt is
        clear and well-structured for the model.
        """
        if intent == Intent.REVENUE_OVERVIEW:
            lines = ["Revenue Performance Data:"]
            if "actual" in data:
                lines.append(
                    f"- Total Revenue: Actual ${data.get('actual', 0):,.0f}, "
                    f"Budget ${data.get('comparator', 0):,.0f}, "
                    f"Variance ${data.get('variance', 0):,.0f} "
                    f"({data.get('pct', 'N/A')})"
                )
            if "top_variances" in data:
                lines.append("- Top Variances:")
                for tv in data["top_variances"]:
                    lines.append(
                        f"  - {tv.get('name', 'Unknown')}: "
                        f"${tv.get('variance', 0):,.0f} ({tv.get('pct', 'N/A')})"
                    )
            return "\n".join(lines)

        if intent == Intent.PL_SUMMARY:
            lines = ["P&L Summary Data:"]
            if "cards" in data:
                for card in data["cards"]:
                    lines.append(
                        f"- {card.get('label', '')}: "
                        f"Actual ${card.get('actual', 0):,.0f}, "
                        f"Variance ${card.get('variance', 0):,.0f} "
                        f"({card.get('pct', 'N/A')})"
                    )
            return "\n".join(lines)

        if intent == Intent.WATERFALL:
            lines = ["Revenue Bridge Data:"]
            if "steps" in data:
                for step in data["steps"]:
                    lines.append(
                        f"- {step.get('label', '')}: ${step.get('value', 0):,.0f}"
                    )
            return "\n".join(lines)

        if intent == Intent.TREND:
            periods = data.get("periods", "?")
            lines = [f"Trend Data ({periods} months):"]
            if "data_points" in data:
                for dp in data["data_points"]:
                    lines.append(
                        f"- {dp.get('period', '')}: ${dp.get('actual', 0):,.0f} "
                        f"(vs budget ${dp.get('budget', 0):,.0f})"
                    )
            return "\n".join(lines)

        if intent == Intent.DECOMPOSITION:
            lines = ["Variance Decomposition:"]
            if "components" in data:
                for comp in data["components"]:
                    lines.append(
                        f"- {comp.get('label', '')}: ${comp.get('value', 0):,.0f} "
                        f"({comp.get('pct', 'N/A')})"
                    )
            return "\n".join(lines)

        if intent == Intent.REVIEW_STATUS:
            lines = ["Review Queue:"]
            if "stats" in data:
                stats = data["stats"]
                lines.append(f"- Total items: {stats.get('total', 0)}")
                lines.append(f"- AI Draft: {stats.get('ai_draft', 0)}")
                lines.append(f"- Reviewed: {stats.get('reviewed', 0)}")
                lines.append(f"- Approved: {stats.get('approved', 0)}")
            return "\n".join(lines)

        # Default: JSON dump
        try:
            return json.dumps(data, indent=2, default=str)
        except (TypeError, ValueError):
            return str(data)

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    def _load_prompts(self) -> dict[str, Any]:
        """Load system prompts from ``services/gateway/prompts/system_prompts.yaml``."""
        candidates = [
            Path(__file__).resolve().parent.parent.parent
            / "services"
            / "gateway"
            / "prompts"
            / "system_prompts.yaml",
            Path("services/gateway/prompts/system_prompts.yaml"),
        ]
        for path in candidates:
            if path.exists():
                with open(path) as fh:
                    return yaml.safe_load(fh) or {}
        logger.warning("system_prompts.yaml not found — using built-in defaults")
        return {}
