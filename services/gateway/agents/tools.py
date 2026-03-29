"""Tool executor — maps agent tool names to Computation Service API calls.

Each tool name from tool_definitions.yaml is mapped to a handler method
that calls the corresponding ComputationClient method with the right params.
"""

from __future__ import annotations

import logging
from typing import Any

from services.gateway.clients.computation_client import (
    ComputationClient,
    ComputationServiceError,
)

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes named tools by delegating to ComputationClient methods.

    Usage::

        executor = ToolExecutor(client)
        result = await executor.execute("get_dashboard_summary", {"period_id": "2026-03"})
    """

    def __init__(self, client: ComputationClient) -> None:
        self._client = client

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict | None:
        """Execute a tool by name.

        Args:
            tool_name: One of the 10 tool names from tool_definitions.yaml.
            params: Parameters extracted from the user message / LLM function call.

        Returns:
            Response dict from the Computation Service, or None on error.
        """
        handler = self._TOOL_MAP.get(tool_name)
        if not handler:
            logger.warning("Unknown tool: %s", tool_name)
            return None
        try:
            return await handler(self, params)
        except ComputationServiceError as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return None

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    async def _get_dashboard_summary(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_summary_cards(
            period_id=params["period_id"],
            bu_id=params.get("bu_id"),
            view_id=params.get("view", "MTD"),
            base_id=params.get("base", "BUDGET"),
        )

    async def _get_variance_list(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_variance_list(
            period_id=params["period_id"],
            bu_id=params.get("bu_id"),
            view_id=params.get("view_id", "MTD"),
            base_id=params.get("base_id", "BUDGET"),
            pl_category=params.get("pl_category"),
            page=params.get("page", 1),
            page_size=params.get("limit", 20),
        )

    async def _get_variance_detail(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_variance_detail(
            variance_id=params["variance_id"],
        )

    async def _get_decomposition(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_decomposition(
            variance_id=params["variance_id"],
        )

    async def _get_drill_down(self, params: dict[str, Any]) -> dict | None:
        """Drill into a variance by account — uses variance_by_account or account_detail."""
        # If we have an account_id, use the account detail endpoint
        if "account_id" in params:
            return await self._client.get_account_detail(
                account_id=params["account_id"],
                period_id=params.get("period_id", ""),
                bu_id=params.get("bu_id"),
                view_id=params.get("view_id", "MTD"),
                base_id=params.get("base_id", "BUDGET"),
            )
        # Fall back to variance detail if we have a variance_id
        if "variance_id" in params:
            return await self._client.get_variance_detail(
                variance_id=params["variance_id"],
            )
        return None

    async def _get_correlations(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_correlations(
            variance_id=params["variance_id"],
        )

    async def _get_trend_analysis(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_trends(
            bu_id=params.get("bu_id"),
            account_id=params.get("account_id", "acct_gross_revenue"),
            base_id=params.get("base_id", "BUDGET"),
            periods=params.get("lookback_months", 12),
        )

    async def _get_pl_waterfall(self, params: dict[str, Any]) -> dict | None:
        return await self._client.get_waterfall(
            period_id=params["period_id"],
            bu_id=params.get("bu_id"),
            base_id=params.get("base", "BUDGET"),
        )

    async def _get_netting_alerts(self, params: dict[str, Any]) -> dict | None:
        """Get netting alerts — maps to netting drilldown endpoint."""
        return await self._client.get_netting(
            node_id=params.get("node_id", ""),
            period_id=params["period_id"],
        )

    async def _get_review_stats(self, params: dict[str, Any]) -> dict | None:
        """Get review stats — placeholder until review service is wired."""
        # Review stats endpoint is on the gateway itself, not computation.
        # For Sprint 1, return a stub.
        return {
            "total": 0,
            "ai_draft": 0,
            "analyst_reviewed": 0,
            "approved": 0,
            "message": "Review stats not yet connected to computation service.",
        }

    # ------------------------------------------------------------------
    # Tool dispatch map
    # ------------------------------------------------------------------

    _TOOL_MAP: dict[str, Any] = {
        "get_dashboard_summary": _get_dashboard_summary,
        "get_variance_list": _get_variance_list,
        "get_variance_detail": _get_variance_detail,
        "get_decomposition": _get_decomposition,
        "get_drill_down": _get_drill_down,
        "get_correlations": _get_correlations,
        "get_trend_analysis": _get_trend_analysis,
        "get_pl_waterfall": _get_pl_waterfall,
        "get_netting_alerts": _get_netting_alerts,
        "get_review_stats": _get_review_stats,
    }
