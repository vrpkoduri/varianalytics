"""Pass 1 — Raw Variance Computation.

Computes variance at ALL intersections — leaf-level from fact_financials,
then rolls up through account hierarchy, and resolves calculated rows
(EBITDA, Gross Profit, etc.) in dependency order.

Grain: Period × BU × CostCenter × Account (with denormalized Geo/Segment/LOB).
Views: MTD (direct), QTD/YTD (sum of MTDs).
Bases: Budget, Forecast, Prior Year.

Edge cases:
- comparator=0 → variance_pct=NULL, flagged "unbudgeted"
- missing PY → skip vs PY comparison
- negative budget → sign convention applies
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import numpy as np
import pandas as pd

from shared.data.loader import DataLoader

logger = logging.getLogger(__name__)

# Comparator column for each base
_BASE_COLUMN_MAP = {
    "BUDGET": "budget_amount",
    "FORECAST": "forecast_amount",
    "PRIOR_YEAR": "prior_year_amount",
}


async def compute_raw_variances(context: dict[str, Any]) -> None:
    """Compute raw variances at all dimensional intersections.

    Populates context["all_variances"] with a DataFrame of all variance rows
    (leaf + rollup + calculated, MTD + QTD + YTD, all 3 bases).

    Args:
        context: Pipeline context dict with data_dir, period_id, and
                 accumulated DataFrames.
    """
    data_dir = context.get("data_dir", "data/output")
    loader = DataLoader(data_dir)

    ff = loader.load_table("fact_financials")
    dim_account = loader.load_table("dim_account")
    dim_period = loader.load_table("dim_period")

    logger.info("Pass 1: Loaded %d fact rows, %d accounts", len(ff), len(dim_account))

    acct_meta = _build_account_metadata(dim_account)

    # Step 1: MTD leaf variances for all 3 bases
    mtd_variances = _compute_mtd_leaf_variances(ff, acct_meta)
    logger.info("Pass 1: %d MTD leaf variance rows", len(mtd_variances))

    # Step 2: Account rollup (leaf → parent accounts)
    mtd_with_rollup = _rollup_accounts(mtd_variances, acct_meta)
    logger.info("Pass 1: %d rows after account rollup", len(mtd_with_rollup))

    # Step 3: Resolve calculated rows in dependency order
    mtd_with_calc = _resolve_calculated_rows(mtd_with_rollup, acct_meta)
    logger.info("Pass 1: %d rows after calculated rows", len(mtd_with_calc))

    # Step 4: Compute QTD/YTD from MTD
    all_views = _compute_qtd_ytd(mtd_with_calc, dim_period)
    logger.info("Pass 1: %d total variance rows (MTD+QTD+YTD)", len(all_views))

    # Step 5: Compute variance percentage
    all_views["variance_pct"] = np.where(
        all_views["comparator_amount"] != 0,
        (all_views["variance_amount"] / all_views["comparator_amount"]) * 100,
        np.nan,
    )

    # Store in context for downstream passes
    context["all_variances"] = all_views
    context["acct_meta"] = acct_meta
    context["dim_period"] = dim_period


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_account_metadata(dim_account: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Build account_id -> metadata lookup from dim_account."""
    meta: dict[str, dict[str, Any]] = {}
    for _, row in dim_account.iterrows():
        deps = None
        if row.get("calc_dependencies") and pd.notna(row.get("calc_dependencies")):
            try:
                deps = json.loads(row["calc_dependencies"])
            except (json.JSONDecodeError, TypeError):
                deps = None
        meta[row["account_id"]] = {
            "account_name": row["account_name"],
            "parent_id": row.get("parent_id"),
            "is_leaf": bool(row.get("is_leaf", True)),
            "is_calculated": bool(row.get("is_calculated", False)),
            "calc_formula": row.get("calc_formula") if pd.notna(row.get("calc_formula")) else None,
            "calc_dependencies": deps,
            "pl_category": row.get("pl_category") if pd.notna(row.get("pl_category")) else None,
            "variance_sign": row.get("variance_sign") if pd.notna(row.get("variance_sign")) else None,
        }
    return meta


def _compute_mtd_leaf_variances(
    ff: pd.DataFrame, acct_meta: dict[str, dict],
) -> pd.DataFrame:
    """Compute MTD variances at leaf level for all 3 bases."""
    all_dfs: list[pd.DataFrame] = []

    for base_id, comp_col in _BASE_COLUMN_MAP.items():
        valid = ff[ff[comp_col].notna()].copy()
        if len(valid) == 0:
            continue

        result = valid[
            ["period_id", "bu_id", "costcenter_node_id", "account_id",
             "geo_node_id", "segment_node_id", "lob_node_id", "fiscal_year",
             "actual_amount"]
        ].copy()
        result["comparator_amount"] = valid[comp_col].values
        result["variance_amount"] = result["actual_amount"] - result["comparator_amount"]
        result["view_id"] = "MTD"
        result["base_id"] = base_id
        result["is_calculated"] = False

        # Add account metadata
        result["pl_category"] = result["account_id"].map(
            lambda a: acct_meta.get(a, {}).get("pl_category")
        )
        result["variance_sign"] = result["account_id"].map(
            lambda a: acct_meta.get(a, {}).get("variance_sign")
        )

        all_dfs.append(result)

    return pd.concat(all_dfs, ignore_index=True)


def _rollup_accounts(
    df: pd.DataFrame, acct_meta: dict[str, dict],
) -> pd.DataFrame:
    """Roll up leaf accounts to parent account nodes.

    For rollup parents (acct_revenue, acct_cor, acct_opex, acct_non_op),
    sum all direct-child leaf accounts.
    """
    parent_children: dict[str, list[str]] = {}
    for acct_id, meta in acct_meta.items():
        parent_id = meta.get("parent_id")
        if parent_id and not meta.get("is_calculated", False):
            parent_children.setdefault(parent_id, []).append(acct_id)

    group_cols = [
        "period_id", "bu_id", "costcenter_node_id",
        "geo_node_id", "segment_node_id", "lob_node_id",
        "fiscal_year", "view_id", "base_id",
    ]
    amount_cols = ["actual_amount", "comparator_amount", "variance_amount"]

    rollup_dfs: list[pd.DataFrame] = [df]

    for parent_id, children in parent_children.items():
        child_data = df[df["account_id"].isin(children)]
        if len(child_data) == 0:
            continue

        parent_meta = acct_meta.get(parent_id, {})
        agg = child_data.groupby(group_cols, as_index=False, dropna=False)[amount_cols].sum()
        agg["account_id"] = parent_id
        agg["is_calculated"] = False
        agg["pl_category"] = parent_meta.get("pl_category")
        agg["variance_sign"] = parent_meta.get("variance_sign")

        rollup_dfs.append(agg)

    return pd.concat(rollup_dfs, ignore_index=True)


def _resolve_calculated_rows(
    df: pd.DataFrame, acct_meta: dict[str, dict],
) -> pd.DataFrame:
    """Resolve calculated rows (EBITDA, Gross Profit, etc.) in dependency order.

    Resolution order is topologically sorted by calc_dependencies.
    """
    calc_order = _topological_sort_calcs(acct_meta)
    if not calc_order:
        return df

    group_cols = [
        "period_id", "bu_id", "costcenter_node_id",
        "geo_node_id", "segment_node_id", "lob_node_id",
        "fiscal_year", "view_id", "base_id",
    ]

    result = df.copy()

    for acct_id in calc_order:
        meta = acct_meta[acct_id]
        formula = meta.get("calc_formula")
        if not formula:
            continue

        calc_rows = _evaluate_formula(result, acct_id, formula, group_cols, acct_meta)
        if calc_rows is not None and len(calc_rows) > 0:
            result = pd.concat([result, calc_rows], ignore_index=True)

    return result


def _topological_sort_calcs(acct_meta: dict[str, dict]) -> list[str]:
    """Topologically sort calculated accounts by dependency order."""
    calc_accounts = {
        acct_id: meta.get("calc_dependencies") or []
        for acct_id, meta in acct_meta.items()
        if meta.get("is_calculated") and meta.get("calc_formula")
    }

    resolved: list[str] = []
    visited: set[str] = set()

    def visit(acct_id: str) -> None:
        if acct_id in visited:
            return
        visited.add(acct_id)
        for dep in calc_accounts.get(acct_id, []):
            if dep in calc_accounts:
                visit(dep)
        resolved.append(acct_id)

    for acct_id in calc_accounts:
        visit(acct_id)

    return resolved


def _evaluate_formula(
    df: pd.DataFrame, acct_id: str, formula: str,
    group_cols: list[str], acct_meta: dict[str, dict],
) -> Optional[pd.DataFrame]:
    """Evaluate a calculated row formula.

    Supports:
    - SUM(parent.children): sum all children of a parent account
    - Arithmetic: acct_a - acct_b + acct_c
    """
    meta = acct_meta[acct_id]

    if formula.startswith("SUM(") and ".children)" in formula:
        parent_ref = formula[4:].split(".")[0]
        child_ids = [
            aid for aid, m in acct_meta.items()
            if m.get("parent_id") == parent_ref and not m.get("is_calculated")
        ]
        child_data = df[df["account_id"].isin(child_ids)]
        if len(child_data) == 0:
            return None

        amount_cols = ["actual_amount", "comparator_amount", "variance_amount"]
        agg = child_data.groupby(group_cols, as_index=False, dropna=False)[amount_cols].sum()
        agg["account_id"] = acct_id
        agg["is_calculated"] = True
        agg["pl_category"] = meta.get("pl_category")
        agg["variance_sign"] = meta.get("variance_sign")
        return agg

    # Parse arithmetic formulas
    tokens = re.split(r"\s*([\+\-])\s*", formula.strip())
    ref_accounts = [t.strip() for t in tokens if t.strip().startswith("acct_")]
    ref_data = df[df["account_id"].isin(ref_accounts)]
    if len(ref_data) == 0:
        return None

    amount_cols = ["actual_amount", "comparator_amount", "variance_amount"]
    result_parts: dict[str, pd.Series] = {}

    for col in amount_cols:
        pivot = ref_data.pivot_table(
            index=group_cols, columns="account_id", values=col, aggfunc="sum",
        ).fillna(0)
        result_parts[col] = _eval_arithmetic(tokens, pivot)

    if result_parts["actual_amount"] is None:
        return None

    result_df = result_parts["actual_amount"].reset_index()
    result_df.columns = list(group_cols) + ["actual_amount"]
    result_df["comparator_amount"] = result_parts["comparator_amount"].values
    result_df["variance_amount"] = result_parts["variance_amount"].values
    result_df["account_id"] = acct_id
    result_df["is_calculated"] = True
    result_df["pl_category"] = meta.get("pl_category")
    result_df["variance_sign"] = meta.get("variance_sign")

    return result_df


def _eval_arithmetic(tokens: list[str], pivot: pd.DataFrame) -> Optional[pd.Series]:
    """Evaluate arithmetic expression on a pivoted DataFrame."""
    result = None
    op = "+"

    for token in tokens:
        token = token.strip()
        if token in ("+", "-"):
            op = token
            continue
        if not token.startswith("acct_"):
            continue

        series = pivot[token] if token in pivot.columns else pd.Series(0, index=pivot.index)

        if result is None:
            result = series if op == "+" else -series
        elif op == "+":
            result = result + series
        else:
            result = result - series

    return result


def _compute_qtd_ytd(
    mtd_df: pd.DataFrame, dim_period: pd.DataFrame,
) -> pd.DataFrame:
    """Compute QTD and YTD views by summing MTD rows."""
    period_meta = {}
    for _, row in dim_period.iterrows():
        period_meta[row["period_id"]] = (row["fiscal_year"], row["fiscal_quarter"])

    mtd_df = mtd_df.copy()
    if "fiscal_quarter" not in mtd_df.columns:
        mtd_df["fiscal_quarter"] = mtd_df["period_id"].map(
            lambda p: period_meta.get(p, (None, None))[1]
        )

    key_cols = [
        "bu_id", "costcenter_node_id", "account_id",
        "geo_node_id", "segment_node_id", "lob_node_id",
        "fiscal_year", "base_id",
        "is_calculated", "pl_category", "variance_sign",
    ]
    amount_cols = ["actual_amount", "comparator_amount", "variance_amount"]

    views: list[pd.DataFrame] = [mtd_df]

    # QTD
    for (fy, fq), group in mtd_df.groupby(["fiscal_year", "fiscal_quarter"]):
        if pd.isna(fq):
            continue
        last_period = group["period_id"].max()
        qtd = group.groupby(key_cols, as_index=False, dropna=False)[amount_cols].sum()
        qtd["period_id"] = last_period
        qtd["view_id"] = "QTD"
        views.append(qtd)

    # YTD
    for fy, group in mtd_df.groupby("fiscal_year"):
        last_period = group["period_id"].max()
        ytd = group.groupby(key_cols, as_index=False, dropna=False)[amount_cols].sum()
        ytd["period_id"] = last_period
        ytd["view_id"] = "YTD"
        views.append(ytd)

    result = pd.concat(views, ignore_index=True)
    result = result.drop(columns=["fiscal_quarter"], errors="ignore")
    return result
