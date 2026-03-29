"""Domain-specific agents.

Each domain agent encapsulates the prompt engineering, tool selection,
and narrative style for a specific area of the P&L. They are invoked
by the OrchestratorAgent after intent classification.
"""

from typing import Any


class PLAgent:
    """P&L overview agent.

    Handles broad questions about the income statement, top-level variances,
    and cross-functional summaries. Produces narratives at the summary and
    board levels.

    Tools used:
        - get_dashboard_summary
        - get_pl_waterfall
        - get_variance_list
        - get_review_stats
    """

    async def generate_response(self, context: dict[str, Any]) -> str:
        """Generate a P&L-focused narrative response.

        Args:
            context: Filter state + intent metadata from orchestrator.

        Returns:
            Narrative text for SSE streaming.
        """
        # TODO: build prompt with RAG examples, call LiteLLM, format response
        raise NotImplementedError


class RevenueAgent:
    """Revenue variance agent.

    Specialises in revenue-line analysis including Volume x Price x Mix x FX
    decomposition, customer/product drill-down, and booking-to-revenue
    bridge explanations.

    Tools used:
        - get_variance_detail
        - get_decomposition
        - get_drill_down
        - get_correlations
        - get_trend_analysis
    """

    async def generate_response(self, context: dict[str, Any]) -> str:
        """Generate a revenue-focused narrative response.

        Args:
            context: Filter state + intent metadata from orchestrator.

        Returns:
            Narrative text for SSE streaming.
        """
        # TODO: build prompt with revenue-specific examples, call LiteLLM
        raise NotImplementedError
