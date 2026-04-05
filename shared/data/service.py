"""Data Access Service — centralized query layer for all API endpoints.

Singleton wrapping DataLoader for computed parquet data.
Provides typed query methods that return dicts/lists ready for API responses.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Optional

import numpy as np
import pandas as pd

from shared.data.loader import DataLoader

logger = logging.getLogger(__name__)


def _to_native(value: Any) -> Any:
    """Convert numpy/pandas types to Python native types for JSON serialization."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if pd.isna(value):
        return None
    return value


def _clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert numpy types in a dict to native Python types."""
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            cleaned[k] = _clean_dict(v)
        elif isinstance(v, np.ndarray):
            cleaned[k] = _clean_list(v.tolist())
        elif isinstance(v, list):
            cleaned[k] = _clean_list(v)
        elif isinstance(v, str):
            # Try to parse JSON strings (from parquet)
            if v.startswith('[') or v.startswith('{'):
                try:
                    cleaned[k] = json.loads(v)
                except (json.JSONDecodeError, ValueError):
                    cleaned[k] = v
            else:
                cleaned[k] = v
        else:
            cleaned[k] = _to_native(v)
    return cleaned


def _clean_list(lst: list[Any]) -> list[Any]:
    """Recursively convert numpy types in a list."""
    result = []
    for item in lst:
        if isinstance(item, dict):
            result.append(_clean_dict(item))
        elif isinstance(item, list):
            result.append(_clean_list(item))
        else:
            result.append(_to_native(item))
    return result

# Summary card metrics: account_id -> display name
_SUMMARY_CARD_ACCOUNTS: list[tuple[str, str]] = [
    ("acct_revenue", "Total Revenue"),
    ("acct_cor", "Total COGS"),
    ("acct_gross_profit", "Gross Profit"),
    ("acct_opex", "Total OpEx"),
    ("acct_ebitda", "EBITDA"),
    ("acct_operating_income", "Operating Income"),
    ("acct_net_income", "Net Income"),
]

# Standard P&L presentation order (root children, top-down)
_PL_ROOT_CHILDREN_ORDER: list[str] = [
    "acct_revenue",
    "acct_gross_revenue",
    "acct_cor",
    "acct_total_cor",
    "acct_gross_profit",
    "acct_opex",
    "acct_total_opex",
    "acct_ebitda",
    "acct_operating_income",
    "acct_non_op",
    "acct_total_nonop",
    "acct_pbt",
    "acct_tax",
    "acct_net_income",
]


class DataService:
    """Centralized data access for all services.

    Loads all parquet tables once at init, provides query methods
    operating on in-memory DataFrames.
    """

    _instance: Optional[DataService] = None

    def __init__(self, data_dir: str = "data/output") -> None:
        self._loader = DataLoader(data_dir)
        self._data_dir = data_dir
        self._tables: dict[str, pd.DataFrame] = {}
        self._account_lookup: dict[str, dict[str, Any]] = {}
        self._account_children: dict[str, list[str]] = {}
        self._graph_cache: dict[str, Any] = {}  # period_id → VarianceGraph
        self._load_all_tables()
        self._build_account_metadata()

    @classmethod
    def get_instance(cls, data_dir: str = "data/output") -> DataService:
        """Return the singleton instance, creating it if needed."""
        if cls._instance is None:
            cls._instance = cls(data_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton — used in testing."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_all_tables(self) -> None:
        """Load all available parquet tables into memory."""
        table_names = [
            "fact_variance_material",
            "fact_decomposition",
            "fact_netting_flags",
            "fact_trend_flags",
            "fact_correlations",
            "fact_financials",
            "dim_account",
            "dim_hierarchy",
            "dim_business_unit",
            "dim_period",
            "fact_section_narrative",
            "fact_executive_summary",
        ]
        for name in table_names:
            if self._loader.table_exists(name):
                try:
                    self._tables[name] = self._loader.load_table(name)
                    logger.info("Loaded table %s: %d rows", name, len(self._tables[name]))
                except Exception as e:
                    logger.error("Failed to load table %s: %s", name, e)
                    self._tables[name] = pd.DataFrame()
            else:
                logger.warning("Table %s not found, skipping", name)
                self._tables[name] = pd.DataFrame()

    def _build_account_metadata(self) -> None:
        """Build account lookup dict and parent->children mapping."""
        accts = self._tables.get("dim_account", pd.DataFrame())
        if accts.empty:
            return
        for _, row in accts.iterrows():
            self._account_lookup[row["account_id"]] = row.to_dict()
        # Build children mapping
        for _, row in accts.iterrows():
            pid = row.get("parent_id")
            if pid and pd.notna(pid):
                self._account_children.setdefault(pid, []).append(row["account_id"])

    # ------------------------------------------------------------------
    # Knowledge Graph access
    # ------------------------------------------------------------------

    def get_graph(self, period_id: Optional[str] = None) -> Any:
        """Return a cached VarianceGraph, building on first access.

        Args:
            period_id: Optional period filter.  Graph is cached per key
                (period_id or '__all__').

        Returns:
            VarianceGraph instance.
        """
        cache_key = period_id or "__all__"
        if cache_key not in self._graph_cache:
            self._graph_cache[cache_key] = self._build_graph(period_id)
        return self._graph_cache[cache_key]

    def _build_graph(self, period_id: Optional[str] = None) -> Any:
        """Build a knowledge graph from loaded tables."""
        from shared.knowledge.graph_builder import build_variance_graph_from_data

        return build_variance_graph_from_data(self._data_dir, period_id=period_id)

    def invalidate_graph_cache(self) -> None:
        """Clear all cached graphs.  Call after engine re-run."""
        self._graph_cache.clear()
        logger.info("Knowledge graph cache invalidated")

    def _table(self, name: str) -> pd.DataFrame:
        """Get a table, returning empty DataFrame if not loaded."""
        return self._tables.get(name, pd.DataFrame())

    def _filter_variance(
        self,
        df: pd.DataFrame,
        period_id: Optional[str] = None,
        bu_id: Optional[str] = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> pd.DataFrame:
        """Apply standard filters to fact_variance_material."""
        mask = (df["view_id"] == view_id) & (df["base_id"] == base_id)
        if period_id is not None:
            mask &= df["period_id"] == period_id
        if bu_id is not None:
            mask &= df["bu_id"] == bu_id
        return df[mask]

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        """Convert a value to float, returning None for NaN/inf."""
        if val is None:
            return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_favorable(variance_amount: float, variance_sign: Optional[str]) -> bool:
        """Determine if a variance is favorable given sign convention."""
        if variance_sign == "inverse":
            return variance_amount < 0  # cost savings
        return variance_amount > 0  # revenue increase

    # ------------------------------------------------------------------
    # 1. Summary Cards
    # ------------------------------------------------------------------

    def get_summary_cards(
        self,
        period_id: str,
        bu_id: Optional[str] = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> list[dict[str, Any]]:
        """Return summary metric cards for dashboard.

        Returns list of dicts with: metric_name, actual, comparator,
        variance_amount, variance_pct, is_favorable, is_material.
        Cards for: Total Revenue, Total COGS, Gross Profit, Total OpEx,
        EBITDA, Operating Income, Net Income.
        """
        logger.info(
            "get_summary_cards(period=%s, bu=%s, view=%s, base=%s)",
            period_id, bu_id, view_id, base_id,
        )
        vm = self._table("fact_variance_material")
        if vm.empty:
            return []

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)
        cards: list[dict[str, Any]] = []

        for acct_id, metric_name in _SUMMARY_CARD_ACCOUNTS:
            acct_rows = filtered[filtered["account_id"] == acct_id]
            if acct_rows.empty:
                continue

            actual = acct_rows["actual_amount"].sum()
            comparator = acct_rows["comparator_amount"].sum()
            var_amt = acct_rows["variance_amount"].sum()
            var_pct = (var_amt / comparator * 100) if comparator != 0 else None
            is_mat = bool(acct_rows["is_material"].any())

            acct_meta = self._account_lookup.get(acct_id, {})
            vsign = acct_meta.get("variance_sign")

            # Narrative lookup for this KPI account
            narr_oneliner = ""
            if not acct_rows.empty and "narrative_oneliner" in acct_rows.columns:
                first_narr = acct_rows.iloc[0].get("narrative_oneliner")
                if pd.notna(first_narr):
                    narr_oneliner = str(first_narr)

            cards.append(_clean_dict({
                "metric_name": metric_name,
                "account_id": acct_id,
                "actual": round(float(actual), 2),
                "comparator": round(float(comparator), 2),
                "variance_amount": round(float(var_amt), 2),
                "variance_pct": round(float(var_pct), 2) if var_pct is not None else None,
                "is_favorable": bool(self._is_favorable(var_amt, vsign)),
                "is_material": bool(is_mat),
                "narrative_oneliner": narr_oneliner,
            }))

        return cards

    # ------------------------------------------------------------------
    # 2. Waterfall
    # ------------------------------------------------------------------

    def get_waterfall(
        self,
        period_id: str,
        bu_id: Optional[str] = None,
        base_id: str = "BUDGET",
        view_id: str = "MTD",
    ) -> list[dict[str, Any]]:
        """Return waterfall steps for revenue bridge.

        Budget total -> each BU's variance -> Actual total.
        Each step: {name, value, cumulative, is_total, is_positive}.
        """
        logger.info(
            "get_waterfall(period=%s, bu=%s, base=%s)", period_id, bu_id, base_id,
        )
        vm = self._table("fact_variance_material")
        if vm.empty:
            return []

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)
        rev_rows = filtered[filtered["account_id"] == "acct_revenue"]

        if rev_rows.empty:
            return []

        budget_total = rev_rows["comparator_amount"].sum()
        actual_total = rev_rows["actual_amount"].sum()

        steps: list[dict[str, Any]] = []

        # Start with budget total
        steps.append({
            "name": "Budget",
            "value": round(budget_total, 2),
            "cumulative": round(budget_total, 2),
            "is_total": True,
            "is_positive": True,
        })

        # Each BU as a variance step
        bu_groups = rev_rows.groupby("bu_id").agg(
            variance_amount=("variance_amount", "sum"),
        ).reset_index()
        bu_groups = bu_groups.sort_values("bu_id")

        bu_names = self._table("dim_business_unit")
        bu_name_map = {}
        if not bu_names.empty:
            bu_name_map = dict(zip(bu_names["bu_id"], bu_names["bu_name"]))

        cumulative = budget_total
        for _, row in bu_groups.iterrows():
            var_amt = row["variance_amount"]
            cumulative += var_amt
            steps.append({
                "name": bu_name_map.get(row["bu_id"], row["bu_id"]),
                "value": round(var_amt, 2),
                "cumulative": round(cumulative, 2),
                "is_total": False,
                "is_positive": var_amt >= 0,
            })

        # End with actual total
        steps.append({
            "name": "Actual",
            "value": round(actual_total, 2),
            "cumulative": round(actual_total, 2),
            "is_total": True,
            "is_positive": True,
        })

        return steps

    # ------------------------------------------------------------------
    # 3. Heatmap
    # ------------------------------------------------------------------

    def get_heatmap(
        self,
        period_id: str,
        base_id: str = "BUDGET",
        view_id: str = "MTD",
        bu_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return heatmap of revenue variances: geo rows x BU columns.

        Returns: {rows: [geo_names], columns: [bu_names],
                  cells: [[{value, pct, is_material}]]}
        """
        logger.info("get_heatmap(period=%s, base=%s)", period_id, base_id)
        vm = self._table("fact_variance_material")
        if vm.empty:
            return {"rows": [], "columns": [], "cells": []}

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)
        # Revenue leaf accounts only (not calculated)
        rev = filtered[
            (filtered["pl_category"] == "Revenue") & (filtered["is_calculated"] == False)
        ]

        if rev.empty:
            return {"rows": [], "columns": [], "cells": []}

        # Aggregate by geo x BU
        pivot = rev.groupby(["geo_node_id", "bu_id"]).agg(
            variance_amount=("variance_amount", "sum"),
            variance_pct=("variance_pct", "mean"),
            is_material=("is_material", "any"),
        ).reset_index()

        # Get dimension labels
        dh = self._table("dim_hierarchy")
        geo_name_map = {}
        if not dh.empty:
            geo_nodes = dh[dh["dimension_name"] == "Geography"]
            geo_name_map = dict(zip(geo_nodes["node_id"], geo_nodes["node_name"]))

        bu_df = self._table("dim_business_unit")
        bu_name_map = {}
        if not bu_df.empty:
            bu_name_map = dict(zip(bu_df["bu_id"], bu_df["bu_name"]))

        geo_ids = sorted(pivot["geo_node_id"].unique())
        bu_ids = sorted(pivot["bu_id"].unique())

        geo_names = [geo_name_map.get(g, g) for g in geo_ids]
        bu_names = [bu_name_map.get(b, b) for b in bu_ids]

        # Build cell matrix
        cells: list[list[dict[str, Any]]] = []
        for geo_id in geo_ids:
            row: list[dict[str, Any]] = []
            for b_id in bu_ids:
                cell_data = pivot[
                    (pivot["geo_node_id"] == geo_id) & (pivot["bu_id"] == b_id)
                ]
                if cell_data.empty:
                    row.append({"value": 0.0, "pct": None, "is_material": False})
                else:
                    r = cell_data.iloc[0]
                    row.append({
                        "value": round(float(r["variance_amount"]), 2),
                        "pct": self._safe_float(r["variance_pct"]),
                        "is_material": bool(r["is_material"]),
                    })
            cells.append(row)

        # If bu_id filter is set, narrow columns to only that BU
        if bu_id is not None:
            matching_indices = [i for i, bid in enumerate(bu_ids) if bid == bu_id]
            if matching_indices:
                bu_names = [bu_names[i] for i in matching_indices]
                cells = [[row[i] for i in matching_indices] for row in cells]

        return {"rows": geo_names, "columns": bu_names, "cells": cells}

    # ------------------------------------------------------------------
    # 4. Trends
    # ------------------------------------------------------------------

    def get_trends(
        self,
        bu_id: Optional[str] = None,
        account_id: str = "acct_gross_revenue",
        base_id: str = "BUDGET",
        periods: int = 12,
        view_id: str = "MTD",
    ) -> list[dict[str, Any]]:
        """Return last N periods of MTD variance data for an account.

        Returns list of {period_id, actual, comparator, variance_amount, variance_pct}.
        """
        logger.info(
            "get_trends(bu=%s, account=%s, base=%s, periods=%d)",
            bu_id, account_id, base_id, periods,
        )
        vm = self._table("fact_variance_material")
        if vm.empty:
            return []

        filtered = self._filter_variance(vm, None, bu_id, view_id, base_id)
        acct_rows = filtered[filtered["account_id"] == account_id]

        if acct_rows.empty:
            return []

        # Aggregate by period
        by_period = acct_rows.groupby("period_id").agg(
            actual=("actual_amount", "sum"),
            comparator=("comparator_amount", "sum"),
            variance_amount=("variance_amount", "sum"),
        ).reset_index()

        by_period = by_period.sort_values("period_id", ascending=True)
        by_period = by_period.tail(periods)

        result: list[dict[str, Any]] = []
        for _, row in by_period.iterrows():
            comp = row["comparator"]
            var_pct = (row["variance_amount"] / comp * 100) if comp != 0 else None
            result.append({
                "period_id": row["period_id"],
                "actual": round(float(row["actual"]), 2),
                "comparator": round(float(row["comparator"]), 2),
                "variance_amount": round(float(row["variance_amount"]), 2),
                "variance_pct": round(var_pct, 2) if var_pct is not None else None,
            })

        return result

    # ------------------------------------------------------------------
    # 5. Variance List
    # ------------------------------------------------------------------

    def get_variance_list(
        self,
        period_id: str,
        bu_id: Optional[str] = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
        pl_category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "variance_amount",
        sort_desc: bool = True,
    ) -> dict[str, Any]:
        """Return paginated list of variances.

        Returns {items: [...], total_count, page, page_size, total_pages}.
        Each item: variance fields + account_name + narrative_oneliner.
        """
        logger.info(
            "get_variance_list(period=%s, bu=%s, view=%s, base=%s, cat=%s, page=%d)",
            period_id, bu_id, view_id, base_id, pl_category, page,
        )
        vm = self._table("fact_variance_material")
        if vm.empty:
            return {"items": [], "total_count": 0, "page": page, "page_size": page_size, "total_pages": 0}

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)

        # Only leaf accounts (not calculated rollups) for the list
        filtered = filtered[filtered["is_calculated"] == False]

        if pl_category is not None:
            filtered = filtered[filtered["pl_category"] == pl_category]

        total_count = len(filtered)
        total_pages = max(1, math.ceil(total_count / page_size))

        # Sort
        sort_col = sort_by if sort_by in filtered.columns else "variance_amount"
        sort_key = filtered[sort_col].abs() if sort_col == "variance_amount" else filtered[sort_col]
        filtered = filtered.assign(_sort_key=sort_key)
        filtered = filtered.sort_values("_sort_key", ascending=not sort_desc)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_df = filtered.iloc[start:end]

        items: list[dict[str, Any]] = []
        for _, row in page_df.iterrows():
            acct_meta = self._account_lookup.get(row["account_id"], {})
            items.append({
                "variance_id": row.get("variance_id", ""),
                "account_id": row["account_id"],
                "account_name": acct_meta.get("account_name", row["account_id"]),
                "bu_id": row["bu_id"],
                "period_id": row["period_id"],
                "actual_amount": round(float(row["actual_amount"]), 2),
                "comparator_amount": round(float(row["comparator_amount"]), 2),
                "variance_amount": round(float(row["variance_amount"]), 2),
                "variance_pct": self._safe_float(row.get("variance_pct")),
                "is_material": bool(row.get("is_material", False)),
                "is_netted": bool(row.get("is_netted", False)),
                "is_trending": bool(row.get("is_trending", False)),
                "geo_node_id": row.get("geo_node_id", ""),
                "segment_node_id": row.get("segment_node_id", ""),
                "lob_node_id": row.get("lob_node_id", ""),
                "costcenter_node_id": row.get("costcenter_node_id", ""),
                "variance_sign": row.get("variance_sign", "natural"),
                "pl_category": row.get("pl_category", ""),
                "narrative_oneliner": row.get("narrative_oneliner"),
                "narrative_detail": row.get("narrative_detail"),
                "narrative_source": row.get("narrative_source"),
            })

        return {
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # ------------------------------------------------------------------
    # 6. Variance Detail
    # ------------------------------------------------------------------

    def get_variance_detail(self, variance_id: str) -> Optional[dict[str, Any]]:
        """Return enriched variance detail with decomposition and correlations.

        Joins fact_variance_material + fact_decomposition + fact_correlations.
        Returns None if variance_id not found.
        """
        logger.info("get_variance_detail(variance_id=%s)", variance_id)
        vm = self._table("fact_variance_material")
        if vm.empty:
            return None

        row = vm[vm["variance_id"] == variance_id]
        if row.empty:
            return None

        r = row.iloc[0]
        acct_meta = self._account_lookup.get(r["account_id"], {})

        result: dict[str, Any] = {
            "variance_id": variance_id,
            "period_id": r["period_id"],
            "bu_id": r["bu_id"],
            "account_id": r["account_id"],
            "account_name": acct_meta.get("account_name", r["account_id"]),
            "geo_node_id": r["geo_node_id"],
            "segment_node_id": r["segment_node_id"],
            "lob_node_id": r["lob_node_id"],
            "costcenter_node_id": r["costcenter_node_id"],
            "view_id": r["view_id"],
            "base_id": r["base_id"],
            "actual_amount": round(float(r["actual_amount"]), 2),
            "comparator_amount": round(float(r["comparator_amount"]), 2),
            "variance_amount": round(float(r["variance_amount"]), 2),
            "variance_pct": self._safe_float(r.get("variance_pct")),
            "is_material": bool(r.get("is_material", False)),
            "is_netted": bool(r.get("is_netted", False)),
            "is_trending": bool(r.get("is_trending", False)),
            "pl_category": r.get("pl_category"),
            "variance_sign": acct_meta.get("variance_sign"),
            "narratives": {
                "detail": r.get("narrative_detail"),
                "midlevel": r.get("narrative_midlevel"),
                "summary": r.get("narrative_summary"),
                "oneliner": r.get("narrative_oneliner"),
                "board": r.get("narrative_board"),
            },
            "narrative_source": r.get("narrative_source"),
            "decomposition": None,
            "correlations": [],
        }

        # Join decomposition
        decomp = self._table("fact_decomposition")
        if not decomp.empty:
            d_row = decomp[decomp["variance_id"] == variance_id]
            if not d_row.empty:
                d = d_row.iloc[0]
                components = d["components"]
                # Parse JSON string if needed
                if isinstance(components, str):
                    try:
                        components = json.loads(components)
                    except Exception:
                        components = {}
                result["decomposition"] = {
                    "method": d["method"],
                    "components": components,
                    "total_explained": self._safe_float(d["total_explained"]),
                    "residual": self._safe_float(d["residual"]),
                }

        # Join correlations
        corr = self._table("fact_correlations")
        if not corr.empty:
            c_rows = corr[
                (corr["variance_id_a"] == variance_id)
                | (corr["variance_id_b"] == variance_id)
            ]
            for _, c in c_rows.iterrows():
                other_id = (
                    c["variance_id_b"]
                    if c["variance_id_a"] == variance_id
                    else c["variance_id_a"]
                )
                result["correlations"].append({
                    "correlation_id": c["correlation_id"],
                    "other_variance_id": other_id,
                    "correlation_score": self._safe_float(c["correlation_score"]),
                    "dimension_overlap": c.get("dimension_overlap", []),
                    "directional_match": bool(c.get("directional_match", False)),
                    "hypothesis": c.get("hypothesis"),
                    "confidence": self._safe_float(c.get("confidence")),
                })

        return result

    # ------------------------------------------------------------------
    # 7. P&L Statement
    # ------------------------------------------------------------------

    def get_pl_statement(
        self,
        period_id: str,
        bu_id: Optional[str] = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> list[dict[str, Any]]:
        """Return nested P&L statement as a tree.

        Root node: acct_total_pl with children in standard P&L order.
        Each row: account_id, account_name, depth, is_calculated, is_leaf,
        actual, comparator, variance_amount, variance_pct, is_material,
        pl_category, children.
        """
        logger.info(
            "get_pl_statement(period=%s, bu=%s, view=%s, base=%s)",
            period_id, bu_id, view_id, base_id,
        )
        vm = self._table("fact_variance_material")
        accts = self._table("dim_account")
        if vm.empty or accts.empty:
            return []

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)

        # Aggregate by account_id across cost centers / geos
        agg = filtered.groupby("account_id").agg(
            actual=("actual_amount", "sum"),
            comparator=("comparator_amount", "sum"),
            variance_amount=("variance_amount", "sum"),
            is_material=("is_material", "any"),
        ).reset_index()

        # Also pick first narrative per account for P&L display
        narr_cols = ["account_id", "narrative_detail", "narrative_oneliner", "narrative_source"]
        narr_available = [c for c in narr_cols if c in filtered.columns]
        narr_lookup: dict[str, dict] = {}
        if len(narr_available) > 1:  # at least account_id + one narrative
            narr_df = filtered[narr_available].drop_duplicates(subset=["account_id"])
            for _, nrow in narr_df.iterrows():
                narr_lookup[str(nrow["account_id"])] = {
                    c: str(nrow.get(c, "")) if pd.notna(nrow.get(c)) else ""
                    for c in narr_available if c != "account_id"
                }

        amounts: dict[str, dict[str, Any]] = {}
        for _, row in agg.iterrows():
            acct_id = str(row["account_id"])
            comp = row["comparator"]
            var_pct = (row["variance_amount"] / comp * 100) if comp != 0 else None
            narr = narr_lookup.get(acct_id, {})
            amounts[acct_id] = {
                "actual": round(float(row["actual"]), 2),
                "comparator": round(float(row["comparator"]), 2),
                "variance_amount": round(float(row["variance_amount"]), 2),
                "variance_pct": round(var_pct, 2) if var_pct is not None else None,
                "is_material": bool(row["is_material"]),
                "narrative_detail": narr.get("narrative_detail", ""),
                "narrative_oneliner": narr.get("narrative_oneliner", ""),
                "narrative_source": narr.get("narrative_source", ""),
            }

        def _build_node(acct_id: str, depth: int = 0) -> Optional[dict[str, Any]]:
            meta = self._account_lookup.get(acct_id)
            if meta is None:
                return None

            child_ids = self._account_children.get(acct_id, [])
            # Sort children by sort_order
            child_ids_sorted = sorted(
                child_ids,
                key=lambda cid: self._account_lookup.get(cid, {}).get("sort_order", 999),
            )
            children = []
            for cid in child_ids_sorted:
                child_node = _build_node(cid, depth + 1)
                if child_node is not None:
                    children.append(child_node)

            amt = amounts.get(acct_id, {})
            return {
                "account_id": acct_id,
                "account_name": meta.get("account_name", acct_id),
                "depth": depth,
                "is_calculated": bool(meta.get("is_calculated", False)),
                "is_leaf": bool(meta.get("is_leaf", True)),
                "actual": amt.get("actual", 0.0),
                "comparator": amt.get("comparator", 0.0),
                "variance_amount": amt.get("variance_amount", 0.0),
                "variance_pct": amt.get("variance_pct"),
                "is_material": amt.get("is_material", False),
                "pl_category": meta.get("pl_category"),
                "narrative_detail": amt.get("narrative_detail", ""),
                "narrative_oneliner": amt.get("narrative_oneliner", ""),
                "narrative_source": amt.get("narrative_source", ""),
                "children": children,
            }

        root = _build_node("acct_total_pl")
        if root is None:
            return []
        return [root]

    # ------------------------------------------------------------------
    # 8. Account Detail
    # ------------------------------------------------------------------

    def get_account_detail(
        self,
        account_id: str,
        period_id: str,
        bu_id: Optional[str] = None,
        view_id: str = "MTD",
        base_id: str = "BUDGET",
    ) -> Optional[dict[str, Any]]:
        """Return account summary + child variances + decomposition.

        Returns None if account not found.
        """
        logger.info(
            "get_account_detail(account=%s, period=%s, bu=%s)",
            account_id, period_id, bu_id,
        )
        meta = self._account_lookup.get(account_id)
        if meta is None:
            return None

        vm = self._table("fact_variance_material")
        if vm.empty:
            return None

        filtered = self._filter_variance(vm, period_id, bu_id, view_id, base_id)

        # Account-level aggregate
        acct_rows = filtered[filtered["account_id"] == account_id]
        actual = acct_rows["actual_amount"].sum() if not acct_rows.empty else 0.0
        comparator = acct_rows["comparator_amount"].sum() if not acct_rows.empty else 0.0
        var_amt = acct_rows["variance_amount"].sum() if not acct_rows.empty else 0.0
        var_pct = (var_amt / comparator * 100) if comparator != 0 else None

        result: dict[str, Any] = {
            "account_id": account_id,
            "account_name": meta.get("account_name", account_id),
            "pl_category": meta.get("pl_category"),
            "is_calculated": bool(meta.get("is_calculated", False)),
            "variance_sign": meta.get("variance_sign"),
            "actual": round(actual, 2),
            "comparator": round(comparator, 2),
            "variance_amount": round(var_amt, 2),
            "variance_pct": round(var_pct, 2) if var_pct is not None else None,
            "child_variances": [],
            "decomposition": [],
        }

        # Child account variances
        child_ids = self._account_children.get(account_id, [])
        for cid in child_ids:
            child_rows = filtered[filtered["account_id"] == cid]
            if child_rows.empty:
                continue
            c_actual = child_rows["actual_amount"].sum()
            c_comp = child_rows["comparator_amount"].sum()
            c_var = child_rows["variance_amount"].sum()
            c_pct = (c_var / c_comp * 100) if c_comp != 0 else None
            c_meta = self._account_lookup.get(cid, {})
            result["child_variances"].append({
                "account_id": cid,
                "account_name": c_meta.get("account_name", cid),
                "actual": round(c_actual, 2),
                "comparator": round(c_comp, 2),
                "variance_amount": round(c_var, 2),
                "variance_pct": round(c_pct, 2) if c_pct is not None else None,
            })

        # Decomposition for this account's variances
        decomp = self._table("fact_decomposition")
        if not decomp.empty and not acct_rows.empty:
            var_ids = acct_rows["variance_id"].tolist()
            d_rows = decomp[decomp["variance_id"].isin(var_ids)]
            for _, d in d_rows.iterrows():
                result["decomposition"].append({
                    "variance_id": d["variance_id"],
                    "method": d["method"],
                    "components": d["components"],
                    "total_explained": self._safe_float(d["total_explained"]),
                    "residual": self._safe_float(d["residual"]),
                })

        return result

    # ------------------------------------------------------------------
    # 9. Dimension Hierarchy
    # ------------------------------------------------------------------

    def get_dimension_hierarchy(self, dimension_name: str) -> list[dict[str, Any]]:
        """Return hierarchy tree for a dimension (Geography, Segment, LOB, CostCenter).

        Returns list with single root node dict containing nested children.
        """
        logger.info("get_dimension_hierarchy(dimension=%s)", dimension_name)
        dh = self._table("dim_hierarchy")
        if dh.empty:
            return []

        dim_nodes = dh[dh["dimension_name"].str.lower() == dimension_name.lower()]
        if dim_nodes.empty:
            return []

        # Build tree from flat parent-child data
        nodes_by_id: dict[str, dict[str, Any]] = {}
        for _, row in dim_nodes.iterrows():
            nodes_by_id[row["node_id"]] = {
                "node_id": row["node_id"],
                "node_name": row["node_name"],
                "parent_id": row.get("parent_id") if pd.notna(row.get("parent_id")) else None,
                "depth": int(row["depth"]),
                "is_leaf": bool(row["is_leaf"]),
                "children": [],
            }

        roots: list[dict[str, Any]] = []
        for nid, node in nodes_by_id.items():
            pid = node["parent_id"]
            if pid and pid in nodes_by_id:
                nodes_by_id[pid]["children"].append(node)
            else:
                roots.append(node)

        return roots

    # ------------------------------------------------------------------
    # 10. Business Units
    # ------------------------------------------------------------------

    def get_business_units(self) -> list[dict[str, Any]]:
        """Return list of business unit dicts."""
        logger.info("get_business_units()")
        bu = self._table("dim_business_unit")
        if bu.empty:
            return []
        return bu.sort_values("sort_order").to_dict(orient="records")

    # ------------------------------------------------------------------
    # 11. Accounts
    # ------------------------------------------------------------------

    def get_accounts(self) -> list[dict[str, Any]]:
        """Return list of account dicts with hierarchy info."""
        logger.info("get_accounts()")
        accts = self._table("dim_account")
        if accts.empty:
            return []
        result = accts.sort_values("sort_order").to_dict(orient="records")
        # Clean up NaN values
        for row in result:
            for k, v in row.items():
                if isinstance(v, float) and math.isnan(v):
                    row[k] = None
        return result

    # ------------------------------------------------------------------
    # 12. Periods
    # ------------------------------------------------------------------

    def get_periods(self) -> list[dict[str, Any]]:
        """Return list of period dicts with has_data flag.

        The has_data flag indicates whether fact_variance_material
        contains rows for that period, allowing the frontend to default
        to the latest period that actually has computed data.
        """
        logger.info("get_periods()")
        periods = self._table("dim_period")
        if periods.empty:
            return []

        # Determine which periods have variance data
        vm = self._tables.get("fact_variance_material", pd.DataFrame())
        periods_with_data: set[str] = set()
        if not vm.empty and "period_id" in vm.columns:
            periods_with_data = set(vm["period_id"].dropna().unique())

        records = periods.sort_values("period_id").to_dict(orient="records")
        for rec in records:
            rec["has_data"] = rec.get("period_id", "") in periods_with_data
        return records

    # ------------------------------------------------------------------
    # 13. Netting Alerts
    # ------------------------------------------------------------------

    def get_netting_alerts(self, period_id: str, bu_id: Optional[str] = None, limit: int = 5) -> list[dict]:
        """Get top netting alerts from fact_netting_flags."""
        import json as _json

        df = self._tables.get("fact_netting_flags")
        if df is None or df.empty:
            return []

        filtered = df[df["period_id"] == period_id].copy() if "period_id" in df.columns else df.copy()

        # Sort by gross_variance descending (biggest offsetting movements first)
        if "gross_variance" in filtered.columns:
            filtered = filtered.sort_values("gross_variance", ascending=False)

        alerts: list[dict] = []
        for _, row in filtered.head(limit).iterrows():
            # Extract child details to find the two biggest offsetting items
            child_details = row.get("child_details", [])
            if isinstance(child_details, str):
                try:
                    child_details = _json.loads(child_details)
                except Exception:
                    child_details = []

            # Find largest positive and negative children
            positives = sorted(
                [c for c in child_details if isinstance(c, dict) and c.get("variance_amount", c.get("variance", 0)) > 0],
                key=lambda x: x.get("variance_amount", x.get("variance", 0)), reverse=True,
            )
            negatives = sorted(
                [c for c in child_details if isinstance(c, dict) and c.get("variance_amount", c.get("variance", 0)) < 0],
                key=lambda x: abs(x.get("variance_amount", x.get("variance", 0))), reverse=True,
            )

            left_id = positives[0].get("account_id", "") if positives else ""
            left_meta = self._account_lookup.get(left_id, {})
            left_name = (positives[0].get("account_name") or (left_meta.get("account_name") if isinstance(left_meta, dict) else left_id) or left_id) if positives else "Item A"
            left_val = positives[0].get("variance_amount", positives[0].get("variance", 0)) if positives else 0
            right_id = negatives[0].get("account_id", "") if negatives else ""
            right_meta = self._account_lookup.get(right_id, {})
            right_name = (negatives[0].get("account_name") or (right_meta.get("account_name") if isinstance(right_meta, dict) else right_id) or right_id) if negatives else "Item B"
            right_val = negatives[0].get("variance_amount", negatives[0].get("variance", 0)) if negatives else 0

            net = row.get("net_variance", 0)

            alerts.append({
                "left": f"{left_name} +${abs(left_val/1000):.1f}K" if left_val > 0 else f"{left_name} -${abs(left_val/1000):.1f}K",
                "right": f"{right_name} -${abs(right_val/1000):.1f}K" if right_val < 0 else f"{right_name} +${abs(right_val/1000):.1f}K",
                "net": f"{'+'if net > 0 else '-'}${abs(net/1000):.1f}K",
                "favorable": net > 0,
                "netting_ratio": round(row.get("netting_ratio", 0), 1),
            })

        return alerts

    # ------------------------------------------------------------------
    # 14. Trend Alerts
    # ------------------------------------------------------------------

    def get_trend_alerts(self, period_id: Optional[str] = None, bu_id: Optional[str] = None, limit: int = 5) -> list[dict]:
        """Get top trend alerts from fact_trend_flags."""
        df = self._tables.get("fact_trend_flags")
        if df is None or df.empty:
            return []

        filtered = df.copy()
        if bu_id and "bu_id" in filtered.columns:
            # Note: trend flags may not have bu_id directly
            pass

        # Sort by absolute cumulative_amount descending
        if "cumulative_amount" in filtered.columns:
            filtered["abs_cum"] = filtered["cumulative_amount"].abs()
            filtered = filtered.sort_values("abs_cum", ascending=False)

        # Deduplicate by account_id (take the longest streak per account)
        if "account_id" in filtered.columns:
            filtered = filtered.drop_duplicates(subset=["account_id"], keep="first")

        alerts: list[dict] = []
        for _, row in filtered.head(limit).iterrows():
            acct_id = str(row.get("account_id", "Unknown"))
            acct_meta = self._account_lookup.get(acct_id, {})
            acct = acct_meta.get("account_name") or acct_id.replace("acct_", "").replace("_", " ").title()
            periods = int(row.get("consecutive_periods", 0))
            direction = row.get("direction", "increasing")
            cum_amount = row.get("cumulative_amount", 0)

            desc = f"{acct}: {periods} consecutive months {direction}"
            proj = f"{'+'if cum_amount > 0 else ''}${cum_amount/1000:.0f}K projected YE" if cum_amount else ""

            alerts.append({
                "description": desc,
                "projection": proj,
            })

        return alerts

    # ------------------------------------------------------------------
    # 15. Section Narratives (Phase 2C)
    # ------------------------------------------------------------------

    def get_section_narratives(
        self,
        period_id: str,
        base_id: str = "BUDGET",
        view_id: str = "MTD",
    ) -> list[dict[str, Any]]:
        """Return section narratives for each P&L section."""
        df = self._tables.get("fact_section_narrative")
        if df is None or df.empty:
            return []

        filtered = df[
            (df["period_id"] == period_id)
            & (df["base_id"] == base_id)
            & (df["view_id"] == view_id)
        ]
        return [_clean_dict(row.to_dict()) for _, row in filtered.iterrows()]

    # ------------------------------------------------------------------
    # 16. Executive Summary (Phase 2C)
    # ------------------------------------------------------------------

    def get_executive_summary(
        self,
        period_id: str,
        base_id: str = "BUDGET",
        view_id: str = "MTD",
    ) -> Optional[dict[str, Any]]:
        """Return the executive summary for a period."""
        df = self._tables.get("fact_executive_summary")
        if df is None or df.empty:
            return None

        filtered = df[
            (df["period_id"] == period_id)
            & (df["base_id"] == base_id)
            & (df["view_id"] == view_id)
        ]
        if filtered.empty:
            return None

        return _clean_dict(filtered.iloc[0].to_dict())
