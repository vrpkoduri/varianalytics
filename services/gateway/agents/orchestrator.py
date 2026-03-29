"""Orchestrator agent.

Central coordinator that classifies user intent, routes to the appropriate
domain agent, manages tool calls, and streams responses back via SSE.

Design principle: LLM handles intent classification and natural-language
generation only. All computation, routing, data access, and threshold logic
lives in deterministic Python code.

Sprint 1: Template-based responses (keyword intent + template narrative).
Sprint 1 SD-14: LiteLLM integration (drop-in replacement).
"""

from __future__ import annotations

import logging
from typing import Any

from services.gateway.agents.domain_agents import PLAgent, RevenueAgent, ReviewAgent
from services.gateway.agents.intent import (
    ExtractedEntities,
    Intent,
    KeywordIntentClassifier,
    LLMIntentClassifier,
)
from services.gateway.agents.templates import format_response, get_suggestions
from services.gateway.agents.tools import ToolExecutor
from services.gateway.clients.computation_client import ComputationClient
from services.gateway.streaming.context import StreamingContext
from shared.data.review_store import ReviewStore
from shared.llm.client import LLMClient
from shared.llm.narrative import NarrativeGenerator

logger = logging.getLogger("gateway.orchestrator")

# Intent → domain agent routing
_REVENUE_INTENTS = {
    Intent.REVENUE_OVERVIEW,
    Intent.DECOMPOSITION,
    Intent.TREND,
    Intent.WATERFALL,
    Intent.HEATMAP,
}

_PL_INTENTS = {
    Intent.PL_SUMMARY,
    Intent.VARIANCE_DETAIL,
    Intent.DRILL_DOWN,
}

_REVIEW_INTENTS = {
    Intent.REVIEW_STATUS,
}


class OrchestratorAgent:
    """Top-level agent that coordinates chat interactions.

    Responsibilities:
        - Classify user intent (keyword-based, upgradeable to LLM)
        - Route to domain agents (PLAgent, RevenueAgent, ReviewAgent)
        - Execute tool calls against Computation Service APIs
        - Stream typed SSE events back to the client
        - Enforce persona-based visibility (RBAC — future)
        - Maintain conversation context window

    The orchestrator never sees raw bulk data. It works exclusively
    through the 10 defined tools that map to Computation Service endpoints.
    """

    def __init__(
        self,
        computation_client: ComputationClient,
        review_store: ReviewStore,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize the orchestrator with its dependencies.

        Args:
            computation_client: HTTP client for Computation Service.
            review_store: In-memory review/approval state.
            llm_client: Optional LLM client. If provided and available,
                        uses LLM for intent classification and narrative
                        generation. Falls back to keyword+templates otherwise.
        """
        # Intent classifier: LLM if available, else keyword
        if llm_client and llm_client.is_available:
            self._classifier = LLMIntentClassifier(llm_client)
            logger.info("Using LLM intent classifier (%s)", llm_client.provider)
        else:
            self._classifier = KeywordIntentClassifier()
            logger.info("Using keyword intent classifier (LLM not available)")

        # Narrative generator: LLM if available, else templates
        narrative_gen = None
        if llm_client and llm_client.is_available:
            narrative_gen = NarrativeGenerator(llm_client)
            logger.info("Using LLM narrative generation")

        self._tool_executor = ToolExecutor(computation_client)
        self._revenue_agent = RevenueAgent(self._tool_executor, narrative_gen)
        self._pl_agent = PLAgent(self._tool_executor, narrative_gen)
        self._review_agent = ReviewAgent(review_store)

    async def handle_message(
        self,
        message: str,
        context: dict[str, Any],
        streaming_ctx: StreamingContext,
    ) -> None:
        """Process a user message and produce an SSE event stream.

        Pipeline:
            1. Classify intent + extract entities
            2. Merge entities with UI context (period, BU, view, base)
            3. Route to appropriate domain agent
            4. Agent calls tools → formats response → emits SSE events
            5. Emit follow-up suggestions + done

        Args:
            message: User's natural-language input.
            context: Current UI filter state (period_id, bu_id, etc.).
            streaming_ctx: SSE streaming context to emit events on.
        """
        try:
            # Step 1: Classify intent (async for LLM, sync for keyword)
            if isinstance(self._classifier, LLMIntentClassifier):
                intent, entities = await self._classifier.classify(message, ui_context=context)
            else:
                intent, entities = self._classifier.classify(message, ui_context=context)
            logger.info(
                "Intent: %s | Entities: period=%s bu=%s account=%s",
                intent.value,
                entities.period_id,
                entities.bu_id,
                entities.account_id,
            )

            # Step 2: Merge entities with UI context defaults
            merged_context = self._merge_context(entities, context)

            # Step 3+4: Route to domain agent
            if intent in _REVENUE_INTENTS:
                await self._revenue_agent.generate_response(
                    intent, entities, merged_context, streaming_ctx,
                )
            elif intent in _PL_INTENTS:
                await self._pl_agent.generate_response(
                    intent, entities, merged_context, streaming_ctx,
                )
            elif intent in _REVIEW_INTENTS:
                await self._review_agent.generate_response(
                    intent, entities, merged_context, streaming_ctx,
                )
            elif intent == Intent.NETTING:
                await self._revenue_agent.generate_netting_response(
                    entities, merged_context, streaming_ctx,
                )
            else:
                # General fallback
                response = format_response(Intent.GENERAL, {})
                await streaming_ctx.emit_token(response)

            # Step 5: Emit suggestions + done
            suggestions = get_suggestions(intent)
            if suggestions:
                await streaming_ctx.emit_suggestion(suggestions)

            await streaming_ctx.emit_done()

        except Exception as exc:
            logger.exception("Error in orchestrator: %s", exc)
            await streaming_ctx.emit_error(
                f"An error occurred while processing your request: {exc}",
                code="ORCHESTRATOR_ERROR",
            )
            await streaming_ctx.emit_done()

    def _merge_context(
        self, entities: ExtractedEntities, ui_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge extracted entities with UI context. Entities take precedence."""
        merged = dict(ui_context) if ui_context else {}

        # Entity values override UI context
        if entities.period_id:
            merged["period_id"] = entities.period_id
        if entities.bu_id:
            merged["bu_id"] = entities.bu_id
        if entities.account_id:
            merged["account_id"] = entities.account_id
        if entities.view_id:
            merged["view_id"] = entities.view_id
        if entities.base_id:
            merged["base_id"] = entities.base_id
        if entities.dimension:
            merged["dimension"] = entities.dimension

        # Ensure defaults exist
        merged.setdefault("period_id", "2025-12")
        merged.setdefault("view_id", "MTD")
        merged.setdefault("base_id", "BUDGET")

        return merged
