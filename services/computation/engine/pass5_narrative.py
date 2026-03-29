"""Pass 5 — Template-Based Multi-Level Narrative Generation.

Sprint 0 implementation uses deterministic templates (no LLM).
RAG-enhanced LLM generation is deferred to Sprint 1.

Generates four narrative levels for each material variance:

1. **detail**   — Full analyst narrative with amount, percentage,
                  comparison base, and favorability label.
2. **midlevel** — BU-leader summary: account, amount, percentage, direction.
3. **summary**  — CFO-level: account, amount, direction.
4. **oneliner** — Dashboard one-liner: amount and direction.
5. **board**    — None (on-demand only, generated in Sprint 1+).

Also creates:
- ``fact_review_status`` entries with status = AI_DRAFT for each variance.
- ``audit_log`` entry for the engine run.

Output: populates context["narratives"], context["review_status"],
and context["audit_entries"].
"""

from __future__ import annotations

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
    audit_entry = create_audit_entry(
        event_type="engine_run",
        service="computation",
        action="pass5_narrative_generation",
        details={
            "engine_run_id": engine_run_id,
            "period_id": context.get("period_id"),
            "narratives_generated": generated_count,
            "method": "template",
            "llm_used": False,
        },
    )
    context["audit_entries"] = [audit_entry]

    logger.info(
        "Pass 5: Generated %d narratives (template-based), "
        "created %d review entries, engine_run_id=%s",
        generated_count,
        len(review_entries),
        engine_run_id,
    )
