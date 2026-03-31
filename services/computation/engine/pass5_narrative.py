"""Pass 5 — Multi-Level Narrative Generation (LLM-first + template fallback).

Generates four narrative levels for each material variance:

1. **detail**   — Full analyst narrative with amount, percentage,
                  comparison base, and favorability label.
2. **midlevel** — BU-leader summary: account, amount, percentage, direction.
3. **summary**  — CFO-level: account, amount, direction.
4. **oneliner** — Dashboard one-liner: amount and direction.
5. **board**    — None (on-demand only, generated in Sprint 1+).

When ``context["llm_client"]`` is present and available, LLM-based
generation with RAG few-shot examples is attempted first. If the LLM
call fails or is unavailable, deterministic templates are used as a
guaranteed fallback.

Also creates:
- ``fact_review_status`` entries with status = AI_DRAFT for each variance.
- ``audit_log`` entry for the engine run.

Output: populates context["narratives"], context["review_status"],
and context["audit_entries"].
"""

from __future__ import annotations

import json
import logging
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


async def _generate_llm_narrative(
    llm_client: Any,
    rag_retriever: Any | None,
    row_data: dict,
    acct_meta: dict,
) -> dict | None:
    """Try to generate narrative via LLM with RAG few-shot examples.

    Returns dict with {detail, midlevel, summary, oneliner} or None on failure.
    """
    try:
        # Retrieve similar approved commentaries for few-shot
        examples: list[Any] = []
        if rag_retriever:
            examples = await rag_retriever.retrieve_similar(
                {
                    "account_id": row_data.get("account_id", ""),
                    "account_name": acct_meta.get("account_name", ""),
                    "variance_amount": row_data.get("variance_amount", 0),
                    "pl_category": acct_meta.get("pl_category", ""),
                },
                top_k=2,
            )

        # Build prompt
        few_shot_text = ""
        if examples:
            few_shot_text = (
                "\n\nHere are examples of approved commentaries for similar variances:\n"
            )
            for ex in examples:
                few_shot_text += f"- {ex.narrative_text}\n"

        variance_desc = (
            f"Account: {acct_meta.get('account_name', 'Unknown')}\n"
            f"Variance: ${row_data.get('variance_amount', 0):,.0f} "
            f"({row_data.get('variance_pct', 0):.1f}%)\n"
            f"Category: {acct_meta.get('pl_category', 'Unknown')}\n"
            f"Period: {row_data.get('period_id', 'Unknown')}\n"
            f"BU: {row_data.get('bu_id', 'All')}"
        )

        system_prompt = (
            "You are a senior FP&A analyst generating variance narratives. "
            "Generate 4 levels of narrative for the given variance. "
            "Return ONLY a JSON object with keys: detail, midlevel, summary, oneliner. "
            "Detail: 2-3 sentences with root cause and impact. "
            "Midlevel: 1-2 sentences for management. "
            "Summary: 1 sentence for CFO. "
            "Oneliner: <10 words for dashboard."
        )

        user_prompt = (
            f"Generate narratives for this variance:\n\n{variance_desc}{few_shot_text}"
        )

        response = await llm_client.complete(
            task="narrative_generation",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Fallback dict means LLM not available
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
        logger.debug("LLM narrative generation failed: %s", exc)
        return None


async def generate_narratives(context: dict[str, Any]) -> None:
    """Generate template-based multi-level narratives for all material variances.

    Updates ``context["material_variances"]`` with narrative columns and
    creates review-status and audit-log entries.

    Args:
        context: Pipeline context dict. Must contain:
            - material_variances: DataFrame from Pass 2
            - acct_meta: dict mapping account_id -> account metadata
                         (at minimum ``account_name`` and optionally
                         ``variance_sign``).
    """
    material: pd.DataFrame = context.get("material_variances", pd.DataFrame())

    if material.empty:
        logger.warning("Pass 5: No material variances — skipping narrative generation")
        context["narratives"] = pd.DataFrame()
        context["review_status"] = []
        context["audit_entries"] = []
        return

    acct_meta: dict[str, dict[str, Any]] = context.get("acct_meta", {})
    engine_run_id = str(uuid4())

    review_entries: list[dict[str, Any]] = []
    generated_count = 0

    # ------------------------------------------------------------------
    # LLM availability check
    # ------------------------------------------------------------------
    llm_client = context.get("llm_client")
    rag_retriever = context.get("rag_retriever")
    use_llm = (
        llm_client is not None
        and hasattr(llm_client, "is_available")
        and llm_client.is_available
    )
    llm_count = 0
    template_count = 0

    # ------------------------------------------------------------------
    # Generate narratives for each material variance row
    # ------------------------------------------------------------------
    detail_col: list[str | None] = []
    midlevel_col: list[str | None] = []
    summary_col: list[str | None] = []
    oneliner_col: list[str | None] = []
    board_col: list[None] = []
    source_col: list[str] = []

    for _, row in material.iterrows():
        var_dict = row.to_dict()
        account_id = var_dict.get("account_id", "")
        meta = acct_meta.get(account_id, {})
        account_name = meta.get("account_name", account_id)

        # -- Try LLM-first path --
        if use_llm:
            llm_result = await _generate_llm_narrative(
                llm_client, rag_retriever, var_dict, meta
            )
            if llm_result:
                detail_col.append(llm_result["detail"])
                midlevel_col.append(llm_result["midlevel"])
                summary_col.append(llm_result["summary"])
                oneliner_col.append(llm_result["oneliner"])
                board_col.append(None)
                source_col.append("llm")

                # Create review status entry (AI_DRAFT)
                review_entries.append(
                    {
                        "review_id": str(uuid4()),
                        "variance_id": var_dict.get("variance_id", ""),
                        "status": ReviewStatus.AI_DRAFT.value,
                        "assigned_analyst": None,
                        "reviewer": None,
                        "approver": None,
                        "original_narrative": llm_result["detail"],
                        "edited_narrative": None,
                        "edit_diff": None,
                        "hypothesis_feedback": None,
                        "review_notes": None,
                        "created_at": datetime.now(timezone.utc),
                        "reviewed_at": None,
                        "approved_at": None,
                    }
                )

                generated_count += 1
                llm_count += 1
                continue  # Skip template generation
            # Fall through to template if LLM failed

        variance_amount = var_dict.get("variance_amount", 0.0)
        variance_pct = var_dict.get("variance_pct")
        base_id = str(var_dict.get("base_id", "BUDGET"))
        is_inverse = str(meta.get("variance_sign", "natural")) == "inverse"

        # Format building blocks
        direction = "increased" if variance_amount > 0 else "decreased"
        formatted_amount = format_currency_thousands(abs(variance_amount))
        formatted_pct = format_percentage(variance_pct)
        base_label = _BASE_LABELS.get(base_id, base_id)
        favorable = sign_convention_label(variance_amount, is_inverse)

        # -- detail (analyst) --
        narrative_detail = (
            f"{account_name} {direction} by {formatted_amount} "
            f"({formatted_pct}) vs {base_label}. "
            f"{favorable}. [AI Draft]"
        )

        # -- midlevel (BU leader) --
        narrative_midlevel = (
            f"{account_name}: {formatted_amount} ({formatted_pct}) "
            f"{direction} vs {base_label}."
        )

        # -- summary (CFO) --
        narrative_summary = f"{account_name} {formatted_amount} {direction}."

        # -- oneliner (dashboard) --
        narrative_oneliner = f"{formatted_amount} {direction}"

        detail_col.append(narrative_detail)
        midlevel_col.append(narrative_midlevel)
        summary_col.append(narrative_summary)
        oneliner_col.append(narrative_oneliner)
        board_col.append(None)
        source_col.append(NarrativeSource.GENERATED.value)

        # Create review status entry (AI_DRAFT)
        review_entries.append(
            {
                "review_id": str(uuid4()),
                "variance_id": var_dict.get("variance_id", ""),
                "status": ReviewStatus.AI_DRAFT.value,
                "assigned_analyst": None,
                "reviewer": None,
                "approver": None,
                "original_narrative": narrative_detail,
                "edited_narrative": None,
                "edit_diff": None,
                "hypothesis_feedback": None,
                "review_notes": None,
                "created_at": datetime.now(timezone.utc),
                "reviewed_at": None,
                "approved_at": None,
            }
        )

        generated_count += 1
        template_count += 1

    # ------------------------------------------------------------------
    # Update material_variances DataFrame with narrative columns
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
    # Also update the main material_variances reference
    context["material_variances"] = material

    # ------------------------------------------------------------------
    # Store review status entries
    # ------------------------------------------------------------------
    context["review_status"] = review_entries

    # ------------------------------------------------------------------
    # Create audit log entry for the engine run
    # ------------------------------------------------------------------
    method = "llm+template" if llm_count > 0 else "template"
    audit_entry = create_audit_entry(
        event_type="engine_run",
        service="computation",
        action="pass5_narrative_generation",
        details={
            "engine_run_id": engine_run_id,
            "period_id": context.get("period_id"),
            "narratives_generated": generated_count,
            "llm_generated": llm_count,
            "template_generated": template_count,
            "method": method,
            "llm_used": llm_count > 0,
        },
    )
    context["audit_entries"] = [audit_entry]

    logger.info(
        "Pass 5: Generated %d narratives (llm=%d, template=%d), "
        "created %d review entries, engine_run_id=%s",
        generated_count,
        llm_count,
        template_count,
        len(review_entries),
        engine_run_id,
    )
