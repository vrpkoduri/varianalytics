"""NetworkX implementation of the Variance Knowledge Graph.

In-memory directed graph (``networkx.DiGraph``) with typed nodes and edges.
Built from engine pipeline context or persisted parquet data.

Node attributes always include ``node_type`` (str).
Edge attributes always include ``edge_type`` (str).

Performance: Builds ~100K variance nodes + edges in < 2 seconds.
Memory: ~50-80 MB for full 12-period dataset.

Phase 3A MVP.  Swappable for Neo4j via the abstract VarianceGraph interface.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Optional

import networkx as nx
import pandas as pd

from shared.knowledge.graph_interface import VarianceGraph

logger = logging.getLogger(__name__)

# Calculated row dependencies (account_id → [dependency account_ids])
# These represent the calc_depends_on edges.
CALCULATED_ROW_DEPS: dict[str, list[str]] = {
    "gross_profit": ["total_revenue", "total_cogs"],
    "ebitda": ["gross_profit", "total_opex"],
    "ebit": ["ebitda"],  # EBITDA - D&A (simplified)
    "ebt": ["ebit", "total_nonop"],
    "net_income": ["ebt", "total_tax"],
}

# P&L section mapping (pl_category → section name)
PL_SECTION_MAP: dict[str, str] = {
    "Revenue": "revenue",
    "COGS": "cost_of_goods_sold",
    "OpEx": "operating_expenses",
    "NonOp": "non_operating",
    "Tax": "tax",
}


class NetworkXGraph(VarianceGraph):
    """NetworkX-based implementation of the variance knowledge graph.

    Uses a single ``networkx.DiGraph`` with typed nodes and edges.
    All traversal is done via NetworkX's built-in graph algorithms.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Build from engine context
    # ------------------------------------------------------------------

    def build_from_context(self, context: dict[str, Any]) -> None:
        """Build graph from engine pipeline context dict.

        Expected context keys (all optional — missing data is skipped):
            acct_meta           -- dict[account_id, dict]
            material_variances  -- DataFrame
            all_variances       -- DataFrame
            correlations        -- DataFrame
            netting_flags       -- DataFrame
            trend_flags         -- DataFrame
            decomposition       -- DataFrame
            period_id           -- str
            data_dir            -- str
        """
        self._graph.clear()

        acct_meta = context.get("acct_meta", {})
        material = context.get("material_variances")
        correlations = context.get("correlations")
        netting = context.get("netting_flags")
        trends = context.get("trend_flags")
        decomposition = context.get("decomposition")
        data_dir = context.get("data_dir", "data/output")

        # Load dimension tables from disk for hierarchy/period/BU nodes
        from shared.data.loader import DataLoader

        loader = DataLoader(data_dir)

        # Structural nodes
        self._add_account_hierarchy(acct_meta)
        self._add_calc_dependencies()

        dim_hierarchy = loader.load_table("dim_hierarchy") if loader.table_exists("dim_hierarchy") else None
        if dim_hierarchy is not None:
            self._add_dimension_hierarchies(dim_hierarchy)

        dim_period = loader.load_table("dim_period") if loader.table_exists("dim_period") else None
        if dim_period is not None:
            self._add_periods(dim_period)

        dim_bu = loader.load_table("dim_business_unit") if loader.table_exists("dim_business_unit") else None
        if dim_bu is not None:
            self._add_business_units(dim_bu)

        # Variance nodes + relationship edges
        if isinstance(material, pd.DataFrame) and not material.empty:
            self._add_variances(material, acct_meta)
        elif isinstance(context.get("all_variances"), pd.DataFrame):
            self._add_variances(context["all_variances"], acct_meta)

        if isinstance(correlations, pd.DataFrame) and not correlations.empty:
            self._add_correlations(correlations)

        if isinstance(netting, pd.DataFrame) and not netting.empty:
            self._add_netting(netting)

        if isinstance(trends, pd.DataFrame) and not trends.empty:
            self._add_trends(trends)

        if isinstance(decomposition, pd.DataFrame) and not decomposition.empty:
            self._add_decomposition(decomposition)

        # Section nodes
        self._add_sections(material)

        logger.info(
            "Knowledge graph built: %d nodes, %d edges",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    def build_from_data(
        self,
        data_dir: str,
        period_id: Optional[str] = None,
    ) -> None:
        """Build graph from persisted parquet files."""
        self._graph.clear()

        from shared.data.loader import DataLoader

        loader = DataLoader(data_dir)

        # Account hierarchy from dim_account
        dim_account = loader.load_table("dim_account") if loader.table_exists("dim_account") else None
        if dim_account is not None:
            acct_meta = self._acct_meta_from_dim(dim_account)
            self._add_account_hierarchy(acct_meta)
            self._add_calc_dependencies()
        else:
            acct_meta = {}

        # Dimension hierarchies
        dim_hierarchy = loader.load_table("dim_hierarchy") if loader.table_exists("dim_hierarchy") else None
        if dim_hierarchy is not None:
            self._add_dimension_hierarchies(dim_hierarchy)

        # Periods
        dim_period = loader.load_table("dim_period") if loader.table_exists("dim_period") else None
        if dim_period is not None:
            self._add_periods(dim_period)

        # Business units
        dim_bu = loader.load_table("dim_business_unit") if loader.table_exists("dim_business_unit") else None
        if dim_bu is not None:
            self._add_business_units(dim_bu)

        # Variances
        material = loader.load_table("fact_variance_material") if loader.table_exists("fact_variance_material") else None
        if isinstance(material, pd.DataFrame) and not material.empty:
            if period_id:
                material = material[material["period_id"] == period_id]
            self._add_variances(material, acct_meta)
            self._add_sections(material)

        # Correlations
        correlations = loader.load_table("fact_correlations") if loader.table_exists("fact_correlations") else None
        if isinstance(correlations, pd.DataFrame) and not correlations.empty:
            self._add_correlations(correlations)

        # Netting
        netting = loader.load_table("fact_netting_flags") if loader.table_exists("fact_netting_flags") else None
        if isinstance(netting, pd.DataFrame) and not netting.empty:
            self._add_netting(netting)

        # Trends
        trends = loader.load_table("fact_trend_flags") if loader.table_exists("fact_trend_flags") else None
        if isinstance(trends, pd.DataFrame) and not trends.empty:
            self._add_trends(trends)

        # Decomposition
        decomp = loader.load_table("fact_decomposition") if loader.table_exists("fact_decomposition") else None
        if isinstance(decomp, pd.DataFrame) and not decomp.empty:
            self._add_decomposition(decomp)

        logger.info(
            "Knowledge graph built from data: %d nodes, %d edges",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    # ------------------------------------------------------------------
    # Internal: add nodes/edges by type
    # ------------------------------------------------------------------

    def _acct_meta_from_dim(self, dim_account: pd.DataFrame) -> dict[str, dict]:
        """Build acct_meta dict from dim_account DataFrame."""
        meta: dict[str, dict] = {}
        for _, row in dim_account.iterrows():
            acct_id = str(row.get("account_id", ""))
            meta[acct_id] = {
                "account_id": acct_id,
                "account_name": str(row.get("account_name", acct_id)),
                "parent_id": row.get("parent_id"),
                "pl_category": str(row.get("pl_category", "")),
                "variance_sign": str(row.get("variance_sign", "natural")),
                "is_calculated": bool(row.get("is_calculated", False)),
            }
        return meta

    def _add_account_hierarchy(self, acct_meta: dict[str, dict]) -> None:
        """Add account nodes and parent_of edges."""
        for acct_id, meta in acct_meta.items():
            self._graph.add_node(
                acct_id,
                node_type="account",
                name=meta.get("account_name", acct_id),
                pl_category=meta.get("pl_category", ""),
                variance_sign=meta.get("variance_sign", "natural"),
                is_calculated=meta.get("is_calculated", False),
                parent_id=meta.get("parent_id"),
            )

        # Parent-of edges
        for acct_id, meta in acct_meta.items():
            parent = meta.get("parent_id")
            if parent and parent in acct_meta:
                self._graph.add_edge(parent, acct_id, edge_type="parent_of")

    def _add_calc_dependencies(self) -> None:
        """Add calc_depends_on edges for calculated rows (EBITDA, GP, etc.)."""
        for calc_row, deps in CALCULATED_ROW_DEPS.items():
            for dep in deps:
                if self._graph.has_node(calc_row) and self._graph.has_node(dep):
                    self._graph.add_edge(calc_row, dep, edge_type="calc_depends_on")

    def _add_dimension_hierarchies(self, dim_hierarchy: pd.DataFrame) -> None:
        """Add dimension hierarchy nodes and parent_of edges."""
        for _, row in dim_hierarchy.iterrows():
            dim_type = str(row.get("dimension_name", "")).lower()
            node_id = str(row.get("node_id", ""))
            full_id = f"{dim_type}:{node_id}"
            parent_node = row.get("parent_id")

            self._graph.add_node(
                full_id,
                node_type="dimension",
                dim_type=dim_type,
                name=str(row.get("node_name", node_id)),
                depth=int(row.get("depth", 0)),
                is_leaf=bool(row.get("is_leaf", True)),
            )

            if parent_node and str(parent_node) != "" and str(parent_node) != "nan":
                parent_full_id = f"{dim_type}:{parent_node}"
                if self._graph.has_node(parent_full_id):
                    self._graph.add_edge(parent_full_id, full_id, edge_type="parent_of")

    def _add_periods(self, dim_period: pd.DataFrame) -> None:
        """Add period nodes and prior_period_of chain."""
        periods = sorted(dim_period["period_id"].unique().tolist())

        for pid in periods:
            row = dim_period[dim_period["period_id"] == pid].iloc[0] if len(dim_period[dim_period["period_id"] == pid]) > 0 else {}
            month = 0
            if isinstance(pid, str) and len(pid) >= 7:
                try:
                    month = int(pid[5:7])
                except (ValueError, IndexError):
                    pass

            self._graph.add_node(
                pid,
                node_type="period",
                fiscal_year=str(row.get("fiscal_year", "")),
                month=month,
                is_high_season=month in (11, 12, 1),
                is_low_season=month in (7, 8),
            )

        # Temporal chain: prior_period_of
        for i in range(1, len(periods)):
            self._graph.add_edge(
                periods[i], periods[i - 1], edge_type="prior_period_of"
            )

    def _add_business_units(self, dim_bu: pd.DataFrame) -> None:
        """Add business unit nodes."""
        for _, row in dim_bu.iterrows():
            bu_id = str(row.get("bu_id", ""))
            self._graph.add_node(
                bu_id,
                node_type="business_unit",
                name=str(row.get("bu_name", bu_id)),
            )

    def _add_variances(
        self, df: pd.DataFrame, acct_meta: dict[str, dict]
    ) -> None:
        """Add variance nodes and belongs_to edges."""
        for _, row in df.iterrows():
            vid = str(row.get("variance_id", ""))
            if not vid:
                continue

            acct_id = str(row.get("account_id", ""))
            bu_id = str(row.get("bu_id", ""))
            period_id = str(row.get("period_id", ""))
            pl_cat = str(row.get("pl_category", acct_meta.get(acct_id, {}).get("pl_category", "")))

            self._graph.add_node(
                vid,
                node_type="variance",
                account_id=acct_id,
                bu_id=bu_id,
                period_id=period_id,
                base_id=str(row.get("base_id", "")),
                view_id=str(row.get("view_id", "")),
                variance_amount=float(row.get("variance_amount", 0)),
                variance_pct=float(row.get("variance_pct", 0)) if pd.notna(row.get("variance_pct")) else None,
                is_material=bool(row.get("is_material", False)),
                is_netted=bool(row.get("is_netted", False)),
                is_trending=bool(row.get("is_trending", False)),
                pl_category=pl_cat,
                account_name=str(row.get("account_name", acct_meta.get(acct_id, {}).get("account_name", acct_id))),
            )

            # belongs_to edges
            if acct_id and self._graph.has_node(acct_id):
                self._graph.add_edge(vid, acct_id, edge_type="belongs_to")
            if bu_id and self._graph.has_node(bu_id):
                self._graph.add_edge(vid, bu_id, edge_type="belongs_to")
            if period_id and self._graph.has_node(period_id):
                self._graph.add_edge(vid, period_id, edge_type="belongs_to")

    def _add_correlations(self, df: pd.DataFrame) -> None:
        """Add correlates_with edges (bidirectional) and hypothesis nodes."""
        for _, row in df.iterrows():
            vid_a = str(row.get("variance_id_a", ""))
            vid_b = str(row.get("variance_id_b", ""))
            score = float(row.get("correlation_score", 0))
            hypothesis = row.get("hypothesis")

            if not (vid_a and vid_b):
                continue

            edge_attrs: dict[str, Any] = {
                "edge_type": "correlates_with",
                "score": score,
            }

            if hypothesis and str(hypothesis) not in ("", "nan", "None"):
                corr_id = str(row.get("correlation_id", f"{vid_a}_{vid_b}"))
                hyp_node_id = f"hypothesis:{corr_id}"
                self._graph.add_node(
                    hyp_node_id,
                    node_type="hypothesis",
                    text=str(hypothesis),
                    confidence=float(row.get("confidence", 0)),
                )
                edge_attrs["hypothesis_node"] = hyp_node_id

            # Bidirectional correlation edges
            if self._graph.has_node(vid_a) and self._graph.has_node(vid_b):
                self._graph.add_edge(vid_a, vid_b, **edge_attrs)
                self._graph.add_edge(vid_b, vid_a, **edge_attrs)

    def _add_netting(self, df: pd.DataFrame) -> None:
        """Add nets_with edges from netting flags."""
        for _, row in df.iterrows():
            parent_node_id = str(row.get("parent_node_id", ""))
            check_type = str(row.get("check_type", ""))
            net_variance = float(row.get("net_variance", 0))
            gross_variance = float(row.get("gross_variance", 0))
            netting_ratio = float(row.get("netting_ratio", 0))

            # Try to parse child details for edge targets
            child_details = row.get("child_details", "[]")
            if isinstance(child_details, str):
                try:
                    child_details = json.loads(child_details)
                except (json.JSONDecodeError, TypeError):
                    child_details = []

            # Store netting info on the parent node if it's a variance
            if self._graph.has_node(parent_node_id):
                self._graph.nodes[parent_node_id]["netting"] = {
                    "net_variance": net_variance,
                    "gross_variance": gross_variance,
                    "netting_ratio": netting_ratio,
                    "check_type": check_type,
                }

    def _add_trends(self, df: pd.DataFrame) -> None:
        """Add has_trend edges linking variances to their trend periods."""
        for _, row in df.iterrows():
            acct_id = str(row.get("account_id", ""))
            direction = str(row.get("direction", ""))
            consec = int(row.get("consecutive_periods", 0))
            cumulative = float(row.get("cumulative_amount", 0))

            # Store trend info on the account node
            if self._graph.has_node(acct_id):
                existing = self._graph.nodes[acct_id].get("trend")
                if not existing or consec > existing.get("consecutive_periods", 0):
                    self._graph.nodes[acct_id]["trend"] = {
                        "direction": direction,
                        "consecutive_periods": consec,
                        "cumulative_amount": cumulative,
                    }

    def _add_decomposition(self, df: pd.DataFrame) -> None:
        """Add decomposition data to variance nodes."""
        for _, row in df.iterrows():
            vid = str(row.get("variance_id", ""))
            if not vid or not self._graph.has_node(vid):
                continue

            components = row.get("components", {})
            if isinstance(components, str):
                try:
                    components = json.loads(components)
                except (json.JSONDecodeError, TypeError):
                    components = {}

            self._graph.nodes[vid]["decomposition"] = {
                "method": str(row.get("method", "")),
                "components": components if isinstance(components, dict) else {},
            }

    def _add_sections(self, material: Optional[pd.DataFrame]) -> None:
        """Add section nodes and section_member_of edges."""
        if not isinstance(material, pd.DataFrame) or material.empty:
            return

        # Build section nodes per period
        for period_id in material["period_id"].unique():
            period_df = material[material["period_id"] == period_id]
            for pl_cat in period_df["pl_category"].dropna().unique():
                section_name = PL_SECTION_MAP.get(str(pl_cat), str(pl_cat).lower())
                section_id = f"section:{section_name}:{period_id}"
                self._graph.add_node(
                    section_id,
                    node_type="section",
                    section_name=section_name,
                    period_id=str(period_id),
                )

                # section_member_of edges from variances to sections
                cat_rows = period_df[period_df["pl_category"] == pl_cat]
                for _, row in cat_rows.iterrows():
                    vid = str(row.get("variance_id", ""))
                    if vid and self._graph.has_node(vid):
                        self._graph.add_edge(vid, section_id, edge_type="section_member_of")

    # ------------------------------------------------------------------
    # Core queries
    # ------------------------------------------------------------------

    def get_full_context(self, variance_id: str) -> dict[str, Any]:
        """Return all relationship data for a single variance."""
        if not self._graph.has_node(variance_id):
            return {
                "correlations": [],
                "netting": None,
                "trends": None,
                "decomposition": None,
                "siblings": [],
                "peer_variances": [],
                "parent_chain": [],
                "period_history": [],
            }

        node = self._graph.nodes[variance_id]
        acct_id = node.get("account_id", "")
        bu_id = node.get("bu_id", "")

        return {
            "correlations": self.get_correlations(variance_id),
            "netting": node.get("netting"),
            "trends": self._get_trend_for_account(acct_id),
            "decomposition": node.get("decomposition"),
            "siblings": self.get_siblings(variance_id),
            "peer_variances": self.get_peer_variances(variance_id),
            "parent_chain": self.get_account_ancestors(acct_id),
            "period_history": self.get_period_history(acct_id, bu_id),
        }

    def get_cascade_chain(self, variance_id: str) -> list[str]:
        """Return IDs of narratives/sections that must regenerate.

        Legacy signature — returns flat list of IDs.
        See get_cascade_chain_typed() for enhanced version with types.
        """
        typed = self.get_cascade_chain_typed(variance_id)
        return [entry["id"] for entry in typed]

    def get_cascade_chain_typed(self, variance_id: str) -> list[dict[str, Any]]:
        """Return ordered cascade chain with types and levels.

        Enhanced version that includes:
        - All transitive parent variances (not just direct parent)
        - Section nodes affected by this variance's pl_category
        - Executive summary node for the period
        - Topological ordering (parents first, then sections, then exec)

        Returns:
            Ordered list of dicts:
            [
                {"id": "v_parent_001", "type": "parent_variance", "level": 1, "account_id": "..."},
                {"id": "section:revenue:2026-06", "type": "section", "level": 2, "section_name": "..."},
                {"id": "exec:2026-06", "type": "executive", "level": 3},
            ]
        """
        if not self._graph.has_node(variance_id):
            return []

        node = self._graph.nodes[variance_id]
        acct_id = node.get("account_id", "")
        period_id = node.get("period_id", "")
        base_id = node.get("base_id", "")
        view_id = node.get("view_id", "")

        chain: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # Level 1: Walk up ALL ancestor accounts (transitive)
        ancestors = self.get_account_ancestors(acct_id)
        for ancestor_id in ancestors:
            for neighbor in self._graph.predecessors(ancestor_id):
                ndata = self._graph.nodes.get(neighbor, {})
                if (
                    ndata.get("node_type") == "variance"
                    and ndata.get("period_id") == period_id
                    and ndata.get("base_id") == base_id
                    and ndata.get("view_id") == view_id
                    and neighbor not in seen_ids
                    and neighbor != variance_id
                ):
                    chain.append({
                        "id": neighbor,
                        "type": "parent_variance",
                        "level": 1,
                        "account_id": ancestor_id,
                    })
                    seen_ids.add(neighbor)

        # Level 2: Find ALL section nodes for this period that contain
        # this variance or any of its parent variances
        section_ids: set[str] = set()
        # Direct section membership
        for neighbor in self._graph.successors(variance_id):
            ndata = self._graph.nodes.get(neighbor, {})
            if ndata.get("node_type") == "section":
                section_ids.add(neighbor)
        # Parent variance section membership
        for entry in chain:
            if entry["type"] == "parent_variance":
                for neighbor in self._graph.successors(entry["id"]):
                    ndata = self._graph.nodes.get(neighbor, {})
                    if ndata.get("node_type") == "section":
                        section_ids.add(neighbor)

        for sid in sorted(section_ids):
            sdata = self._graph.nodes.get(sid, {})
            chain.append({
                "id": sid,
                "type": "section",
                "level": 2,
                "section_name": sdata.get("section_name", ""),
            })
            seen_ids.add(sid)

        # Level 3: Executive summary for this period
        exec_id = f"exec:{period_id}"
        chain.append({
            "id": exec_id,
            "type": "executive",
            "level": 3,
        })

        return chain

    def get_siblings(self, variance_id: str) -> list[dict[str, Any]]:
        """Return sibling variances under the same parent account."""
        if not self._graph.has_node(variance_id):
            return []

        node = self._graph.nodes[variance_id]
        acct_id = node.get("account_id", "")
        period_id = node.get("period_id", "")
        base_id = node.get("base_id", "")
        view_id = node.get("view_id", "")

        # Find parent account
        parent_id = self._graph.nodes.get(acct_id, {}).get("parent_id")
        if not parent_id:
            return []

        # Find sibling accounts (children of parent)
        sibling_accts = [
            n for n in self._graph.successors(parent_id)
            if self._graph.edges.get((parent_id, n), {}).get("edge_type") == "parent_of"
            and n != acct_id
        ]

        # Find variance nodes for sibling accounts in same period
        siblings = []
        for sib_acct in sibling_accts:
            for pred in self._graph.predecessors(sib_acct):
                pdata = self._graph.nodes.get(pred, {})
                if (
                    pdata.get("node_type") == "variance"
                    and pdata.get("period_id") == period_id
                    and pdata.get("base_id") == base_id
                    and pdata.get("view_id") == view_id
                ):
                    siblings.append({
                        "account_id": sib_acct,
                        "account_name": self._graph.nodes.get(sib_acct, {}).get("name", sib_acct),
                        "variance_amount": pdata.get("variance_amount", 0),
                        "variance_pct": pdata.get("variance_pct", 0),
                    })
        return siblings

    def get_correlations(self, variance_id: str) -> list[dict[str, Any]]:
        """Return correlated variances."""
        result = []
        if not self._graph.has_node(variance_id):
            return result

        for neighbor in self._graph.successors(variance_id):
            edge = self._graph.edges.get((variance_id, neighbor), {})
            if edge.get("edge_type") == "correlates_with":
                hyp_node = edge.get("hypothesis_node")
                hypothesis = None
                if hyp_node and self._graph.has_node(hyp_node):
                    hypothesis = self._graph.nodes[hyp_node].get("text")

                result.append({
                    "partner_id": neighbor,
                    "score": edge.get("score", 0),
                    "hypothesis": hypothesis,
                })
        return result

    def get_account_ancestors(self, account_id: str) -> list[str]:
        """Return ancestor account IDs from parent to root."""
        ancestors = []
        current = account_id
        visited = set()
        while current and current not in visited:
            visited.add(current)
            parent = self._graph.nodes.get(current, {}).get("parent_id")
            if parent and self._graph.has_node(parent):
                ancestors.append(parent)
                current = parent
            else:
                break
        return ancestors

    def get_peer_variances(self, variance_id: str) -> list[dict[str, Any]]:
        """Return peer variances: same account, same period, different BU."""
        if not self._graph.has_node(variance_id):
            return []

        node = self._graph.nodes[variance_id]
        acct_id = node.get("account_id", "")
        period_id = node.get("period_id", "")
        bu_id = node.get("bu_id", "")
        base_id = node.get("base_id", "")
        view_id = node.get("view_id", "")

        peers = []
        # Find all variances pointing to the same account node
        if not self._graph.has_node(acct_id):
            return peers

        for pred in self._graph.predecessors(acct_id):
            pdata = self._graph.nodes.get(pred, {})
            if (
                pdata.get("node_type") == "variance"
                and pdata.get("period_id") == period_id
                and pdata.get("bu_id") != bu_id
                and pdata.get("base_id") == base_id
                and pdata.get("view_id") == view_id
            ):
                peers.append({
                    "variance_id": pred,
                    "bu_id": pdata.get("bu_id", ""),
                    "variance_amount": pdata.get("variance_amount", 0),
                    "variance_pct": pdata.get("variance_pct", 0),
                })
        return peers

    def get_period_history(
        self,
        account_id: str,
        bu_id: str,
        n_periods: int = 6,
    ) -> list[dict[str, Any]]:
        """Return variance history for an account+BU over prior periods."""
        # Collect all variance nodes for this account+BU
        if not self._graph.has_node(account_id):
            return []

        history: dict[str, dict] = {}
        for pred in self._graph.predecessors(account_id):
            pdata = self._graph.nodes.get(pred, {})
            if (
                pdata.get("node_type") == "variance"
                and pdata.get("bu_id") == bu_id
            ):
                pid = pdata.get("period_id", "")
                if pid:
                    history[pid] = {
                        "period_id": pid,
                        "variance_amount": pdata.get("variance_amount", 0),
                        "variance_pct": pdata.get("variance_pct", 0),
                    }

        # Sort by period_id and return last N
        sorted_history = sorted(history.values(), key=lambda x: x["period_id"])
        return sorted_history[-n_periods:] if len(sorted_history) > n_periods else sorted_history

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def summary(self) -> dict[str, Any]:
        nodes_by_type: dict[str, int] = defaultdict(int)
        edges_by_type: dict[str, int] = defaultdict(int)

        for _, data in self._graph.nodes(data=True):
            nodes_by_type[data.get("node_type", "unknown")] += 1

        for _, _, data in self._graph.edges(data=True):
            edges_by_type[data.get("edge_type", "unknown")] += 1

        return {
            "node_count": self._graph.number_of_nodes(),
            "edge_count": self._graph.number_of_edges(),
            "nodes_by_type": dict(nodes_by_type),
            "edges_by_type": dict(edges_by_type),
        }

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        if not self._graph.has_node(node_id):
            return None
        return dict(self._graph.nodes[node_id])

    def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        direction: str = "out",
    ) -> list[str]:
        if not self._graph.has_node(node_id):
            return []

        if direction == "out":
            neighbors = list(self._graph.successors(node_id))
        elif direction == "in":
            neighbors = list(self._graph.predecessors(node_id))
        else:  # both
            neighbors = list(set(self._graph.successors(node_id)) | set(self._graph.predecessors(node_id)))

        if edge_type:
            filtered = []
            for n in neighbors:
                if direction in ("out", "both"):
                    e = self._graph.edges.get((node_id, n), {})
                    if e.get("edge_type") == edge_type:
                        filtered.append(n)
                        continue
                if direction in ("in", "both"):
                    e = self._graph.edges.get((n, node_id), {})
                    if e.get("edge_type") == edge_type:
                        filtered.append(n)
            return filtered

        return neighbors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_trend_for_account(self, account_id: str) -> Optional[dict[str, Any]]:
        """Get trend data stored on an account node."""
        if not self._graph.has_node(account_id):
            return None
        return self._graph.nodes[account_id].get("trend")
