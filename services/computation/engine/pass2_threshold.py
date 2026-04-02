"""Pass 2 — Threshold Filter.

Applies materiality thresholds using OR logic to determine which
variances qualify for downstream analysis. Three qualification types:

1. Material — exceeds absolute $ and/or percentage thresholds
   (configurable per P&L category in thresholds YAML).
2. Netted — flagged by Pass 1.5, even if parent node is below threshold.
3. Trending — flagged by Pass 2.5, even if current-period variance
   is below threshold.

For each variance row (primary view: MTD, base: BUDGET):
- Check is_material using ThresholdConfig with pl_category
- Check if flagged by netting (is_netted)
- Check if flagged by trend (is_trending)
- Keep if ANY of the 3 flags is True

Also keeps QTD/YTD rows for the same account+dimension keys
that are material in MTD.

Output: populates context["material_variances"] with enriched DataFrame
including variance_id, is_material, is_netted, is_trending columns.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from shared.config.thresholds import ThresholdConfig
from shared.models.enums import NettingCheckType, TrendRuleType

logger = logging.getLogger(__name__)

# Dimension columns that form a unique variance key (excluding period/view/base)
_KEY_COLS = [
    "account_id", "bu_id", "costcenter_node_id",
    "geo_node_id", "segment_node_id", "lob_node_id",
]


async def apply_threshold_filter(context: dict[str, Any]) -> None:
    """Filter variances to those qualifying as material, netted, or trending.

    Reads context["all_variances"], context["netting_flags"], and
    context["trend_flags"]. Produces context["material_variances"]
    containing only rows that pass the OR-logic filter.

    Args:
        context: Pipeline context dict. Must contain:
            - all_variances: DataFrame from Pass 1
            - netting_flags: DataFrame from Pass 1.5
            - trend_flags: DataFrame from Pass 2.5
            - period_id: Current period key
    """
    all_variances: pd.DataFrame = context["all_variances"]
    netting_flags: pd.DataFrame = context.get("netting_flags", pd.DataFrame())
    trend_flags: pd.DataFrame = context.get("trend_flags", pd.DataFrame())
    period_id: str = context["period_id"]

    if all_variances.empty:
        logger.warning("Pass 2: No variances available — skipping threshold filter")
        context["material_variances"] = pd.DataFrame()
        return

    threshold_config = ThresholdConfig()

    # -----------------------------------------------------------------
    # Step 1: Filter to current period, ALL bases, MTD view
    # -----------------------------------------------------------------
    mtd_mask = (
        (all_variances["period_id"] == period_id)
        & (all_variances["view_id"] == "MTD")
    )
    mtd_df = all_variances[mtd_mask].copy()

    if mtd_df.empty:
        logger.warning("Pass 2: No MTD rows for period %s", period_id)
        context["material_variances"] = pd.DataFrame()
        return

    logger.info("Pass 2: Evaluating %d MTD rows for period=%s across bases: %s",
                len(mtd_df), period_id, list(mtd_df["base_id"].unique()))

    # -----------------------------------------------------------------
    # Step 2: Check materiality for each row
    # -----------------------------------------------------------------
    mtd_df["is_material"] = mtd_df.apply(
        lambda row: threshold_config.is_material(
            variance_amount=row["variance_amount"],
            variance_pct=row["variance_pct"] if pd.notna(row.get("variance_pct")) else None,
            pl_category=row.get("pl_category"),
        ),
        axis=1,
    )

    # -----------------------------------------------------------------
    # Step 3: Check netting flags
    # -----------------------------------------------------------------
    netted_account_ids = _extract_netted_accounts(netting_flags, period_id)
    mtd_df["is_netted"] = mtd_df["account_id"].isin(netted_account_ids)

    # -----------------------------------------------------------------
    # Step 4: Check trend flags
    # -----------------------------------------------------------------
    trending_keys = _extract_trending_keys(trend_flags)
    mtd_df["_dim_key"] = mtd_df[_KEY_COLS].apply(
        lambda row: "|".join(str(v) for v in row), axis=1
    )
    mtd_df["is_trending"] = mtd_df["_dim_key"].isin(trending_keys)

    # -----------------------------------------------------------------
    # Step 5: Apply OR logic — keep if ANY flag is True
    # -----------------------------------------------------------------
    qualified_mask = mtd_df["is_material"] | mtd_df["is_netted"] | mtd_df["is_trending"]
    qualified_mtd = mtd_df[qualified_mask].copy()

    logger.info(
        "Pass 2: %d of %d MTD rows qualify (material=%d, netted=%d, trending=%d)",
        len(qualified_mtd),
        len(mtd_df),
        mtd_df["is_material"].sum(),
        mtd_df["is_netted"].sum(),
        mtd_df["is_trending"].sum(),
    )

    # -----------------------------------------------------------------
    # Step 6: Also pull QTD/YTD rows for qualified dimension keys
    # -----------------------------------------------------------------
    qualified_dim_keys = set(qualified_mtd["_dim_key"].unique())

    other_views_mask = (
        (all_variances["period_id"] == period_id)
        & (all_variances["view_id"].isin(["QTD", "YTD"]))
    )
    other_views = all_variances[other_views_mask].copy()

    if not other_views.empty:
        other_views["_dim_key"] = other_views[_KEY_COLS].apply(
            lambda row: "|".join(str(v) for v in row), axis=1
        )
        other_views = other_views[other_views["_dim_key"].isin(qualified_dim_keys)].copy()

        # Carry forward flags from MTD row (deduplicate keys across bases)
        flag_df = qualified_mtd[["_dim_key", "is_material", "is_netted", "is_trending"]].drop_duplicates(subset=["_dim_key"])
        key_to_flags = flag_df.set_index("_dim_key").to_dict("index")

        other_views["is_material"] = other_views["_dim_key"].map(
            lambda k: key_to_flags.get(k, {}).get("is_material", False)
        )
        other_views["is_netted"] = other_views["_dim_key"].map(
            lambda k: key_to_flags.get(k, {}).get("is_netted", False)
        )
        other_views["is_trending"] = other_views["_dim_key"].map(
            lambda k: key_to_flags.get(k, {}).get("is_trending", False)
        )

        logger.info("Pass 2: Including %d QTD/YTD rows for qualified keys", len(other_views))
    else:
        other_views = pd.DataFrame()

    # -----------------------------------------------------------------
    # Step 7: Combine and assign variance_id
    # -----------------------------------------------------------------
    combined = pd.concat([qualified_mtd, other_views], ignore_index=True)

    # Drop helper column
    combined = combined.drop(columns=["_dim_key"], errors="ignore")

    # Assign deterministic variance_id (hash of dimension keys)
    # Same variance always gets the same ID across engine re-runs.
    _ID_COLS = ["period_id", "account_id", "bu_id", "costcenter_node_id",
                "geo_node_id", "segment_node_id", "lob_node_id", "view_id", "base_id"]
    combined["variance_id"] = combined[_ID_COLS].apply(
        lambda row: hashlib.sha256("|".join(str(v) for v in row).encode()).hexdigest()[:16],
        axis=1,
    )
    combined["created_at"] = datetime.now(timezone.utc)

    # Verify uniqueness
    dup_count = combined["variance_id"].duplicated().sum()
    if dup_count > 0:
        logger.warning("Pass 2: %d duplicate variance_ids detected — de-duplicating", dup_count)
        combined = combined.drop_duplicates(subset=["variance_id"], keep="first")

    context["material_variances"] = combined

    logger.info(
        "Pass 2: Threshold filter complete — %d total qualified rows "
        "(MTD=%d, QTD/YTD=%d)",
        len(combined),
        len(qualified_mtd),
        len(other_views) if not other_views.empty else 0,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_netted_accounts(
    netting_flags: pd.DataFrame,
    period_id: str,
) -> set[str]:
    """Extract account IDs flagged by netting detection for the current period.

    Collects both the parent_node_id (the netted parent) and all child
    account_ids from child_details, so downstream passes can find them.
    """
    if netting_flags.empty:
        return set()

    # Filter to current period
    if "period_id" in netting_flags.columns:
        period_flags = netting_flags[netting_flags["period_id"] == period_id]
    else:
        period_flags = netting_flags

    netted_ids: set[str] = set()

    for _, row in period_flags.iterrows():
        # The parent itself is netted
        parent_id = row.get("parent_node_id")
        if parent_id and row.get("parent_dimension") == "account":
            netted_ids.add(parent_id)

        # Also include child accounts from the netting flag
        child_details = row.get("child_details", [])
        if isinstance(child_details, list):
            for child in child_details:
                if isinstance(child, dict) and "account_id" in child:
                    netted_ids.add(child["account_id"])

    return netted_ids


def _extract_trending_keys(trend_flags: pd.DataFrame) -> set[str]:
    """Extract dimension keys that are flagged as trending.

    The dimension_key in trend_flags is a pipe-delimited string of
    (account_id, bu_id, costcenter_node_id, geo_node_id, segment_node_id,
    lob_node_id) — matching _KEY_COLS order.
    """
    if trend_flags.empty:
        return set()

    if "dimension_key" in trend_flags.columns:
        return set(trend_flags["dimension_key"].unique())

    return set()
