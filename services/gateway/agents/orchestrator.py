"""Orchestrator agent.

Central coordinator that classifies user intent, routes to the appropriate
domain agent, manages tool calls, and streams responses back via SSE.

Design principle: LLM handles intent classification and natural-language
generation only. All computation, routing, data access, and threshold logic
lives in deterministic Python code.
"""

from typing import Any


class OrchestratorAgent:
    """Top-level agent that coordinates chat interactions.

    Responsibilities:
        - Classify user intent (LLM call via LiteLLM)
        - Route to domain agents (PLAgent, RevenueAgent, etc.)
        - Execute tool calls against Service 2 (Computation) APIs
        - Stream typed SSE events back to the client
        - Enforce persona-based visibility (RBAC filtering)
        - Maintain conversation context window

    The orchestrator never sees raw bulk data. It works exclusively
    through the 10 defined tools that map to Service 2 API endpoints.
    """

    async def handle_message(self, message: str, context: dict[str, Any]) -> None:
        """Process a user message and produce an SSE event stream.

        Args:
            message: User's natural-language input.
            context: Current UI filter state (period, BU, account, etc.).
        """
        # TODO: implement intent classification → domain routing → tool execution
        raise NotImplementedError
