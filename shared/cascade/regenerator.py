"""Cascade Regenerator — regenerates parent/section/executive narratives.

When a leaf narrative changes, this module regenerates all affected
ancestors in topological order using the knowledge graph's cascade chain.

Usage::

    from shared.cascade.regenerator import CascadeRegenerator
    from shared.data.service import DataService

    ds = DataService("data/output")
    graph = ds.get_graph("2026-06")
    regen = CascadeRegenerator(ds, graph)

    result = await regen.regenerate_chain("v_leaf_001", "2026-06")
    print(result.regenerated)  # ['v_parent_001', 'section:revenue:2026-06', 'exec:2026-06']
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

import pandas as pd

logger = logging.getLogger("cascade.regenerator")


@dataclass
class CascadeResult:
    """Result of a cascade regeneration run."""

    cascade_id: str = ""
    trigger_variance_id: str = ""
    period_id: str = ""
    regenerated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    total_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    chain: list[dict[str, Any]] = field(default_factory=list)


class CascadeRegenerator:
    """Executes cascade regeneration of narrative hierarchy.

    Uses the knowledge graph to find affected nodes, then regenerates
    in topological order: parents → sections → executive.

    Args:
        data_service: DataService for reading variance/narrative data.
        graph: VarianceGraph instance with cascade chain queries.
        llm_client: Optional LLM client for narrative generation.
    """

    def __init__(
        self,
        data_service: Any,
        graph: Any,
        llm_client: Any = None,
    ) -> None:
        self._ds = data_service
        self._graph = graph
        self._llm_client = llm_client

    async def regenerate_chain(
        self,
        variance_id: str,
        period_id: str,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
        use_llm: bool = False,
    ) -> CascadeResult:
        """Regenerate full cascade chain for a changed variance.

        Finds affected parents/sections/executive via knowledge graph,
        then regenerates each in topological order.

        Args:
            variance_id: The variance that was edited/approved.
            period_id: Period of the variance.
            view_id: View type (MTD/QTD/YTD).
            base_id: Comparison base (BUDGET/FORECAST/PRIOR_YEAR).
            use_llm: Whether to use LLM for parent regeneration.

        Returns:
            CascadeResult with regenerated IDs and audit trail.
        """
        start = time.monotonic()
        result = CascadeResult(
            cascade_id=str(uuid4())[:8],
            trigger_variance_id=variance_id,
            period_id=period_id,
        )

        # Get the cascade chain from knowledge graph
        chain = self._graph.get_cascade_chain_typed(variance_id)
        result.chain = chain

        if not chain:
            result.total_seconds = time.monotonic() - start
            logger.info(
                "Cascade %s: no chain for %s — nothing to regenerate",
                result.cascade_id, variance_id,
            )
            return result

        logger.info(
            "Cascade %s: chain has %d steps for %s",
            result.cascade_id, len(chain), variance_id,
        )

        # Load material variances for this period
        material = self._get_material_variances(period_id, view_id, base_id)

        # Process each level in order
        for entry in chain:
            step_start = time.monotonic()
            entry_id = entry["id"]
            entry_type = entry["type"]

            try:
                if entry_type == "parent_variance":
                    narrative = self._regenerate_parent(
                        entry_id, entry.get("account_id", ""),
                        period_id, view_id, base_id, material,
                    )
                    if narrative:
                        self._update_narrative(material, entry_id, narrative)
                        result.regenerated.append(entry_id)
                    else:
                        result.skipped.append(entry_id)

                elif entry_type == "section":
                    section_name = entry.get("section_name", "")
                    narrative = self._regenerate_section(
                        section_name, period_id, material,
                    )
                    if narrative:
                        result.regenerated.append(entry_id)
                    else:
                        result.skipped.append(entry_id)

                elif entry_type == "executive":
                    narrative = self._regenerate_executive(period_id, material)
                    if narrative:
                        result.regenerated.append(entry_id)
                    else:
                        result.skipped.append(entry_id)

            except Exception as exc:
                logger.warning(
                    "Cascade %s: error regenerating %s: %s",
                    result.cascade_id, entry_id, exc,
                )
                result.errors.append(f"{entry_id}: {exc}")

            result.timings[entry_id] = time.monotonic() - step_start

        result.total_seconds = time.monotonic() - start
        logger.info(
            "Cascade %s complete: %d regenerated, %d skipped, %.1f s",
            result.cascade_id,
            len(result.regenerated),
            len(result.skipped),
            result.total_seconds,
        )
        return result

    # ------------------------------------------------------------------
    # Individual regeneration methods
    # ------------------------------------------------------------------

    def _regenerate_parent(
        self,
        variance_id: str,
        account_id: str,
        period_id: str,
        view_id: str,
        base_id: str,
        material: pd.DataFrame,
    ) -> Optional[dict[str, str]]:
        """Regenerate a parent account narrative from its children.

        Returns dict with narrative_detail, narrative_summary, etc.
        or None if no children found.
        """
        # Find children accounts
        children_accts = self._get_child_accounts(account_id)
        if not children_accts:
            return None

        # Get children's narratives from material
        mask = (
            material["account_id"].isin(children_accts)
            & (material["period_id"] == period_id)
            & (material["view_id"] == view_id)
            & (material["base_id"] == base_id)
        )
        children = material[mask]

        if children.empty:
            return None

        # Collect child narrative texts
        child_entries = []
        for _, row in children.iterrows():
            name = str(row.get("account_name", row.get("account_id", "")))
            narrative = str(row.get("narrative_detail", ""))
            amount = float(row.get("variance_amount", 0))
            child_entries.append({
                "name": name,
                "narrative": narrative[:200],
                "amount": amount,
            })

        # Sort by absolute impact
        child_entries.sort(key=lambda x: abs(x["amount"]), reverse=True)

        # Get parent variance data
        parent_mask = material["variance_id"] == variance_id
        if not parent_mask.any():
            return None
        parent_row = material[parent_mask].iloc[0]
        parent_amount = float(parent_row.get("variance_amount", 0))
        parent_name = str(parent_row.get("account_name", account_id))

        # Generate synthesized narrative (template)
        direction = "increased" if parent_amount > 0 else "decreased"
        top_drivers = child_entries[:3]
        driver_text = "; ".join(
            f"{d['name']} (${abs(d['amount']):,.0f})" for d in top_drivers
        )
        favorable_count = sum(1 for d in child_entries if d["amount"] > 0)

        detail = (
            f"{parent_name} {direction} by ${abs(parent_amount):,.0f}. "
            f"Key drivers: {driver_text}. "
            f"{favorable_count}/{len(child_entries)} children favorable."
        )
        summary = f"{parent_name} {direction} ${abs(parent_amount):,.0f}, driven by {top_drivers[0]['name']}."
        oneliner = f"{parent_name}: {'+'if parent_amount > 0 else ''}{parent_amount:,.0f}"

        return {
            "narrative_detail": detail,
            "narrative_midlevel": detail,
            "narrative_summary": summary,
            "narrative_oneliner": oneliner,
            "narrative_source": "cascade_regenerated",
        }

    def _regenerate_section(
        self,
        section_name: str,
        period_id: str,
        material: pd.DataFrame,
    ) -> Optional[dict[str, str]]:
        """Regenerate a section narrative from its member variances.

        Returns dict with section narrative text, or None.
        """
        # Map section names to pl_categories
        section_to_category = {
            "revenue": "Revenue",
            "cost_of_goods_sold": "COGS",
            "operating_expenses": "OpEx",
            "non_operating": "NonOp",
            "tax": "Tax",
        }

        pl_cat = section_to_category.get(section_name)
        if not pl_cat:
            return None

        # Filter material to this section + period
        mask = (
            (material["pl_category"] == pl_cat)
            & (material["period_id"] == period_id)
        )
        section_data = material[mask]

        if section_data.empty:
            return None

        # Aggregate section totals
        total_amount = float(section_data["variance_amount"].sum())
        direction = "favorable" if total_amount > 0 else "unfavorable"

        # Top 3 drivers
        top_drivers = section_data.nlargest(3, "variance_amount", keep="first")
        driver_parts = []
        for _, row in top_drivers.iterrows():
            name = str(row.get("account_name", row.get("account_id", "")))
            amt = float(row.get("variance_amount", 0))
            driver_parts.append(f"{name} (${abs(amt):,.0f})")

        positive_count = int((section_data["variance_amount"] > 0).sum())

        narrative = (
            f"{pl_cat} variance is ${abs(total_amount):,.0f} {direction}. "
            f"Top drivers: {', '.join(driver_parts)}. "
            f"{positive_count}/{len(section_data)} items favorable. "
            f"[Cascade regenerated]"
        )

        return {
            "section_name": section_name,
            "period_id": period_id,
            "narrative": narrative,
            "total_variance": total_amount,
            "driver_count": len(section_data),
            "status": "AI_DRAFT",
        }

    def _regenerate_executive(
        self,
        period_id: str,
        material: pd.DataFrame,
    ) -> Optional[dict[str, str]]:
        """Regenerate executive summary from section data.

        Returns dict with headline + narrative, or None.
        """
        period_data = material[material["period_id"] == period_id]
        if period_data.empty:
            return None

        # Revenue
        rev_data = period_data[period_data["pl_category"] == "Revenue"]
        rev_total = float(rev_data["variance_amount"].sum()) if not rev_data.empty else 0

        # COGS + OpEx (costs)
        cost_data = period_data[period_data["pl_category"].isin(["COGS", "OpEx"])]
        cost_total = float(cost_data["variance_amount"].sum()) if not cost_data.empty else 0

        # Net
        net_total = rev_total + cost_total

        # Headline
        rev_dir = "above" if rev_total > 0 else "below"
        headline = (
            f"Revenue ${abs(rev_total):,.0f} {rev_dir} plan. "
            f"Net impact: ${abs(net_total):,.0f} {'favorable' if net_total > 0 else 'unfavorable'}."
        )

        # Full narrative (3 paragraphs)
        p1 = f"Revenue is ${abs(rev_total):,.0f} {'above' if rev_total > 0 else 'below'} budget."
        p2 = f"Total costs are ${abs(cost_total):,.0f} {'favorable' if cost_total < 0 else 'unfavorable'}."
        p3 = f"Net bottom-line impact is ${abs(net_total):,.0f} {'favorable' if net_total > 0 else 'unfavorable'}."

        full_narrative = f"{p1}\n\n{p2}\n\n{p3}"

        return {
            "period_id": period_id,
            "headline": headline,
            "full_narrative": full_narrative,
            "revenue_variance": rev_total,
            "cost_variance": cost_total,
            "net_variance": net_total,
            "status": "AI_DRAFT",
        }

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    def _get_material_variances(
        self, period_id: str, view_id: str, base_id: str
    ) -> pd.DataFrame:
        """Load material variances from DataService."""
        table = self._ds._table("fact_variance_material")
        if table.empty:
            return table

        mask = (table["period_id"] == period_id)
        if "view_id" in table.columns:
            mask &= table["view_id"] == view_id
        if "base_id" in table.columns:
            mask &= table["base_id"] == base_id
        return table[mask].copy()

    def _get_child_accounts(self, parent_id: str) -> list[str]:
        """Get child account IDs for a parent."""
        children = self._ds._account_children.get(parent_id, [])
        return children

    def _update_narrative(
        self, material: pd.DataFrame, variance_id: str, narrative: dict
    ) -> None:
        """Update narrative columns in the material DataFrame in-place."""
        mask = material["variance_id"] == variance_id
        if not mask.any():
            return

        for col in ["narrative_detail", "narrative_midlevel", "narrative_summary",
                     "narrative_oneliner", "narrative_source"]:
            if col in narrative and col in material.columns:
                material.loc[mask, col] = narrative[col]
