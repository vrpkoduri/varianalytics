"""Pass 5 — Multi-Level Narrative Generation (Parallel LLM + Context Enrichment).

Enhanced with:
- **Context enrichment**: Each variance's LLM prompt includes correlations,
  netting patterns, trends, decomposition drivers, and sibling variances
  from Passes 1-4.
- **Parallel batching**: asyncio.gather with Semaphore(10) for 10x throughput.
- **Template fallback**: Guaranteed output even when LLM fails.

Generates four narrative levels for each material variance:
1. detail   — Full analyst narrative with root cause and related drivers.
2. midlevel — BU-leader summary.
3. summary  — CFO-level one sentence.
4. oneliner — Dashboard one-liner.
5. board    — None (on-demand only).

Output: populates context["narratives"], context["review_status"],
and context["audit_entries"].
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd

from shared.models.enums import ComparisonBase, NarrativeSource, ReviewStatus
from shared.utils.audit import create_audit_entry
from shared.utils.formatting import (
    format_currency_thousands,
    format_percentage,
    sign_convention_label,
)

logger = logging.getLogger(__name__)

# Friendly labels for comparison bases
_BASE_LABELS: dict[str, str] = {
    "BUDGET": "Budget",
    "FORECAST": "Forecast",
    "PRIOR_YEAR": "Prior Year",
}

# Max concurrent LLM calls
_CONCURRENCY = 10


# ======================================================================
# Context Enrichment — pre-compute relationship maps from Passes 1-4
# ======================================================================


def _build_context_maps(context: dict[str, Any]) -> dict[str, Any]:
    """Pre-index all relationship data from prior passes for O(1) lookup.

    If a knowledge graph is available in context["knowledge_graph"],
    delegates to _context_maps_from_graph() for graph-backed lookups.
    Otherwise falls back to the legacy dict-building logic.

    Returns dict with 5 maps: correlations, netting, trends,
    decomposition, siblings.
    """
    graph = context.get("knowledge_graph")
    if graph is not None:
        try:
            return _context_maps_from_graph(graph, context)
        except Exception:
            logger.warning(
                "Graph-backed context maps failed — falling back to legacy",
                exc_info=True,
            )

    return _build_context_maps_legacy(context)


def _context_maps_from_graph(graph: Any, context: dict[str, Any]) -> dict[str, Any]:
    """Build the 5 context maps using knowledge graph queries.

    Produces the same output format as _build_context_maps_legacy() so
    callers (_build_enriched_prompt, template/LLM generators) are unaffected.
    """
    from shared.knowledge.graph_interface import VarianceGraph

    assert isinstance(graph, VarianceGraph)

    # 1. Correlations map: variance_id → [correlated partners]
    corr_map: dict[str, list[dict]] = {}
    material = context.get("material_variances")
    if isinstance(material, pd.DataFrame) and not material.empty:
        for vid in material["variance_id"].dropna().unique():
            vid_str = str(vid)
            correlations = graph.get_correlations(vid_str)
            if correlations:
                corr_map[vid_str] = correlations

    # 2. Netting map: parent_node_id → netting details
    netting_map: dict[str, dict] = {}
    netting = context.get("netting_flags")
    if isinstance(netting, pd.DataFrame) and not netting.empty:
        for _, row in netting.iterrows():
            key = str(row.get("parent_node_id", ""))
            node_data = graph.get_node(key)
            if node_data and "netting" in node_data:
                netting_map[key] = node_data["netting"]
            else:
                # Fallback: read directly from DataFrame
                netting_map[key] = {
                    "net_variance": row.get("net_variance", 0),
                    "gross_variance": row.get("gross_variance", 0),
                    "netting_ratio": row.get("netting_ratio", 0),
                    "check_type": row.get("check_type", ""),
                }

    # 3. Trends map: account_id → best trend
    trend_map: dict[str, dict] = {}
    acct_meta = context.get("acct_meta", {})
    for acct_id in acct_meta:
        trend = graph._get_trend_for_account(acct_id) if hasattr(graph, '_get_trend_for_account') else None
        if trend:
            trend_map[acct_id] = trend

    # 4. Decomposition map: variance_id → components
    decomp_map: dict[str, dict] = {}
    if isinstance(material, pd.DataFrame) and not material.empty:
        for vid in material["variance_id"].dropna().unique():
            vid_str = str(vid)
            node = graph.get_node(vid_str)
            if node and "decomposition" in node:
                decomp_map[vid_str] = node["decomposition"]

    # 5. Siblings map: parent_account → [sibling variance summaries]
    sibling_map: dict[str, list[dict]] = {}
    if isinstance(material, pd.DataFrame) and not material.empty:
        for _, row in material.iterrows():
            acct_id = str(row.get("account_id", ""))
            parent = acct_meta.get(acct_id, {}).get("parent_id")
            if parent:
                sibling_map.setdefault(parent, []).append({
                    "account_id": acct_id,
                    "account_name": acct_meta.get(acct_id, {}).get("account_name", acct_id),
                    "variance_amount": row.get("variance_amount", 0),
                    "variance_pct": row.get("variance_pct", 0),
                })

    # ------------------------------------------------------------------
    # Intelligence dimensions (Phase 3F+3G+3H — 15 total)
    # ------------------------------------------------------------------
    intelligence_maps = _build_intelligence_maps(
        material=material,
        acct_meta=acct_meta,
        decomp_map=decomp_map,
        corr_map=corr_map,
        graph=graph,
        period_id=context.get("period_id", ""),
    )

    logger.info("Context maps built from knowledge graph (with %d intelligence dimensions)", len(intelligence_maps))

    return {
        "correlations": corr_map,
        "netting": netting_map,
        "trends": trend_map,
        "decomposition": decomp_map,
        "siblings": sibling_map,
        **intelligence_maps,
    }


def _build_intelligence_maps(
    material: Any,
    acct_meta: dict[str, Any],
    decomp_map: dict[str, dict],
    corr_map: dict[str, list],
    graph: Any,
    period_id: str,
) -> dict[str, Any]:
    """Pre-compute all 15 intelligence dimensions for context enrichment.

    Returns dict with keys: materiality, risk, projection, persistence,
    pivot, peer, causal, multi_year, anomaly, budget, market.
    Each value is a dict[variance_id, intelligence_result].
    """
    maps: dict[str, Any] = {}

    if not isinstance(material, pd.DataFrame) or material.empty:
        return maps

    try:
        from shared.intelligence.materiality import compute_materiality_context
        from shared.intelligence.risk import classify_risk
        from shared.intelligence.projection import compute_cumulative_projection
        from shared.intelligence.persistence import compute_persistence
        from shared.intelligence.pivot import compute_dimensional_pivot
        from shared.intelligence.peer_comparison import compute_peer_comparison
        from shared.intelligence.causal_chains import compute_causal_chain
        from shared.intelligence.multi_year import compute_multi_year_pattern
        from shared.intelligence.anomaly import compute_anomaly_score
        from shared.intelligence.budget_assumptions import compute_budget_gap
        from shared.intelligence.market_context import compute_market_context

        # Period totals for materiality (revenue, EBITDA, etc.)
        period_totals = _compute_period_totals(material, period_id)

        materiality_map: dict[str, dict] = {}
        risk_map: dict[str, dict] = {}
        projection_map: dict[str, dict] = {}
        persistence_map: dict[str, dict] = {}
        pivot_map: dict[str, dict] = {}
        peer_map: dict[str, dict] = {}
        causal_map: dict[str, dict] = {}
        multi_year_map: dict[str, dict] = {}
        anomaly_map: dict[str, dict] = {}
        budget_map: dict[str, dict] = {}

        for vid in material["variance_id"].dropna().unique():
            vid_str = str(vid)
            row = material[material["variance_id"] == vid].iloc[0]
            amount = float(row.get("variance_amount", 0))
            pct = float(row.get("variance_pct", 0)) if pd.notna(row.get("variance_pct")) else 0
            acct_id = str(row.get("account_id", ""))
            bu_id = str(row.get("bu_id", ""))
            pl_cat = str(row.get("pl_category", acct_meta.get(acct_id, {}).get("pl_category", "")))

            # Period history from graph
            history = []
            if graph and hasattr(graph, "get_period_history"):
                history = graph.get_period_history(acct_id, bu_id, n_periods=36)

            # Phase 3F: Quick Intelligence
            materiality_map[vid_str] = compute_materiality_context(amount, period_totals)
            risk_map[vid_str] = classify_risk(decomp_map.get(vid_str), pl_cat)
            projection_map[vid_str] = compute_cumulative_projection(amount, period_id, history)
            persistence_map[vid_str] = compute_persistence(history)

            # Phase 3G: Core Intelligence
            pivot_map[vid_str] = compute_dimensional_pivot(vid_str, material, acct_id)

            peers = []
            if graph and hasattr(graph, "get_peer_variances"):
                peers = graph.get_peer_variances(vid_str)
            peer_map[vid_str] = compute_peer_comparison(peers, bu_id, amount)

            causal_map[vid_str] = compute_causal_chain(corr_map.get(vid_str, []), acct_meta)
            multi_year_map[vid_str] = compute_multi_year_pattern(history, period_id)

            # Phase 3H: Quality
            anomaly_map[vid_str] = compute_anomaly_score(amount, history)
            budget_map[vid_str] = compute_budget_gap(pct, period_id, pl_cat)

        # Market context — computed once per period, shared across all variances
        market = compute_market_context(period_id)

        maps = {
            "materiality": materiality_map,
            "risk": risk_map,
            "projection": projection_map,
            "persistence": persistence_map,
            "pivot": pivot_map,
            "peer": peer_map,
            "causal": causal_map,
            "multi_year": multi_year_map,
            "anomaly": anomaly_map,
            "budget": budget_map,
            "market": market,
        }

    except Exception:
        logger.warning("Intelligence maps computation failed — continuing without intelligence", exc_info=True)

    return maps


def _compute_period_totals(material: pd.DataFrame, period_id: str) -> dict[str, float]:
    """Compute P&L totals for materiality context."""
    totals: dict[str, float] = {}
    period_data = material[material["period_id"] == period_id] if "period_id" in material.columns else material

    for pl_cat, label in [("Revenue", "revenue"), ("COGS", "cogs"), ("OpEx", "opex")]:
        cat_data = period_data[period_data["pl_category"] == pl_cat] if "pl_category" in period_data.columns else pd.DataFrame()
        if not cat_data.empty:
            totals[label] = float(cat_data["variance_amount"].abs().sum())

    # EBITDA = Revenue - COGS - OpEx
    totals["ebitda"] = totals.get("revenue", 0) - totals.get("cogs", 0) - totals.get("opex", 0)

    return totals


def _build_context_maps_legacy(context: dict[str, Any]) -> dict[str, Any]:
    """Legacy context map builder — pre-index from DataFrames for O(1) lookup.

    Returns dict with 5 maps: correlations, netting, trends,
    decomposition, siblings.
    """
    # 1. Correlations: variance_id → [correlated partners]
    corr_map: dict[str, list[dict]] = {}
    correlations = context.get("correlations")
    if isinstance(correlations, pd.DataFrame) and not correlations.empty:
        for _, row in correlations.iterrows():
            vid_a = row.get("variance_id_a", "")
            vid_b = row.get("variance_id_b", "")
            score = row.get("correlation_score", 0)
            hyp = row.get("hypothesis")
            for vid, partner in [(vid_a, vid_b), (vid_b, vid_a)]:
                corr_map.setdefault(vid, []).append(
                    {"partner_id": partner, "score": score, "hypothesis": hyp}
                )

    # 2. Netting: parent_node_id → netting details
    netting_map: dict[str, dict] = {}
    netting = context.get("netting_flags")
    if isinstance(netting, pd.DataFrame) and not netting.empty:
        for _, row in netting.iterrows():
            key = row.get("parent_node_id", "")
            netting_map[key] = {
                "net_variance": row.get("net_variance", 0),
                "gross_variance": row.get("gross_variance", 0),
                "netting_ratio": row.get("netting_ratio", 0),
                "check_type": row.get("check_type", ""),
            }

    # 3. Trends: account_id → best (longest) trend
    trend_map: dict[str, dict] = {}
    trends = context.get("trend_flags")
    if isinstance(trends, pd.DataFrame) and not trends.empty:
        for _, row in trends.iterrows():
            acct = row.get("account_id", "")
            periods = row.get("consecutive_periods", 0)
            if acct not in trend_map or periods > trend_map[acct].get(
                "consecutive_periods", 0
            ):
                trend_map[acct] = {
                    "direction": row.get("direction", ""),
                    "consecutive_periods": periods,
                    "cumulative_amount": row.get("cumulative_amount", 0),
                }

    # 4. Decomposition: variance_id → components
    decomp_map: dict[str, dict] = {}
    decomp = context.get("decomposition")
    if isinstance(decomp, pd.DataFrame) and not decomp.empty:
        for _, row in decomp.iterrows():
            vid = row.get("variance_id", "")
            components = row.get("components", {})
            if isinstance(components, str):
                try:
                    components = json.loads(components)
                except (json.JSONDecodeError, TypeError):
                    components = {}
            decomp_map[vid] = {
                "method": row.get("method", ""),
                "components": components if isinstance(components, dict) else {},
            }

    # 5. Siblings: parent_account → [sibling variance summaries]
    sibling_map: dict[str, list[dict]] = {}
    material = context.get("material_variances")
    acct_meta = context.get("acct_meta", {})
    if isinstance(material, pd.DataFrame) and not material.empty:
        for _, row in material.iterrows():
            acct_id = row.get("account_id", "")
            parent = acct_meta.get(acct_id, {}).get("parent_id")
            if parent:
                sibling_map.setdefault(parent, []).append(
                    {
                        "account_id": acct_id,
                        "account_name": acct_meta.get(acct_id, {}).get(
                            "account_name", acct_id
                        ),
                        "variance_amount": row.get("variance_amount", 0),
                        "variance_pct": row.get("variance_pct", 0),
                    }
                )

    return {
        "correlations": corr_map,
        "netting": netting_map,
        "trends": trend_map,
        "decomposition": decomp_map,
        "siblings": sibling_map,
    }


def _build_enriched_prompt(
    var_dict: dict[str, Any],
    acct_meta: dict[str, Any],
    context_maps: dict[str, Any],
) -> str:
    """Build context-rich prompt with cause-and-effect relationships."""
    variance_id = var_dict.get("variance_id", "")
    account_id = var_dict.get("account_id", "")
    parent_id = acct_meta.get("parent_id", "")

    sections: list[str] = []

    # Base variance info
    sections.append(f"Account: {acct_meta.get('account_name', account_id)}")
    sections.append(
        f"Variance: ${var_dict.get('variance_amount', 0):,.0f} "
        f"({var_dict.get('variance_pct', 0):.1f}%)"
    )
    sections.append(f"Category: {acct_meta.get('pl_category', 'Unknown')}")
    sections.append(
        f"BU: {var_dict.get('bu_id', 'All')}, Period: {var_dict.get('period_id', '')}"
    )

    # Decomposition drivers
    decomp = context_maps["decomposition"].get(variance_id)
    if decomp and decomp.get("components"):
        comps = decomp["components"]
        comp_strs = [
            f"{k}: ${v:,.0f}"
            for k, v in comps.items()
            if isinstance(v, (int, float)) and k not in ("residual", "method")
        ]
        if comp_strs:
            sections.append(
                f"\nDecomposition ({decomp['method']}): {', '.join(comp_strs)}"
            )

    # Correlated variances
    corrs = context_maps["correlations"].get(variance_id, [])
    if corrs:
        corr_strs = []
        for c in corrs[:3]:
            hyp = f" — {c['hypothesis']}" if c.get("hypothesis") else ""
            corr_strs.append(f"  - {c['partner_id']} (score: {c['score']:.2f}){hyp}")
        sections.append(f"\nCorrelated variances:\n" + "\n".join(corr_strs))

    # Trend context
    trend = context_maps["trends"].get(account_id)
    if trend:
        sections.append(
            f"\nTrend: {trend['direction']} for {trend['consecutive_periods']} "
            f"consecutive months, cumulative ${trend['cumulative_amount']:,.0f}"
        )

    # Netting context (try multiple key formats)
    bu = var_dict.get("bu_id", "")
    cc = var_dict.get("costcenter_node_id", "")
    geo = var_dict.get("geo_node_id", "")
    netting_key = f"{bu}|{cc}|{geo}"
    netting = context_maps["netting"].get(netting_key) or context_maps["netting"].get(
        account_id
    )
    if netting:
        sections.append(
            f"\nNetting alert: Net ${netting['net_variance']:,.0f} masks "
            f"gross ${netting['gross_variance']:,.0f} "
            f"(ratio {netting['netting_ratio']:.1f}x)"
        )

    # Sibling context
    siblings = context_maps["siblings"].get(parent_id, [])
    others = [s for s in siblings if s["account_id"] != account_id][:4]
    if others:
        sib_strs = [
            f"  - {s['account_name']}: ${s['variance_amount']:,.0f} ({s['variance_pct']:.1f}%)"
            for s in others
        ]
        sections.append(
            f"\nSibling variances under same parent:\n" + "\n".join(sib_strs)
        )

    # Intelligence context (Phase 3F+3G+3H — 15 dimensions)
    intel_notes = _collect_intelligence_notes(variance_id, context_maps)
    if intel_notes:
        sections.append(f"\nIntelligence Context:\n" + "\n".join(f"  - {n}" for n in intel_notes))

    return "\n".join(sections)


def _collect_intelligence_notes(
    variance_id: str,
    context_maps: dict[str, Any],
) -> list[str]:
    """Collect non-empty intelligence notes for a variance.

    Checks all 11 intelligence dimension keys in context_maps.
    Returns up to 6 most relevant notes (avoids narrative bloat).
    """
    notes: list[str] = []

    # Intelligence dimension keys to check (order = priority)
    dimension_keys = [
        "materiality", "risk", "anomaly", "peer",
        "causal", "projection", "persistence", "pivot",
        "multi_year", "budget", "market",
    ]

    for key in dimension_keys:
        intel_data = context_maps.get(key)
        if intel_data is None:
            continue

        # Per-variance dict (most dimensions)
        if isinstance(intel_data, dict) and variance_id in intel_data:
            entry = intel_data[variance_id]
            if isinstance(entry, dict):
                note = entry.get("note", "")
                if note:
                    notes.append(note)

        # Market context is shared (not per-variance)
        elif isinstance(intel_data, dict) and "note" in intel_data:
            note = intel_data.get("note", "")
            if note:
                notes.append(note)

    return notes[:6]  # Cap at 6 to avoid bloat


# ======================================================================
# LLM Narrative Generation — enriched with context
# ======================================================================


async def _generate_llm_narrative_enriched(
    llm_client: Any,
    rag_retriever: Any | None,
    row_data: dict[str, Any],
    acct_meta: dict[str, Any],
    context_maps: dict[str, Any],
) -> dict[str, str] | None:
    """Generate narrative via LLM with full context enrichment.

    Returns dict with {detail, midlevel, summary, oneliner} or None on failure.
    """
    try:
        # Build enriched prompt with all relationship data
        enriched_context = _build_enriched_prompt(row_data, acct_meta, context_maps)

        # RAG few-shot examples (optional, ignore failures)
        few_shot_text = ""
        if rag_retriever:
            try:
                examples = await rag_retriever.retrieve_similar(
                    {
                        "account_id": row_data.get("account_id", ""),
                        "account_name": acct_meta.get("account_name", ""),
                        "variance_amount": row_data.get("variance_amount", 0),
                        "pl_category": acct_meta.get("pl_category", ""),
                    },
                    top_k=2,
                )
                if examples:
                    few_shot_text = "\n\nApproved commentary examples:\n"
                    for ex in examples:
                        few_shot_text += f"- {ex.narrative_text}\n"
            except Exception:
                pass

        system_prompt = (
            "You are a senior FP&A analyst generating variance narratives. "
            "You have access to decomposition drivers, correlated variances, "
            "trend analysis, netting patterns, and sibling account context. "
            "Use this information to provide cause-and-effect analysis. "
            "Be specific with dollar amounts and percentages. "
            "Return ONLY a JSON object with keys: detail, midlevel, summary, oneliner. "
            "Detail: 2-3 sentences with root cause, impact, and related drivers. "
            "Midlevel: 1-2 sentences for management. "
            "Summary: 1 sentence for CFO. "
            "Oneliner: <10 words for dashboard."
        )

        user_prompt = f"Generate narratives:\n\n{enriched_context}{few_shot_text}"

        response = await llm_client.complete(
            task="narrative_generation",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        if isinstance(response, dict) and response.get("fallback"):
            return None

        content = response.choices[0].message.content

        # Handle markdown-wrapped JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(content)
        if all(k in parsed for k in ("detail", "midlevel", "summary", "oneliner")):
            return parsed
        return None

    except Exception as exc:
        logger.debug(
            "LLM narrative failed for %s: %s", row_data.get("account_id", "?"), exc
        )
        return None


# ======================================================================
# Template Generation — deterministic fallback (enriched with context)
# ======================================================================


def _generate_template_narrative(
    var_dict: dict[str, Any],
    acct_meta: dict[str, Any],
    context_maps: dict[str, Any],
) -> dict[str, str]:
    """Generate deterministic template narrative with context enrichment."""
    account_name = acct_meta.get("account_name", var_dict.get("account_id", "Unknown"))
    variance_amount = var_dict.get("variance_amount", 0.0)
    variance_pct = var_dict.get("variance_pct")
    base_id = str(var_dict.get("base_id", "BUDGET"))
    is_inverse = str(acct_meta.get("variance_sign", "natural")) == "inverse"

    direction = "increased" if variance_amount > 0 else "decreased"
    formatted_amount = format_currency_thousands(abs(variance_amount))
    formatted_pct = format_percentage(variance_pct)
    base_label = _BASE_LABELS.get(base_id, base_id)
    favorable = sign_convention_label(variance_amount, is_inverse)

    # Context enrichments for template
    trend_note = ""
    trend = context_maps.get("trends", {}).get(var_dict.get("account_id", ""))
    if trend:
        trend_note = (
            f" Trending {trend['direction']} for "
            f"{trend['consecutive_periods']} consecutive months."
        )

    decomp_note = ""
    decomp = context_maps.get("decomposition", {}).get(
        var_dict.get("variance_id", "")
    )
    if decomp and decomp.get("components"):
        comps = decomp["components"]
        valid = {
            k: v
            for k, v in comps.items()
            if isinstance(v, (int, float)) and k not in ("residual", "method")
        }
        if valid:
            top_k, top_v = max(valid.items(), key=lambda x: abs(x[1]))
            decomp_note = f" Primary driver: {top_k} (${top_v:,.0f})."

    # Carry-forward note (compare to prior period)
    carry_note = ""
    prior_narr_map = context_maps.get("prior_narratives", {})
    if prior_narr_map:
        dim_key = f"{var_dict.get('account_id','')}|{var_dict.get('bu_id','')}|{var_dict.get('costcenter_node_id','')}|{var_dict.get('geo_node_id','')}|{var_dict.get('segment_node_id','')}|{var_dict.get('lob_node_id','')}"
        prior = prior_narr_map.get(dim_key)
        if prior and prior.get("variance_pct") is not None:
            prior_pct = prior["variance_pct"]
            curr_pct = var_dict.get("variance_pct", 0) or 0
            prior_month = context_maps.get("prior_period", "")
            if prior_pct != 0 or curr_pct != 0:
                from shared.utils.period_utils import get_month_short
                month_label = get_month_short(prior_month) if prior_month else "prior"
                if abs(curr_pct) > abs(prior_pct):
                    carry_note = f" Variance widened from {prior_pct:+.1f}% in {month_label} to {curr_pct:+.1f}%."
                elif abs(curr_pct) < abs(prior_pct):
                    carry_note = f" Variance narrowed from {prior_pct:+.1f}% in {month_label} to {curr_pct:+.1f}%."

    # Seasonal context
    seasonal_note = ""
    try:
        from shared.config.seasonal import SeasonalConfig
        _seasonal = SeasonalConfig()
        _period = var_dict.get("period_id", "")
        _month = int(_period[5:7]) if _period and "-" in _period else 0
        _pl_cat = var_dict.get("pl_category", "")
        if _month > 0 and _pl_cat:
            s_note = _seasonal.get_seasonal_note(_pl_cat, _month)
            if s_note:
                seasonal_note = f" {s_note}"
    except Exception:
        pass

    # FX context
    fx_note = ""
    try:
        decomp_data = context_maps.get("decomposition", {}).get(var_dict.get("variance_id", ""), {})
        fx_effect = decomp_data.get("fx", 0) if isinstance(decomp_data, dict) else 0
        if isinstance(fx_effect, str):
            fx_effect = 0
        variance_amt = abs(var_dict.get("variance_amount", 0)) or 1
        if fx_effect and abs(fx_effect) > variance_amt * 0.01:  # > 1% of total variance
            fx_dir = "favorable" if fx_effect > 0 else "unfavorable"
            fx_note = f" FX impact: ${abs(fx_effect):,.0f} {fx_dir}."
    except Exception:
        pass

    # Intelligence enrichment (Phase 3F+3G+3H — top 4 relevant notes)
    intel_text = ""
    vid = var_dict.get("variance_id", "")
    if vid:
        intel_notes = _collect_intelligence_notes(vid, context_maps)
        if intel_notes:
            intel_text = " " + " ".join(intel_notes[:4])

    detail = (
        f"{account_name} {direction} by {formatted_amount} "
        f"({formatted_pct}) vs {base_label}. "
        f"{favorable}.{trend_note}{decomp_note}{carry_note}{seasonal_note}{fx_note}{intel_text} [AI Draft]"
    )
    midlevel = (
        f"{account_name}: {formatted_amount} ({formatted_pct}) "
        f"{direction} vs {base_label}.{trend_note}"
    )
    summary = (
        f"{account_name} {formatted_amount} {direction}."
        f"{' Trending.' if trend_note else ''}"
    )
    oneliner = f"{formatted_amount} {direction}"

    return {
        "detail": detail,
        "midlevel": midlevel,
        "summary": summary,
        "oneliner": oneliner,
    }


# ======================================================================
# Parent Narrative Generation (Stage 2 — uses children's narratives)
# ======================================================================


async def _generate_parent_llm_narrative(
    llm_client: Any,
    row_dict: dict[str, Any],
    acct_meta_entry: dict[str, Any],
    children: list[dict[str, Any]],
    context_maps: dict[str, Any],
) -> dict[str, str] | None:
    """Generate parent narrative via LLM using children's narratives as context."""
    account_name = acct_meta_entry.get("account_name", row_dict.get("account_id", ""))
    variance = row_dict.get("variance_amount", 0)
    pct = row_dict.get("variance_pct", 0)
    direction = "increased" if variance > 0 else "decreased"
    fav = "Favorable" if (variance > 0) == (acct_meta_entry.get("variance_sign") == "natural") else "Unfavorable"

    # Build children context (top 5 by materiality)
    top_children = children[:5]
    child_lines = []
    for c in top_children:
        cv = c.get("variance_amount", 0)
        cn = c.get("account_name", c.get("account_id", ""))
        child_lines.append(f"- {cn}: ${abs(cv):,.0f} {'favorable' if cv > 0 else 'unfavorable'}")
        if c.get("narrative_detail"):
            child_lines.append(f"  Narrative: {c['narrative_detail'][:150]}")

    remaining = len(children) - len(top_children)
    remaining_total = sum(abs(c.get("variance_amount", 0)) for c in children[5:])
    if remaining > 0:
        child_lines.append(f"- ...and {remaining} other items totaling ${remaining_total:,.0f}")

    children_text = "\n".join(child_lines) if child_lines else "No child details available."

    system_prompt = (
        "You are a senior FP&A analyst synthesizing child-level variance narratives "
        "into a parent-level summary. Reference the key children by name. "
        "Be specific with dollar amounts. Return JSON: {detail, midlevel, summary, oneliner}."
    )

    user_prompt = (
        f"Parent Account: {account_name}\n"
        f"Total Variance: ${abs(variance):,.0f} ({direction}, {fav})\n"
        f"Percentage: {pct:+.1f}%\n\n"
        f"Child Account Variances:\n{children_text}\n\n"
        f"Synthesize a parent narrative that references the key children and explains "
        f"what drove the parent-level variance. Return JSON with detail (2-3 sentences), "
        f"midlevel (1-2 sentences), summary (1 sentence), oneliner (<10 words)."
    )

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw_response = await llm_client.complete("narrative_generation", messages)
        if isinstance(raw_response, dict) and raw_response.get("fallback"):
            return None
        response = raw_response.choices[0].message.content if hasattr(raw_response, "choices") else str(raw_response)
        if response:
            # Clean LLM response — handle markdown wrapping and extra text
            clean = response.strip()
            # Remove markdown code fences
            if "```json" in clean:
                clean = clean.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            # Try to find JSON object
            if "{" in clean:
                start = clean.index("{")
                end = clean.rindex("}") + 1
                clean = clean[start:end]
            parsed = json.loads(clean)
            if all(k in parsed for k in ("detail", "midlevel", "summary", "oneliner")):
                return parsed
            # If keys are different case, try to normalize
            normalized = {k.lower(): v for k, v in parsed.items()}
            if all(k in normalized for k in ("detail", "midlevel", "summary", "oneliner")):
                return {k: normalized[k] for k in ("detail", "midlevel", "summary", "oneliner")}
    except Exception as exc:
        logger.debug("Parent LLM generation failed for %s: %s", account_name, exc)

    return None


def _generate_parent_template_narrative(
    row_dict: dict[str, Any],
    acct_meta_entry: dict[str, Any],
    children: list[dict[str, Any]],
    context_maps: dict[str, Any],
) -> dict[str, str]:
    """Generate parent narrative from template using children's context."""
    account_name = acct_meta_entry.get("account_name", row_dict.get("account_id", ""))
    variance = row_dict.get("variance_amount", 0)
    pct = row_dict.get("variance_pct", 0) or 0
    direction = "increased" if variance > 0 else "decreased"
    sign = "+" if variance > 0 else ""
    fav = "Favorable" if (variance > 0) == (acct_meta_entry.get("variance_sign") == "natural") else "Unfavorable"

    # Build driver text from top 3 children
    top_children = children[:3]
    driver_parts = []
    for c in top_children:
        cn = c.get("account_name", c.get("account_id", ""))
        cv = c.get("variance_amount", 0)
        cs = "+" if cv > 0 else ""
        driver_parts.append(f"{cn} ({cs}${abs(cv):,.0f})")

    drivers_text = ", ".join(driver_parts) if driver_parts else "underlying account movements"

    # Count positive/negative children
    pos_count = sum(1 for c in children if c.get("variance_amount", 0) > 0)
    neg_count = sum(1 for c in children if c.get("variance_amount", 0) < 0)

    remaining = len(children) - len(top_children)
    remaining_note = f" and {remaining} other items" if remaining > 0 else ""

    # Trend context
    trend_note = ""
    trend_data = context_maps.get("trends", {}).get(row_dict.get("account_id", ""))
    if trend_data:
        trend_note = f" Trending {trend_data.get('direction', '?')} for {trend_data.get('consecutive_periods', '?')} consecutive months."

    detail = (
        f"{account_name} {direction} by ${abs(variance):,.0f} ({sign}{pct:.1f}%) vs Budget. {fav}. "
        f"Driven by {drivers_text}{remaining_note}. "
        f"{pos_count} of {len(children)} components contributed positively.{trend_note} [AI Draft]"
    )

    midlevel = (
        f"{account_name}: ${abs(variance):,.0f} ({sign}{pct:.1f}%) {direction}. "
        f"Key drivers: {drivers_text}.{trend_note}"
    )

    summary = f"{account_name} ${abs(variance):,.0f} {direction}. Driven by {driver_parts[0] if driver_parts else 'multiple factors'}."

    oneliner = f"${abs(variance):,.0f} {direction}"

    return {
        "detail": detail,
        "midlevel": midlevel,
        "summary": summary,
        "oneliner": oneliner,
    }


# ======================================================================
# Numerical Accuracy Validation
# ======================================================================


def _validate_narrative_numbers(narrative: str, var_dict: dict[str, Any], tolerance: float = 2.0) -> bool:
    """Validate dollar amounts in narrative text against source data.

    Returns False if any mentioned amount is >tolerance× the actual variance.
    This catches LLM hallucinations (e.g., "$500K" when actual is $50K).
    """
    import re

    source_amount = abs(var_dict.get("variance_amount", 0))
    if source_amount == 0:
        return True

    # Extract dollar amounts ($X, $XK, $X.XK, $XM)
    dollar_pattern = r'\$([\d,]+(?:\.\d+)?)\s*([KMB])?'
    matches = re.findall(dollar_pattern, narrative)

    for num_str, suffix in matches:
        try:
            val = float(num_str.replace(",", ""))
            if suffix == "K":
                val *= 1000
            elif suffix == "M":
                val *= 1_000_000
            elif suffix == "B":
                val *= 1_000_000_000

            if val > source_amount * tolerance and val > 1000:
                logger.warning(
                    "Hallucination: narrative mentions $%s%s but actual variance is $%.0f",
                    num_str, suffix or "", source_amount,
                )
                return False
        except ValueError:
            continue

    return True


def _compute_narrative_confidence(var_dict: dict[str, Any], context_maps: dict[str, Any]) -> float:
    """Compute confidence score for a narrative based on decomposition quality."""
    variance_id = var_dict.get("variance_id", "")
    decomp = context_maps.get("decomposition", {}).get(variance_id)

    if not decomp:
        return 0.3  # No decomposition available

    is_fallback = decomp.get("is_fallback", True)
    residual = abs(decomp.get("residual", 0))
    total = abs(var_dict.get("variance_amount", 0)) or 1

    if not is_fallback:
        return 0.9  # Real decomposition with unit data
    elif residual / total > 0.4:
        return 0.3  # High residual — largely unexplained
    else:
        return 0.6  # Fallback but reasonable


# ======================================================================
# Main Function — layered parallel batching (leaves first, then parents)
# ======================================================================


async def generate_narratives(context: dict[str, Any]) -> None:
    """Generate 4-level narratives with parallel LLM + template fallback.

    Enhanced flow:
    1. Build context maps from Passes 1-4 (correlations, netting, trends,
       decomposition, siblings) — one-time O(N) scan.
    2. Process all variances in parallel via asyncio.gather with Semaphore.
    3. Each variance: try LLM with enriched prompt → fallback to template.
    4. Update material_variances DataFrame with narratives + review entries.
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 5: No material variances — skipping")
        context["narratives"] = pd.DataFrame()
        context["review_status"] = []
        context["audit_entries"] = []
        return

    acct_meta: dict[str, dict[str, Any]] = context.get("acct_meta", {})
    engine_run_id = str(uuid4())

    # ------------------------------------------------------------------
    # Step 0: Check for existing approved/reviewed narratives to preserve
    # ------------------------------------------------------------------
    existing_review = context.get("existing_review_status")
    preserved_ids: set[str] = set()
    if existing_review is not None and isinstance(existing_review, pd.DataFrame) and not existing_review.empty:
        # Keep narratives that have been reviewed or approved (don't regenerate)
        preserve_mask = existing_review["status"].isin(["ANALYST_REVIEWED", "APPROVED"])
        preserved_ids = set(existing_review[preserve_mask]["variance_id"].unique())
        if preserved_ids:
            logger.info("Pass 5: Preserving %d reviewed/approved narratives", len(preserved_ids))

    # Filter material to only variances that need (re)generation
    needs_generation = material[~material["variance_id"].isin(preserved_ids)]
    preserved = material[material["variance_id"].isin(preserved_ids)]

    logger.info(
        "Pass 5: %d total material, %d need generation, %d preserved",
        len(material), len(needs_generation), len(preserved),
    )

    # LLM availability
    llm_client = context.get("llm_client")
    rag_retriever = context.get("rag_retriever")
    use_llm = (
        llm_client is not None
        and hasattr(llm_client, "is_available")
        and llm_client.is_available
    )

    # ------------------------------------------------------------------
    # Step 1: Build context maps (one-time, ~1 second)
    # ------------------------------------------------------------------
    context_maps = _build_context_maps(context)
    logger.info(
        "Pass 5: Context maps — %d corr, %d netting, %d trends, %d decomp, %d sibling groups",
        sum(len(v) for v in context_maps["correlations"].values()),
        len(context_maps["netting"]),
        len(context_maps["trends"]),
        len(context_maps["decomposition"]),
        len(context_maps["siblings"]),
    )

    # ------------------------------------------------------------------
    # Step 2: Parallel processing with semaphore
    # ------------------------------------------------------------------
    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _process_one(row_dict: dict[str, Any]) -> dict[str, Any]:
        """Process one variance: LLM-first with template fallback."""
        meta = acct_meta.get(row_dict.get("account_id", ""), {})
        async with semaphore:
            if use_llm:
                result = await _generate_llm_narrative_enriched(
                    llm_client, rag_retriever, row_dict, meta, context_maps
                )
                if result:
                    return {**result, "_source": "llm"}
            # Template fallback (always works)
            tmpl = _generate_template_narrative(row_dict, meta, context_maps)
            return {**tmpl, "_source": NarrativeSource.GENERATED.value}

    if needs_generation.empty:
        logger.info("Pass 5: All narratives preserved — no generation needed")
        context["narratives"] = material
        context["review_status"] = []
        context["audit_entries"] = []
        return

    # ------------------------------------------------------------------
    # Step 2A: Split into leaves and parents for layered generation
    # ------------------------------------------------------------------
    if "is_calculated" in needs_generation.columns:
        leaf_mask = needs_generation["is_calculated"] == False  # noqa: E712
    else:
        leaf_mask = pd.Series([True] * len(needs_generation), index=needs_generation.index)  # treat all as leaves
    leaf_rows = needs_generation[leaf_mask]
    parent_rows = needs_generation[~leaf_mask]

    logger.info(
        "Pass 5: Layered generation — %d leaves (Stage 1), %d parents (Stage 2)",
        len(leaf_rows), len(parent_rows),
    )

    # ------------------------------------------------------------------
    # Stage 0.5: Build carry-forward context from prior period
    # ------------------------------------------------------------------
    from shared.utils.period_utils import get_prior_period, get_month_name as _get_month

    prior_period = get_prior_period(context.get("period_id", ""))
    prior_narrative_map: dict[str, dict[str, Any]] = {}

    existing_mat = context.get("existing_material")
    if prior_period and existing_mat is not None and isinstance(existing_mat, pd.DataFrame) and not existing_mat.empty:
        prior_mtd = existing_mat[
            (existing_mat["period_id"] == prior_period)
            & (existing_mat["view_id"] == "MTD")
        ]
        for _, row in prior_mtd.iterrows():
            dim_key = f"{row.get('account_id','')}|{row.get('bu_id','')}|{row.get('costcenter_node_id','')}|{row.get('geo_node_id','')}|{row.get('segment_node_id','')}|{row.get('lob_node_id','')}"
            prior_narrative_map[dim_key] = {
                "narrative": str(row.get("narrative_detail", "")),
                "variance_amount": row.get("variance_amount", 0),
                "variance_pct": row.get("variance_pct", 0),
                "period_id": prior_period,
            }
        logger.info("Pass 5: Carry-forward — %d prior period narratives loaded from %s", len(prior_narrative_map), prior_period)

    # Inject carry-forward into context_maps for prompt building
    context_maps["prior_narratives"] = prior_narrative_map
    context_maps["prior_period"] = prior_period

    # ------------------------------------------------------------------
    # Stage 1: Generate LEAF narratives first
    # ------------------------------------------------------------------
    leaf_dicts = [row.to_dict() for _, row in leaf_rows.iterrows()]
    leaf_tasks = [_process_one(rd) for rd in leaf_dicts]

    logger.info("Pass 5 Stage 1: Processing %d leaf variances (LLM=%s)", len(leaf_tasks), use_llm)
    leaf_results = await asyncio.gather(*leaf_tasks) if leaf_tasks else []

    # Build child narratives map for parent generation
    child_narratives_map: dict[str, dict[str, Any]] = {}
    for i, result in enumerate(leaf_results):
        acct_id = leaf_dicts[i].get("account_id", "")
        bu_id = leaf_dicts[i].get("bu_id", "")
        # Key includes BU so parent can find children at same BU level
        key = f"{acct_id}|{bu_id}"
        child_narratives_map[key] = {
            "account_id": acct_id,
            "account_name": acct_meta.get(acct_id, {}).get("account_name", acct_id),
            "narrative_detail": result.get("detail", ""),
            "narrative_midlevel": result.get("midlevel", ""),
            "variance_amount": leaf_dicts[i].get("variance_amount", 0),
            "variance_pct": leaf_dicts[i].get("variance_pct", 0),
            "bu_id": bu_id,
        }

    # ------------------------------------------------------------------
    # Stage 2: Generate PARENT narratives using children's narratives
    # ------------------------------------------------------------------
    parent_dicts = [row.to_dict() for _, row in parent_rows.iterrows()]

    async def _process_parent(row_dict: dict[str, Any]) -> dict[str, Any]:
        """Process a parent/calculated account using children's narratives."""
        parent_acct_id = row_dict.get("account_id", "")
        parent_bu_id = row_dict.get("bu_id", "")
        meta = acct_meta.get(parent_acct_id, {})

        # Collect children's narratives (same BU)
        # Children come from two sources:
        # 1. Accounts with parent_id pointing to this account (e.g., acct_revenue → advisory_fees)
        # 2. Calculated row dependencies (e.g., acct_ebitda depends on gross_profit, total_opex)
        children = []
        calc_deps = meta.get("calc_dependencies") or []
        if isinstance(calc_deps, str):
            try:
                calc_deps = json.loads(calc_deps)
            except Exception:
                calc_deps = []

        for cid, cmeta in acct_meta.items():
            is_child = (
                cmeta.get("parent_id") == parent_acct_id  # Direct children
                or cid in calc_deps  # Calculation dependencies
            )
            if is_child:
                key = f"{cid}|{parent_bu_id}"
                if key in child_narratives_map:
                    children.append(child_narratives_map[key])
                else:
                    # Child may be a parent itself (not in leaf map) — use its variance data
                    for _, pr in parent_rows.iterrows():
                        if pr["account_id"] == cid and pr["bu_id"] == parent_bu_id:
                            children.append({
                                "account_id": cid,
                                "account_name": cmeta.get("account_name", cid),
                                "narrative_detail": "",
                                "variance_amount": pr.get("variance_amount", 0),
                                "variance_pct": pr.get("variance_pct", 0),
                                "bu_id": parent_bu_id,
                            })
                            break

        # Sort by absolute variance (most material first)
        children.sort(key=lambda c: abs(c.get("variance_amount", 0)), reverse=True)

        async with semaphore:
            if use_llm and children:
                result = await _generate_parent_llm_narrative(
                    llm_client, row_dict, meta, children, context_maps
                )
                if result:
                    return {**result, "_source": "llm"}
            # Template fallback with children context
            tmpl = _generate_parent_template_narrative(row_dict, meta, children, context_maps)
            return {**tmpl, "_source": NarrativeSource.GENERATED.value}

    parent_tasks = [_process_parent(rd) for rd in parent_dicts]
    logger.info("Pass 5 Stage 2: Processing %d parent variances", len(parent_tasks))
    parent_results = await asyncio.gather(*parent_tasks) if parent_tasks else []

    # Combine results in original order (leaves + parents)
    row_dicts = leaf_dicts + parent_dicts
    results = list(leaf_results) + list(parent_results)

    # ------------------------------------------------------------------
    # Step 3: Unpack results
    # ------------------------------------------------------------------
    detail_col: list[str | None] = []
    midlevel_col: list[str | None] = []
    summary_col: list[str | None] = []
    oneliner_col: list[str | None] = []
    board_col: list[None] = []
    source_col: list[str] = []
    confidence_col: list[float] = []
    review_entries: list[dict[str, Any]] = []
    llm_count = 0
    template_count = 0

    for i, result in enumerate(results):
        detail_col.append(result.get("detail", ""))
        midlevel_col.append(result.get("midlevel", ""))
        summary_col.append(result.get("summary", ""))
        oneliner_col.append(result.get("oneliner", ""))
        board_col.append(None)

        source = result.get("_source", NarrativeSource.GENERATED.value)
        source_col.append(source)
        if source == "llm":
            llm_count += 1
        else:
            template_count += 1

        # Confidence scoring
        confidence_col.append(_compute_narrative_confidence(row_dicts[i], context_maps))

        # Review entry
        var_dict = row_dicts[i]
        period_id = var_dict.get("period_id", "")
        fiscal_year = int(period_id.split("-")[0]) if period_id and "-" in period_id else None
        review_entries.append(
            {
                "review_id": str(uuid4()),
                "variance_id": var_dict.get("variance_id", ""),
                "status": ReviewStatus.AI_DRAFT.value,
                "assigned_analyst": None,
                "reviewer": None,
                "approver": None,
                "original_narrative": result.get("detail", ""),
                "edited_narrative": None,
                "edit_diff": None,
                "hypothesis_feedback": None,
                "review_notes": None,
                "period_id": period_id,
                "fiscal_year": fiscal_year,
                "created_at": datetime.now(timezone.utc),
                "reviewed_at": None,
                "approved_at": None,
            }
        )

    # ------------------------------------------------------------------
    # Step 4: Update DataFrame (needs_generation only, then merge with preserved)
    # ------------------------------------------------------------------
    generated = needs_generation.copy()
    generated["narrative_detail"] = detail_col
    generated["narrative_midlevel"] = midlevel_col
    generated["narrative_summary"] = summary_col
    generated["narrative_oneliner"] = oneliner_col
    generated["narrative_board"] = board_col
    generated["narrative_source"] = source_col
    generated["narrative_confidence"] = confidence_col
    generated["engine_run_id"] = engine_run_id

    # Merge newly generated with preserved (approved/reviewed) narratives
    if not preserved.empty:
        # Preserved rows already have narrative columns from existing data
        existing_material = context.get("existing_material")
        if existing_material is not None and isinstance(existing_material, pd.DataFrame) and not existing_material.empty:
            # Get narrative columns from existing material for preserved IDs
            narr_cols = ["narrative_detail", "narrative_midlevel", "narrative_summary",
                        "narrative_oneliner", "narrative_board", "narrative_source", "engine_run_id"]
            existing_narrs = existing_material[existing_material["variance_id"].isin(preserved_ids)]
            if not existing_narrs.empty:
                for col in narr_cols:
                    if col in existing_narrs.columns:
                        preserved = preserved.copy()
                        preserved[col] = preserved["variance_id"].map(
                            existing_narrs.set_index("variance_id")[col].to_dict()
                        ).fillna("")

        material = pd.concat([generated, preserved], ignore_index=True)
    else:
        material = generated

    context["narratives"] = material
    context["material_variances"] = material

    # ------------------------------------------------------------------
    # Step 5: Review status + audit log
    # ------------------------------------------------------------------
    context["review_status"] = review_entries

    method = "llm+template" if llm_count > 0 else "template"
    audit_entry = create_audit_entry(
        event_type="engine_run",
        service="computation",
        action="pass5_narrative_generation",
        details={
            "engine_run_id": engine_run_id,
            "period_id": context.get("period_id"),
            "narratives_generated": len(results),
            "llm_generated": llm_count,
            "template_generated": template_count,
            "method": method,
            "llm_used": use_llm,
            "concurrency": _CONCURRENCY,
        },
    )
    context["audit_entries"] = [audit_entry]

    # ------------------------------------------------------------------
    # Stage 3 (Pass 5C): Section Narratives
    # ------------------------------------------------------------------
    period_id = context.get("period_id", "")
    base_id = context.get("comparison_base", "BUDGET")
    # Normalize base_id to uppercase key
    _BASE_NORM = {"Budget": "BUDGET", "Forecast": "FORECAST", "PY": "PRIOR_YEAR", "Prior Year": "PRIOR_YEAR"}
    base_id = _BASE_NORM.get(base_id, base_id)
    view_id = context.get("view", "MTD")

    _BASE_LABELS = {"BUDGET": "Budget", "FORECAST": "Forecast", "PRIOR_YEAR": "Prior Year"}
    base_label = _BASE_LABELS.get(base_id, base_id)

    MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    section_narratives: list[dict[str, Any]] = []
    # Sections and their parent accounts
    SECTION_MAP = {
        "Revenue": ["acct_revenue", "acct_gross_revenue"],
        "COGS": ["acct_cor", "acct_total_cor"],
        "OpEx": ["acct_opex", "acct_total_opex"],
        "Non-Operating": ["acct_non_op", "acct_total_nonop"],
    }

    mtd_rows = material[(material["view_id"] == "MTD") & (material["base_id"] == base_id)] if "base_id" in material.columns else material[material["view_id"] == "MTD"]

    for section_name, section_accounts in SECTION_MAP.items():
        # Collect narratives for this section (parent + leaves)
        section_rows = mtd_rows[mtd_rows["account_id"].isin(section_accounts)]
        # Also get leaf children
        leaf_ids = [aid for aid, meta in acct_meta.items() if meta.get("parent_id") in section_accounts and not meta.get("is_calculated", False)]
        leaf_rows = mtd_rows[mtd_rows["account_id"].isin(leaf_ids)]

        # Aggregate variance across all BUs for this section
        parent_row = section_rows.groupby("account_id").agg({"variance_amount": "sum", "actual_amount": "sum", "comparator_amount": "sum"}).reset_index()
        leaf_agg = leaf_rows.groupby("account_id").agg({"variance_amount": "sum", "variance_pct": "mean"}).reset_index()

        total_var = parent_row["variance_amount"].sum() if not parent_row.empty else 0
        total_pct = (total_var / parent_row["comparator_amount"].sum() * 100) if not parent_row.empty and parent_row["comparator_amount"].sum() != 0 else 0
        direction = "increased" if total_var > 0 else "decreased"
        sign = "+" if total_var > 0 else ""

        # Top drivers from leaves
        if not leaf_agg.empty:
            leaf_agg["abs_var"] = leaf_agg["variance_amount"].abs()
            top_leaves = leaf_agg.nlargest(3, "abs_var")
            drivers = []
            for _, lr in top_leaves.iterrows():
                lname = acct_meta.get(lr["account_id"], {}).get("account_name", lr["account_id"])
                lvar = lr["variance_amount"]
                ls = "+" if lvar > 0 else ""
                drivers.append({"account_name": lname, "amount": round(float(lvar), 0), "direction": "favorable" if lvar > 0 else "unfavorable"})
        else:
            drivers = []

        driver_text = ", ".join(f"{d['account_name']} ({'+' if d['amount']>0 else ''}{d['amount']:,.0f})" for d in drivers[:3]) if drivers else "underlying account movements"

        pos_count = len(leaf_agg[leaf_agg["variance_amount"] > 0]) if not leaf_agg.empty else 0
        total_count = len(leaf_agg) if not leaf_agg.empty else 0

        section_id = hashlib.sha256(f"{period_id}|{section_name}|{base_id}|{view_id}".encode()).hexdigest()[:16]
        narrative = (
            f"{section_name} {direction} by ${abs(total_var):,.0f} ({sign}{total_pct:.1f}%) vs {base_label}. "
            f"Key drivers: {driver_text}. "
            f"{pos_count} of {total_count} lines contributed positively."
        )

        section_narratives.append({
            "section_id": section_id,
            "period_id": period_id,
            "section_name": section_name,
            "base_id": base_id,
            "view_id": view_id,
            "narrative": narrative,
            "key_drivers": drivers,
            "narrative_confidence": 0.7,
            "status": "AI_DRAFT",
        })

    # Profitability section (derived from calculated rows)
    profit_accounts = {"acct_gross_profit": "Gross Profit", "acct_ebitda": "EBITDA", "acct_operating_income": "Operating Income", "acct_net_income": "Net Income"}
    profit_parts = []
    for pid, pname in profit_accounts.items():
        prows = mtd_rows[mtd_rows["account_id"] == pid]
        if not prows.empty:
            pvar = prows["variance_amount"].sum()
            pact = prows["actual_amount"].sum()
            pcomp = prows["comparator_amount"].sum()
            ppct = (pvar / pcomp * 100) if pcomp != 0 else 0
            margin = (pact / mtd_rows[mtd_rows["account_id"] == "acct_revenue"]["actual_amount"].sum() * 100) if not mtd_rows[mtd_rows["account_id"] == "acct_revenue"].empty and mtd_rows[mtd_rows["account_id"] == "acct_revenue"]["actual_amount"].sum() != 0 else 0
            profit_parts.append(f"{pname} {'increased' if pvar>0 else 'decreased'} by ${abs(pvar):,.0f} ({'+' if pvar>0 else ''}{ppct:.1f}%), margin {margin:.1f}%")

    profit_id = hashlib.sha256(f"{period_id}|Profitability|{base_id}|{view_id}".encode()).hexdigest()[:16]
    profit_narrative = ". ".join(profit_parts[:3]) + "." if profit_parts else "Profitability metrics not available."
    section_narratives.append({
        "section_id": profit_id,
        "period_id": period_id,
        "section_name": "Profitability",
        "base_id": base_id,
        "view_id": view_id,
        "narrative": profit_narrative,
        "key_drivers": [{"account_name": k, "amount": 0, "direction": ""} for k in profit_accounts.values()],
        "narrative_confidence": 0.7,
        "status": "AI_DRAFT",
    })

    context["section_narratives"] = section_narratives
    logger.info("Pass 5C: Generated %d section narratives", len(section_narratives))

    # ------------------------------------------------------------------
    # Stage 4 (Pass 5D): Executive Summary
    # ------------------------------------------------------------------
    # Aggregate KPIs
    rev_total = mtd_rows[mtd_rows["account_id"] == "acct_revenue"]["variance_amount"].sum() if not mtd_rows[mtd_rows["account_id"] == "acct_revenue"].empty else 0
    rev_pct = (rev_total / mtd_rows[mtd_rows["account_id"] == "acct_revenue"]["comparator_amount"].sum() * 100) if not mtd_rows[mtd_rows["account_id"] == "acct_revenue"].empty and mtd_rows[mtd_rows["account_id"] == "acct_revenue"]["comparator_amount"].sum() != 0 else 0
    ebitda_total = mtd_rows[mtd_rows["account_id"] == "acct_ebitda"]["variance_amount"].sum() if not mtd_rows[mtd_rows["account_id"] == "acct_ebitda"].empty else 0
    ebitda_pct = (ebitda_total / mtd_rows[mtd_rows["account_id"] == "acct_ebitda"]["comparator_amount"].sum() * 100) if not mtd_rows[mtd_rows["account_id"] == "acct_ebitda"].empty and mtd_rows[mtd_rows["account_id"] == "acct_ebitda"]["comparator_amount"].sum() != 0 else 0

    # Cross-BU themes
    bu_rev = mtd_rows[(mtd_rows["account_id"] == "acct_revenue")].groupby("bu_id")["variance_amount"].sum()
    pos_bus = [bu for bu, v in bu_rev.items() if v > 0]
    neg_bus = [bu for bu, v in bu_rev.items() if v < 0]
    total_bus = len(bu_rev)
    cross_bu = f"{len(pos_bus)} of {total_bus} BUs exceeded revenue targets" if pos_bus else f"All {total_bus} BUs fell short of revenue targets"

    # Risks from trends + netting
    trend_flags = context.get("trend_flags", pd.DataFrame())
    netting_flags = context.get("netting_flags", pd.DataFrame())
    risk_count = len(trend_flags) + len(netting_flags) if not isinstance(trend_flags, pd.DataFrame) or not trend_flags.empty else 0
    risks = []
    if not isinstance(trend_flags, pd.DataFrame) or not trend_flags.empty:
        risks.append({"risk": f"{len(trend_flags)} trending variances identified", "severity": "medium"})
    if not isinstance(netting_flags, pd.DataFrame) or not netting_flags.empty:
        risks.append({"risk": f"{len(netting_flags)} netting offsets detected", "severity": "medium"})

    # Parse month from period_id
    month_num = int(period_id.split("-")[1]) if "-" in period_id else 1
    month_name = MONTH_NAMES[month_num]
    year = period_id.split("-")[0] if "-" in period_id else "2026"

    # Build section narrative references
    section_refs = {s["section_name"]: s["narrative"] for s in section_narratives}

    headline = (
        f"{month_name} {year} close: Revenue {'up' if rev_total>0 else 'down'} {abs(rev_pct):.1f}%, "
        f"EBITDA {'up' if ebitda_total>0 else 'down'} {abs(ebitda_pct):.1f}%. "
        f"{cross_bu}."
    )

    p1 = (
        f"{month_name} {year} financial performance vs {base_label}: "
        f"{section_refs.get('Revenue', 'Revenue data not available.')}"
    )
    p2 = (
        f"Cost management: {section_refs.get('COGS', '')} "
        f"{section_refs.get('OpEx', '')} "
        f"{section_refs.get('Profitability', '')}"
    )
    p3 = (
        f"{len(risks)} risk items identified. "
        + " ".join(r["risk"] + "." for r in risks)
    ) if risks else "No significant risk items identified."

    full_narrative = f"{p1}\n\n{p2}\n\n{p3}"

    summary_id = hashlib.sha256(f"{period_id}|{base_id}|{view_id}".encode()).hexdigest()[:16]
    context["executive_summary"] = {
        "summary_id": summary_id,
        "period_id": period_id,
        "base_id": base_id,
        "view_id": view_id,
        "headline": headline,
        "full_narrative": full_narrative,
        "carry_forward_note": None,
        "key_risks": risks,
        "cross_bu_themes": [{"theme": cross_bu, "bus_affected": pos_bus + neg_bus}],
        "narrative_confidence": 0.7,
        "status": "AI_DRAFT",
    }
    logger.info("Pass 5D: Executive summary generated — headline: %s", headline[:100])

    logger.info(
        "Pass 5: Generated %d narratives (llm=%d, template=%d), "
        "%d section narratives, 1 executive summary, engine_run_id=%s",
        len(results),
        llm_count,
        template_count,
        len(section_narratives),
        engine_run_id,
    )
