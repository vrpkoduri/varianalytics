"""Domain-specific agents.

Each domain agent encapsulates the tool selection, data fetching, and
narrative formatting for a specific area of the P&L. They are invoked
by the OrchestratorAgent after intent classification.

Sprint 1: Template-based responses using real data from Computation Service.
Sprint 1 SD-14: LLM-generated narratives using system prompts from YAML.
"""

from __future__ import annotations

import logging
from typing import Any

from services.gateway.agents.intent import ExtractedEntities, Intent
from services.gateway.agents.templates import (
    build_variance_table_data,
    format_currency,
    format_pct,
    format_response,
)
from services.gateway.agents.tools import ToolExecutor
from services.gateway.streaming.context import StreamingContext
from shared.data.review_store import ReviewStore
from shared.llm.narrative import NarrativeGenerator

logger = logging.getLogger("gateway.agents")


class RevenueAgent:
    """Revenue variance specialist.

    Handles revenue overview, decomposition, trends, waterfall, heatmap.
    Calls Computation Service via ToolExecutor for real data.
    Uses LLM narrative generation when available, falls back to templates.
    """

    def __init__(
        self, tool_executor: ToolExecutor,
        narrative_gen: NarrativeGenerator | None = None,
    ) -> None:
        self._tools = tool_executor
        self._narrative_gen = narrative_gen

    async def generate_response(
        self,
        intent: Intent,
        entities: ExtractedEntities,
        context: dict[str, Any],
        streaming_ctx: StreamingContext,
    ) -> None:
        """Generate a revenue-focused response with real data.

        Fetches data → formats narrative → emits SSE events.
        """
        period_id = context.get("period_id", "2025-12")
        bu_id = context.get("bu_id")
        base_id = context.get("base_id", "BUDGET")

        if intent == Intent.REVENUE_OVERVIEW:
            await self._handle_revenue_overview(
                period_id, bu_id, base_id, streaming_ctx,
            )
        elif intent == Intent.WATERFALL:
            await self._handle_waterfall(period_id, bu_id, base_id, streaming_ctx)
        elif intent == Intent.HEATMAP:
            await self._handle_heatmap(period_id, base_id, streaming_ctx)
        elif intent == Intent.TREND:
            account_id = context.get("account_id", "acct_gross_revenue")
            await self._handle_trend(
                bu_id, account_id, base_id, streaming_ctx,
            )
        elif intent == Intent.DECOMPOSITION:
            await self._handle_decomposition(period_id, bu_id, base_id, streaming_ctx)
        else:
            # Fallback revenue response
            await self._handle_revenue_overview(
                period_id, bu_id, base_id, streaming_ctx,
            )

    async def _handle_revenue_overview(
        self, period_id: str, bu_id: str | None,
        base_id: str, ctx: StreamingContext,
    ) -> None:
        """Revenue overview: summary cards + top variances table."""
        # Fetch summary cards
        summary = await self._tools.execute("get_dashboard_summary", {
            "period_id": period_id,
            "bu_id": bu_id,
            "base_id": base_id,
        })

        # Fetch top revenue variances
        variances = await self._tools.execute("get_variance_list", {
            "period_id": period_id,
            "bu_id": bu_id,
            "base_id": base_id,
            "pl_category": "Revenue",
            "page_size": 10,
        })

        # Build narrative from data
        data = self._build_revenue_data(summary, variances, period_id, base_id)

        # Emit narrative: LLM if available, else template
        if self._narrative_gen and self._narrative_gen.is_available:
            await self._narrative_gen.generate_streaming(
                agent_type="revenue_agent",
                intent=Intent.REVENUE_OVERVIEW,
                data_context=data,
                streaming_ctx=ctx,
            )
        else:
            narrative = format_response(Intent.REVENUE_OVERVIEW, data)
            await ctx.emit_token(narrative)

        # Emit variance table
        if variances and variances.get("items"):
            columns, rows = build_variance_table_data(variances["items"])
            await ctx.emit_data_table(
                title="Top Revenue Variances",
                columns=columns,
                rows=rows,
            )

        # Emit confidence
        await ctx.emit_confidence(0.85, "high")

    async def _handle_waterfall(
        self, period_id: str, bu_id: str | None,
        base_id: str, ctx: StreamingContext,
    ) -> None:
        """Revenue waterfall bridge chart."""
        waterfall = await self._tools.execute("get_pl_waterfall", {
            "period_id": period_id,
            "bu_id": bu_id,
            "base_id": base_id,
        })

        data = {"period_id": period_id, "base_id": base_id}
        if waterfall:
            data["steps"] = waterfall if isinstance(waterfall, list) else waterfall.get("steps", [])

        narrative = format_response(Intent.WATERFALL, data)
        await ctx.emit_token(narrative)

        # Emit chart data
        if waterfall:
            steps = waterfall if isinstance(waterfall, list) else waterfall.get("steps", [])
            await ctx.emit_mini_chart(
                chart_type="waterfall",
                title="Revenue Bridge",
                data=steps,
            )

    async def _handle_heatmap(
        self, period_id: str, base_id: str, ctx: StreamingContext,
    ) -> None:
        """Variance heatmap by Geo × BU."""
        heatmap = await self._tools.execute("get_dashboard_summary", {
            "period_id": period_id,
            "base_id": base_id,
        })

        data = {"period_id": period_id, "base_id": base_id, "heatmap": heatmap}
        narrative = format_response(Intent.HEATMAP, data)
        await ctx.emit_token(narrative)

    async def _handle_trend(
        self, bu_id: str | None, account_id: str,
        base_id: str, ctx: StreamingContext,
    ) -> None:
        """Account trend over time."""
        trends = await self._tools.execute("get_trend_analysis", {
            "bu_id": bu_id,
            "account_id": account_id,
            "base_id": base_id,
            "periods": 12,
        })

        data = {
            "account_id": account_id,
            "base_id": base_id,
            "trends": trends if isinstance(trends, list) else (trends or {}).get("data", []),
        }
        narrative = format_response(Intent.TREND, data)
        await ctx.emit_token(narrative)

        # Emit trend chart
        if trends:
            chart_data = trends if isinstance(trends, list) else trends.get("data", [])
            if chart_data:
                await ctx.emit_mini_chart(
                    chart_type="line",
                    title=f"{account_id} Trend",
                    data=chart_data,
                )

    async def _handle_decomposition(
        self, period_id: str, bu_id: str | None,
        base_id: str, ctx: StreamingContext,
    ) -> None:
        """Revenue variance decomposition."""
        # Get top revenue variance to decompose
        variances = await self._tools.execute("get_variance_list", {
            "period_id": period_id,
            "bu_id": bu_id,
            "base_id": base_id,
            "pl_category": "Revenue",
            "page_size": 1,
        })

        if variances and variances.get("items"):
            vid = variances["items"][0].get("variance_id")
            if vid:
                decomp = await self._tools.execute("get_decomposition", {
                    "variance_id": vid,
                })
                data = {
                    "period_id": period_id,
                    "variance": variances["items"][0],
                    "decomposition": decomp,
                }
                narrative = format_response(Intent.DECOMPOSITION, data)
                await ctx.emit_token(narrative)
                return

        await ctx.emit_token(format_response(Intent.DECOMPOSITION, {}))

    async def generate_netting_response(
        self, entities: ExtractedEntities,
        context: dict[str, Any], ctx: StreamingContext,
    ) -> None:
        """Netting analysis response."""
        period_id = context.get("period_id", "2025-12")

        # Use netting tool — map to netting endpoint
        netting = await self._tools.execute("get_netting_alerts", {
            "period_id": period_id,
        })

        data = {"period_id": period_id, "netting": netting}
        narrative = format_response(Intent.NETTING, data)
        await ctx.emit_token(narrative)

    def _build_revenue_data(
        self,
        summary: dict | None,
        variances: dict | None,
        period_id: str,
        base_id: str,
    ) -> dict[str, Any]:
        """Build template data dict from API responses."""
        data: dict[str, Any] = {
            "period_id": period_id,
            "period_label": period_id,
            "base_id": base_id,
            "base_label": base_id.title(),
        }

        if summary and summary.get("cards"):
            for card in summary["cards"]:
                if "Revenue" in card.get("metric_name", ""):
                    data["actual"] = card.get("actual", 0)
                    data["comparator"] = card.get("comparator", 0)
                    data["variance_amount"] = card.get("variance_amount", 0)
                    data["variance_pct"] = card.get("variance_pct")
                    data["is_favorable"] = card.get("is_favorable", False)
                    data["direction"] = "up" if data["variance_amount"] > 0 else "down"
                    break

        if variances and variances.get("items"):
            data["top_variances"] = variances["items"][:5]
            data["total_variance_count"] = variances.get("total_count", len(variances["items"]))

        return data


class PLAgent:
    """P&L overview agent.

    Handles broad P&L questions, variance detail, drill-down.
    Uses LLM narrative generation when available, falls back to templates.
    """

    def __init__(
        self, tool_executor: ToolExecutor,
        narrative_gen: NarrativeGenerator | None = None,
    ) -> None:
        self._tools = tool_executor
        self._narrative_gen = narrative_gen

    async def generate_response(
        self,
        intent: Intent,
        entities: ExtractedEntities,
        context: dict[str, Any],
        streaming_ctx: StreamingContext,
    ) -> None:
        """Generate a P&L-focused response with real data."""
        period_id = context.get("period_id", "2025-12")
        bu_id = context.get("bu_id")
        base_id = context.get("base_id", "BUDGET")

        if intent == Intent.PL_SUMMARY:
            await self._handle_pl_summary(period_id, bu_id, base_id, streaming_ctx)
        elif intent == Intent.VARIANCE_DETAIL:
            account_id = entities.account_id or context.get("account_id")
            await self._handle_variance_detail(
                period_id, bu_id, base_id, account_id, streaming_ctx,
            )
        elif intent == Intent.DRILL_DOWN:
            account_id = entities.account_id or context.get("account_id")
            await self._handle_drill_down(
                period_id, bu_id, base_id, account_id, streaming_ctx,
            )
        else:
            await self._handle_pl_summary(period_id, bu_id, base_id, streaming_ctx)

    async def _handle_pl_summary(
        self, period_id: str, bu_id: str | None,
        base_id: str, ctx: StreamingContext,
    ) -> None:
        """Full P&L summary with summary cards."""
        summary = await self._tools.execute("get_dashboard_summary", {
            "period_id": period_id,
            "bu_id": bu_id,
            "base_id": base_id,
        })

        data = {
            "period_id": period_id,
            "period_label": period_id,
            "base_id": base_id,
            "base_label": base_id.title(),
            "cards": summary.get("cards", []) if summary else [],
        }
        # Emit narrative: LLM if available, else template
        if self._narrative_gen and self._narrative_gen.is_available:
            await self._narrative_gen.generate_streaming(
                agent_type="pl_agent",
                intent=Intent.PL_SUMMARY,
                data_context=data,
                streaming_ctx=ctx,
            )
        else:
            narrative = format_response(Intent.PL_SUMMARY, data)
            await ctx.emit_token(narrative)

        # Emit summary table
        if summary and summary.get("cards"):
            columns = ["Metric", "Actual", "Budget", "Variance $", "Variance %"]
            rows = []
            for card in summary["cards"]:
                rows.append([
                    card.get("metric_name", ""),
                    format_currency(card.get("actual", 0)),
                    format_currency(card.get("comparator", 0)),
                    format_currency(card.get("variance_amount", 0)),
                    format_pct(card.get("variance_pct")),
                ])
            await ctx.emit_data_table(
                title="P&L Summary",
                columns=columns,
                rows=rows,
            )

    async def _handle_variance_detail(
        self, period_id: str, bu_id: str | None,
        base_id: str, account_id: str | None,
        ctx: StreamingContext,
    ) -> None:
        """Variance detail for a specific account."""
        if account_id:
            detail = await self._tools.execute("get_drill_down", {
                "account_id": account_id,
                "period_id": period_id,
                "bu_id": bu_id,
                "base_id": base_id,
            })
        else:
            detail = None

        data = {"period_id": period_id, "account_id": account_id, "detail": detail}
        narrative = format_response(Intent.VARIANCE_DETAIL, data)
        await ctx.emit_token(narrative)

    async def _handle_drill_down(
        self, period_id: str, bu_id: str | None,
        base_id: str, account_id: str | None,
        ctx: StreamingContext,
    ) -> None:
        """Drill down into an account."""
        # Same as variance detail for now
        await self._handle_variance_detail(
            period_id, bu_id, base_id, account_id, ctx,
        )


class ReviewAgent:
    """Review queue status agent.

    Handles review status queries using the ReviewStore (direct, no HTTP).
    """

    def __init__(self, review_store: ReviewStore) -> None:
        self._store = review_store

    async def generate_response(
        self,
        intent: Intent,
        entities: ExtractedEntities,
        context: dict[str, Any],
        streaming_ctx: StreamingContext,
    ) -> None:
        """Generate review status response."""
        stats = self._store.get_review_stats()

        data = {
            "total_pending": stats.get("total_pending", 0),
            "ai_draft": stats.get("ai_draft", 0),
            "analyst_reviewed": stats.get("analyst_reviewed", 0),
            "escalated": stats.get("escalated", 0),
            "dismissed": stats.get("dismissed", 0),
            "approved": stats.get("approved", 0),
        }
        narrative = format_response(Intent.REVIEW_STATUS, data)
        await streaming_ctx.emit_token(narrative)
