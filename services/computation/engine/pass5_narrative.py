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

    return "\n".join(sections)


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

    detail = (
        f"{account_name} {direction} by {formatted_amount} "
        f"({formatted_pct}) vs {base_label}. "
        f"{favorable}.{trend_note}{decomp_note} [AI Draft]"
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
# Main Function — parallel batching with asyncio.gather
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

    row_dicts = [row.to_dict() for _, row in material.iterrows()]
    tasks = [_process_one(rd) for rd in row_dicts]

    logger.info(
        "Pass 5: Processing %d variances (%d concurrent, LLM=%s)",
        len(tasks),
        _CONCURRENCY,
        use_llm,
    )
    results = await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Step 3: Unpack results
    # ------------------------------------------------------------------
    detail_col: list[str | None] = []
    midlevel_col: list[str | None] = []
    summary_col: list[str | None] = []
    oneliner_col: list[str | None] = []
    board_col: list[None] = []
    source_col: list[str] = []
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

        # Review entry
        var_dict = row_dicts[i]
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
                "created_at": datetime.now(timezone.utc),
                "reviewed_at": None,
                "approved_at": None,
            }
        )

    # ------------------------------------------------------------------
    # Step 4: Update DataFrame
    # ------------------------------------------------------------------
    material = material.copy()
    material["narrative_detail"] = detail_col
    material["narrative_midlevel"] = midlevel_col
    material["narrative_summary"] = summary_col
    material["narrative_oneliner"] = oneliner_col
    material["narrative_board"] = board_col
    material["narrative_source"] = source_col
    material["engine_run_id"] = engine_run_id

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

    logger.info(
        "Pass 5: Generated %d narratives (llm=%d, template=%d), "
        "engine_run_id=%s",
        len(results),
        llm_count,
        template_count,
        engine_run_id,
    )
