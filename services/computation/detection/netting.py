"""Netting Detection — 4 MVP checks for offsetting child variances.

Netting occurs when child variances within a hierarchy node cancel
each other out, causing the parent to appear immaterial even though
significant movements exist underneath.

MVP checks (1-4):
1. Gross offset — For rollup parents below materiality, if
   sum(abs(children)) / abs(parent) > netting_ratio_threshold (3.0)
   then children are largely offsetting.

2. Dispersion — For each parent, std dev of child variance_pcts
   exceeds child_dispersion_threshold (10pp).

3. Directional split — Parent below threshold has children with
   both positive AND negative variance_amounts.

4. Cross-account — Within a (bu, costcenter, geo, period) slice,
   revenue and cost account variances offset so that
   total_abs > 3x * abs(net).

Returns DataFrame matching fact_netting_flags schema:
    netting_id, parent_node_id, parent_dimension, check_type,
    net_variance, gross_variance, netting_ratio, child_details,
    period_id, created_at
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from shared.config.thresholds import ThresholdConfig
from shared.models.enums import NettingCheckType

logger = logging.getLogger(__name__)


def detect_netting(
    all_variances: pd.DataFrame,
    threshold_config: ThresholdConfig,
    period_id: str,
) -> pd.DataFrame:
    """Run netting detection checks 1-4 on the variance dataset.

    Filters to the current period, base='BUDGET', view='MTD' before
    running checks. Identifies rollup parents whose net variance
    appears small but whose children have large offsetting movements.

    Args:
        all_variances: Full variance DataFrame from Pass 1 with columns
            including account_id, variance_amount, variance_pct, pl_category,
            bu_id, costcenter_node_id, geo_node_id, period_id, view_id, base_id.
        threshold_config: Loaded ThresholdConfig instance.
        period_id: Current period to filter on.

    Returns:
        DataFrame with fact_netting_flags schema columns.
    """
    # Filter to current period, BUDGET base, MTD view
    mask = (
        (all_variances["period_id"] == period_id)
        & (all_variances["base_id"] == "BUDGET")
        & (all_variances["view_id"] == "MTD")
    )
    df = all_variances[mask].copy()

    if df.empty:
        logger.warning("No MTD/BUDGET variances for period %s — skipping netting", period_id)
        return _empty_netting_df()

    logger.info("Netting detection: %d rows for period=%s, base=BUDGET, view=MTD", len(df), period_id)

    flags: list[dict[str, Any]] = []

    # --- Check 1, 2, 3: Account-hierarchy based checks ---
    account_flags = _check_account_hierarchy(df, threshold_config, period_id)
    flags.extend(account_flags)

    # --- Check 4: Cross-account netting ---
    if threshold_config.cross_account_enabled:
        cross_flags = _check_cross_account(df, threshold_config, period_id)
        flags.extend(cross_flags)

    if not flags:
        logger.info("Netting detection: no netting patterns found")
        return _empty_netting_df()

    result = pd.DataFrame(flags)
    logger.info("Netting detection: %d netting flags generated", len(result))
    return result


# ---------------------------------------------------------------------------
# Account hierarchy checks (1, 2, 3)
# ---------------------------------------------------------------------------


def _check_account_hierarchy(
    df: pd.DataFrame,
    threshold_config: ThresholdConfig,
    period_id: str,
) -> list[dict[str, Any]]:
    """Run checks 1-3 on account rollup parents.

    For each unique (account that has children in the data), checks whether
    the parent's net variance masks offsetting children.
    """
    flags: list[dict[str, Any]] = []

    # Build parent->children map from the data.
    # A "parent" is any account_id that appears in the data AND has
    # other accounts that share the same dimension slice with a different
    # account_id (they were rolled up in Pass 1).
    # We rely on the fact that Pass 1 created rollup rows: the parent account
    # appears alongside its children in the same dimension slices.

    dim_cols = [
        "bu_id", "costcenter_node_id", "geo_node_id",
        "segment_node_id", "lob_node_id", "fiscal_year",
    ]

    # Identify rollup parents: accounts whose is_calculated is False and whose
    # account_id appears as a parent_id for other accounts.
    # Since we don't have parent_id directly in the variance df, we identify
    # parents by checking which accounts have children via the acct_meta.
    # For now, we group by dim_cols and look at accounts in each group.
    # Parent accounts from rollup will have the same dim slice as their children.

    # Group variance rows by dimension slice
    grouped = df.groupby(dim_cols, dropna=False)

    for slice_key, slice_df in grouped:
        if len(slice_df) < 2:
            continue

        # Extract dimension values from group key for flag records
        if isinstance(slice_key, tuple):
            dim_values = dict(zip(dim_cols, slice_key))
        else:
            dim_values = {dim_cols[0]: slice_key}

        _run_parent_child_checks(slice_df, threshold_config, period_id, dim_cols, flags, dim_values)

    return flags


def _run_parent_child_checks(
    slice_df: pd.DataFrame,
    threshold_config: ThresholdConfig,
    period_id: str,
    dim_cols: list[str],
    flags: list[dict[str, Any]],
    dim_values: dict[str, Any] | None = None,
) -> None:
    """For a single dimension slice, identify parent-child relationships and run checks 1-3.

    A parent is identified as an account whose variance_amount equals the sum
    of all other accounts' variance_amounts in the slice that share a common
    account_id prefix (e.g., acct_revenue is parent of acct_product_revenue).
    """
    accounts = slice_df[["account_id", "variance_amount", "variance_pct", "pl_category"]].copy()

    # Group accounts by prefix to find parent-child sets.
    # Account IDs follow pattern: acct_{category} for parents,
    # acct_{subcategory}_{name} for children.
    parent_candidates: dict[str, list[str]] = {}
    for acct_id in accounts["account_id"].unique():
        # Check if any other account starts with a prefix derived from this one
        # or if this account's ID is a prefix for others.
        pass

    # More robust: identify parents by checking if an account's variance
    # is approximately the sum of other accounts in the same slice.
    acct_variances = accounts.set_index("account_id")["variance_amount"].to_dict()
    acct_pcts = accounts.set_index("account_id")["variance_pct"].to_dict()
    acct_categories = accounts.set_index("account_id")["pl_category"].to_dict()

    all_acct_ids = list(acct_variances.keys())

    # Try each account as a potential parent
    for parent_id in all_acct_ids:
        child_ids = [a for a in all_acct_ids if a != parent_id]
        if len(child_ids) < 2:
            continue

        parent_var = acct_variances[parent_id]
        child_sum = sum(acct_variances[c] for c in child_ids)

        # Check if this account is indeed a rollup parent
        # (its variance should be close to the sum of children)
        if abs(parent_var) < 1e-6 and abs(child_sum) < 1e-6:
            continue
        if abs(child_sum) > 1e-6 and abs(parent_var - child_sum) / max(abs(child_sum), 1) > 0.01:
            continue  # Not a rollup parent — variances don't match

        parent_pl = acct_categories.get(parent_id)
        parent_is_material = threshold_config.is_material(
            parent_var,
            acct_pcts.get(parent_id),
            pl_category=parent_pl,
        )

        child_details = [
            {
                "account_id": c,
                "variance_amount": acct_variances[c],
                "variance_pct": acct_pcts.get(c),
            }
            for c in child_ids
        ]

        gross_variance = sum(abs(acct_variances[c]) for c in child_ids)
        net_variance = parent_var

        # --- Check 1: Gross offset ---
        # Only check parents whose own variance is BELOW materiality threshold
        if not parent_is_material and abs(net_variance) > 1e-6:
            netting_ratio = gross_variance / abs(net_variance)
            if netting_ratio > threshold_config.netting_ratio_threshold:
                flags.append(_make_flag(
                    parent_node_id=parent_id,
                    parent_dimension="account",
                    check_type=NettingCheckType.GROSS_OFFSET,
                    net_variance=net_variance,
                    gross_variance=gross_variance,
                    netting_ratio=netting_ratio,
                    child_details=child_details,
                    period_id=period_id,
                    dim_values=dim_values,
                ))

        # --- Check 2: Dispersion ---
        child_pcts = [acct_pcts.get(c) for c in child_ids]
        valid_pcts = [p for p in child_pcts if p is not None and not np.isnan(p)]
        if len(valid_pcts) >= 2:
            std_dev = float(np.std(valid_pcts, ddof=1))
            if std_dev > threshold_config.child_dispersion_threshold:
                netting_ratio = gross_variance / abs(net_variance) if abs(net_variance) > 1e-6 else float("inf")
                flags.append(_make_flag(
                    parent_node_id=parent_id,
                    parent_dimension="account",
                    check_type=NettingCheckType.DISPERSION,
                    net_variance=net_variance,
                    gross_variance=gross_variance,
                    netting_ratio=netting_ratio,
                    child_details=child_details,
                    period_id=period_id,
                    dim_values=dim_values,
                ))

        # --- Check 3: Directional split ---
        # Parent below threshold, some children positive, some negative
        if not parent_is_material:
            child_vars = [acct_variances[c] for c in child_ids]
            has_positive = any(v > 0 for v in child_vars)
            has_negative = any(v < 0 for v in child_vars)
            if has_positive and has_negative:
                netting_ratio = gross_variance / abs(net_variance) if abs(net_variance) > 1e-6 else float("inf")
                flags.append(_make_flag(
                    parent_node_id=parent_id,
                    parent_dimension="account",
                    check_type=NettingCheckType.DIRECTIONAL_SPLIT,
                    net_variance=net_variance,
                    gross_variance=gross_variance,
                    netting_ratio=netting_ratio,
                    child_details=child_details,
                    period_id=period_id,
                    dim_values=dim_values,
                ))


# ---------------------------------------------------------------------------
# Check 4: Cross-account netting
# ---------------------------------------------------------------------------


def _check_cross_account(
    df: pd.DataFrame,
    threshold_config: ThresholdConfig,
    period_id: str,
) -> list[dict[str, Any]]:
    """Check 4 — Cross-account netting within (bu, costcenter, geo, period) slices.

    For each slice, checks if revenue and cost account variances offset:
    if total abs sum > 3x * abs(net) → flag.
    """
    flags: list[dict[str, Any]] = []

    slice_cols = ["bu_id", "costcenter_node_id", "geo_node_id", "segment_node_id", "lob_node_id"]
    grouped = df.groupby(slice_cols, dropna=False)

    for slice_key, slice_df in grouped:
        # Separate revenue vs cost/expense accounts
        revenue_mask = slice_df["pl_category"] == "Revenue"
        cost_mask = slice_df["pl_category"].isin(["COGS", "OpEx", "NonOp", "Tax"])

        revenue_rows = slice_df[revenue_mask]
        cost_rows = slice_df[cost_mask]

        if revenue_rows.empty or cost_rows.empty:
            continue

        revenue_total = revenue_rows["variance_amount"].sum()
        cost_total = cost_rows["variance_amount"].sum()
        net_variance = revenue_total + cost_total
        gross_variance = abs(revenue_total) + abs(cost_total)

        if abs(net_variance) < 1e-6:
            continue

        ratio = gross_variance / abs(net_variance)
        if ratio > threshold_config.netting_ratio_threshold:
            # Build child details from both revenue and cost accounts
            child_details = []
            for _, row in slice_df.iterrows():
                if row["pl_category"] in ("Revenue", "COGS", "OpEx", "NonOp", "Tax"):
                    child_details.append({
                        "account_id": row["account_id"],
                        "pl_category": row["pl_category"],
                        "variance_amount": float(row["variance_amount"]),
                        "variance_pct": float(row["variance_pct"]) if pd.notna(row.get("variance_pct")) else None,
                    })

            # Build parent_node_id from slice key
            if isinstance(slice_key, tuple):
                parent_node_id = "|".join(str(k) for k in slice_key)
                dim_values = dict(zip(slice_cols, slice_key))
            else:
                parent_node_id = str(slice_key)
                dim_values = {slice_cols[0]: slice_key}

            flags.append(_make_flag(
                parent_node_id=parent_node_id,
                parent_dimension="cross_account",
                check_type=NettingCheckType.CROSS_ACCOUNT,
                net_variance=net_variance,
                gross_variance=gross_variance,
                netting_ratio=ratio,
                child_details=child_details,
                period_id=period_id,
                dim_values=dim_values,
            ))

    return flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flag(
    *,
    parent_node_id: str,
    parent_dimension: str,
    check_type: NettingCheckType,
    net_variance: float,
    gross_variance: float,
    netting_ratio: float,
    child_details: list[dict[str, Any]],
    period_id: str,
    dim_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a single netting flag dict matching fact_netting_flags schema."""
    dv = dim_values or {}
    return {
        "netting_id": str(uuid4()),
        "parent_node_id": parent_node_id,
        "parent_dimension": parent_dimension,
        "check_type": check_type.value,
        "net_variance": float(net_variance),
        "gross_variance": float(gross_variance),
        "netting_ratio": float(netting_ratio),
        "child_details": child_details,
        "period_id": period_id,
        "bu_id": dv.get("bu_id"),
        "geo_node_id": dv.get("geo_node_id"),
        "segment_node_id": dv.get("segment_node_id"),
        "lob_node_id": dv.get("lob_node_id"),
        "costcenter_node_id": dv.get("costcenter_node_id"),
        "created_at": datetime.now(timezone.utc),
    }


def _empty_netting_df() -> pd.DataFrame:
    """Return an empty DataFrame with the fact_netting_flags schema."""
    return pd.DataFrame(columns=[
        "netting_id", "parent_node_id", "parent_dimension", "check_type",
        "net_variance", "gross_variance", "netting_ratio", "child_details",
        "period_id", "bu_id", "geo_node_id", "segment_node_id",
        "lob_node_id", "costcenter_node_id", "created_at",
    ])
