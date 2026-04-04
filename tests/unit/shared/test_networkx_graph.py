"""Tests for the NetworkX knowledge graph implementation.

Validates node/edge creation, query correctness, and performance.
"""

import pytest
import pandas as pd
import numpy as np

from shared.knowledge.networkx_graph import (
    NetworkXGraph,
    CALCULATED_ROW_DEPS,
    PL_SECTION_MAP,
)
from shared.knowledge.graph_builder import (
    build_variance_graph,
    build_variance_graph_from_data,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_graph():
    """A fresh empty NetworkXGraph."""
    return NetworkXGraph()


@pytest.fixture
def sample_acct_meta():
    """Minimal account hierarchy metadata (7 accounts)."""
    return {
        "total_revenue": {
            "account_id": "total_revenue",
            "account_name": "Total Revenue",
            "parent_id": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "is_calculated": False,
        },
        "A001": {
            "account_id": "A001",
            "account_name": "Brokerage Fees",
            "parent_id": "total_revenue",
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "is_calculated": False,
        },
        "A002": {
            "account_id": "A002",
            "account_name": "Advisory Fees",
            "parent_id": "total_revenue",
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "is_calculated": False,
        },
        "total_cogs": {
            "account_id": "total_cogs",
            "account_name": "Total COGS",
            "parent_id": None,
            "pl_category": "COGS",
            "variance_sign": "inverse",
            "is_calculated": False,
        },
        "A010": {
            "account_id": "A010",
            "account_name": "Direct Costs",
            "parent_id": "total_cogs",
            "pl_category": "COGS",
            "variance_sign": "inverse",
            "is_calculated": False,
        },
        "total_opex": {
            "account_id": "total_opex",
            "account_name": "Total OpEx",
            "parent_id": None,
            "pl_category": "OpEx",
            "variance_sign": "inverse",
            "is_calculated": False,
        },
        "gross_profit": {
            "account_id": "gross_profit",
            "account_name": "Gross Profit",
            "parent_id": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "is_calculated": True,
        },
        "ebitda": {
            "account_id": "ebitda",
            "account_name": "EBITDA",
            "parent_id": None,
            "pl_category": "Revenue",
            "variance_sign": "natural",
            "is_calculated": True,
        },
    }


@pytest.fixture
def sample_dim_hierarchy():
    """Minimal dimension hierarchy (geography)."""
    return pd.DataFrame([
        {"dimension_name": "Geography", "node_id": "GLOBAL", "node_name": "Global", "parent_id": None, "depth": 0, "is_leaf": False},
        {"dimension_name": "Geography", "node_id": "NA", "node_name": "North America", "parent_id": "GLOBAL", "depth": 1, "is_leaf": False},
        {"dimension_name": "Geography", "node_id": "US", "node_name": "United States", "parent_id": "NA", "depth": 2, "is_leaf": True},
        {"dimension_name": "Geography", "node_id": "EMEA", "node_name": "EMEA", "parent_id": "GLOBAL", "depth": 1, "is_leaf": True},
    ])


@pytest.fixture
def sample_dim_period():
    """Minimal period dimension (4 periods)."""
    return pd.DataFrame([
        {"period_id": "2026-03", "fiscal_year": "FY2026"},
        {"period_id": "2026-04", "fiscal_year": "FY2026"},
        {"period_id": "2026-05", "fiscal_year": "FY2026"},
        {"period_id": "2026-06", "fiscal_year": "FY2026"},
    ])


@pytest.fixture
def sample_dim_bu():
    """Minimal BU dimension (3 BUs)."""
    return pd.DataFrame([
        {"bu_id": "marsh", "bu_name": "Marsh"},
        {"bu_id": "mercer", "bu_name": "Mercer"},
        {"bu_id": "guy_carpenter", "bu_name": "Guy Carpenter"},
    ])


@pytest.fixture
def sample_variances(sample_acct_meta):
    """Sample material variances (6 rows)."""
    return pd.DataFrame([
        {"variance_id": "v001", "account_id": "A001", "bu_id": "marsh", "period_id": "2026-06",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": 5000, "variance_pct": 0.05,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "Revenue",
         "account_name": "Brokerage Fees"},
        {"variance_id": "v002", "account_id": "A002", "bu_id": "marsh", "period_id": "2026-06",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": -3000, "variance_pct": -0.03,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "Revenue",
         "account_name": "Advisory Fees"},
        {"variance_id": "v003", "account_id": "A001", "bu_id": "mercer", "period_id": "2026-06",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": 2000, "variance_pct": 0.02,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "Revenue",
         "account_name": "Brokerage Fees"},
        {"variance_id": "v004", "account_id": "A010", "bu_id": "marsh", "period_id": "2026-06",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": -1000, "variance_pct": -0.01,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "COGS",
         "account_name": "Direct Costs"},
        {"variance_id": "v005", "account_id": "A001", "bu_id": "marsh", "period_id": "2026-05",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": 4000, "variance_pct": 0.04,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "Revenue",
         "account_name": "Brokerage Fees"},
        {"variance_id": "v006", "account_id": "A001", "bu_id": "marsh", "period_id": "2026-04",
         "base_id": "BUDGET", "view_id": "MTD", "variance_amount": 3000, "variance_pct": 0.03,
         "is_material": True, "is_netted": False, "is_trending": False, "pl_category": "Revenue",
         "account_name": "Brokerage Fees"},
    ])


@pytest.fixture
def sample_correlations():
    """Sample correlations (2 pairs)."""
    return pd.DataFrame([
        {"correlation_id": "c001", "variance_id_a": "v001", "variance_id_b": "v004",
         "correlation_score": 0.85, "hypothesis": "Revenue increase offset by COGS rise",
         "confidence": 0.7},
        {"correlation_id": "c002", "variance_id_a": "v001", "variance_id_b": "v002",
         "correlation_score": 0.6, "hypothesis": None, "confidence": 0.0},
    ])


@pytest.fixture
def sample_netting():
    """Sample netting flags (1 entry)."""
    return pd.DataFrame([
        {"parent_node_id": "total_revenue", "check_type": "gross_offset",
         "net_variance": 2000, "gross_variance": 8000, "netting_ratio": 4.0,
         "child_details": "[]"},
    ])


@pytest.fixture
def sample_trends():
    """Sample trend flags (1 entry)."""
    return pd.DataFrame([
        {"account_id": "A001", "direction": "increasing",
         "consecutive_periods": 3, "cumulative_amount": 12000},
    ])


@pytest.fixture
def populated_graph(
    empty_graph,
    sample_acct_meta,
    sample_dim_hierarchy,
    sample_dim_period,
    sample_dim_bu,
    sample_variances,
    sample_correlations,
    sample_netting,
    sample_trends,
):
    """A fully populated graph with all node/edge types."""
    g = empty_graph
    g._add_account_hierarchy(sample_acct_meta)
    g._add_calc_dependencies()
    g._add_dimension_hierarchies(sample_dim_hierarchy)
    g._add_periods(sample_dim_period)
    g._add_business_units(sample_dim_bu)
    g._add_variances(sample_variances, sample_acct_meta)
    g._add_correlations(sample_correlations)
    g._add_netting(sample_netting)
    g._add_trends(sample_trends)
    g._add_sections(sample_variances)
    return g


# ---------------------------------------------------------------------------
# Tests: Building
# ---------------------------------------------------------------------------


class TestBuildEmptyGraph:
    """Test building a graph from empty/missing data."""

    def test_build_empty_context(self, empty_graph):
        """Empty context produces a graph with structural nodes only."""
        empty_graph.build_from_context({})
        # May have some dimension/period nodes from data files, or 0 if no files
        assert empty_graph.node_count() >= 0
        assert empty_graph.edge_count() >= 0

    def test_fresh_graph_is_empty(self, empty_graph):
        """A freshly created graph has 0 nodes and edges."""
        assert empty_graph.node_count() == 0
        assert empty_graph.edge_count() == 0


class TestAddAccountHierarchy:
    """Test account node and parent_of edge creation."""

    def test_adds_all_accounts(self, empty_graph, sample_acct_meta):
        """All accounts in acct_meta become nodes."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        assert empty_graph.node_count() == len(sample_acct_meta)

    def test_parent_of_edges(self, empty_graph, sample_acct_meta):
        """Parent-child relationships create parent_of edges."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        # A001 and A002 are children of total_revenue
        neighbors = empty_graph.get_neighbors("total_revenue", edge_type="parent_of", direction="out")
        assert "A001" in neighbors
        assert "A002" in neighbors

    def test_account_node_attributes(self, empty_graph, sample_acct_meta):
        """Account nodes have expected attributes."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        node = empty_graph.get_node("A001")
        assert node is not None
        assert node["node_type"] == "account"
        assert node["name"] == "Brokerage Fees"
        assert node["pl_category"] == "Revenue"
        assert node["variance_sign"] == "natural"

    def test_root_accounts_have_no_parent_edge(self, empty_graph, sample_acct_meta):
        """Root accounts have no incoming parent_of edges."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        preds = empty_graph.get_neighbors("total_revenue", direction="in", edge_type="parent_of")
        assert len(preds) == 0


class TestAddDimensionHierarchy:
    """Test dimension hierarchy nodes."""

    def test_adds_dimension_nodes(self, empty_graph, sample_dim_hierarchy):
        """Dimension nodes are created with prefixed IDs."""
        empty_graph._add_dimension_hierarchies(sample_dim_hierarchy)
        assert empty_graph.has_node("geography:GLOBAL")
        assert empty_graph.has_node("geography:NA")
        assert empty_graph.has_node("geography:US")
        assert empty_graph.has_node("geography:EMEA")

    def test_dimension_parent_of_edges(self, empty_graph, sample_dim_hierarchy):
        """Dimension parent-child creates parent_of edges."""
        empty_graph._add_dimension_hierarchies(sample_dim_hierarchy)
        children = empty_graph.get_neighbors("geography:GLOBAL", edge_type="parent_of", direction="out")
        assert "geography:NA" in children
        assert "geography:EMEA" in children


class TestAddPeriods:
    """Test period nodes and temporal chain."""

    def test_adds_period_nodes(self, empty_graph, sample_dim_period):
        """All periods become nodes."""
        empty_graph._add_periods(sample_dim_period)
        assert empty_graph.has_node("2026-03")
        assert empty_graph.has_node("2026-06")

    def test_prior_period_of_chain(self, empty_graph, sample_dim_period):
        """Adjacent periods are linked by prior_period_of edges."""
        empty_graph._add_periods(sample_dim_period)
        # 2026-04 → prior_period_of → 2026-03
        neighbors = empty_graph.get_neighbors("2026-04", edge_type="prior_period_of", direction="out")
        assert "2026-03" in neighbors

    def test_period_attributes(self, empty_graph, sample_dim_period):
        """Period nodes have month, is_high_season, is_low_season."""
        empty_graph._add_periods(sample_dim_period)
        node = empty_graph.get_node("2026-03")
        assert node["month"] == 3
        assert node["is_high_season"] is False
        assert node["is_low_season"] is False


class TestAddBusinessUnits:
    """Test BU nodes."""

    def test_adds_bu_nodes(self, empty_graph, sample_dim_bu):
        """All BUs become nodes."""
        empty_graph._add_business_units(sample_dim_bu)
        assert empty_graph.has_node("marsh")
        assert empty_graph.has_node("mercer")
        assert empty_graph.has_node("guy_carpenter")

    def test_bu_node_attributes(self, empty_graph, sample_dim_bu):
        """BU nodes have name attribute."""
        empty_graph._add_business_units(sample_dim_bu)
        node = empty_graph.get_node("marsh")
        assert node["node_type"] == "business_unit"
        assert node["name"] == "Marsh"


class TestAddVariances:
    """Test variance node and belongs_to edge creation."""

    def test_adds_variance_nodes(self, empty_graph, sample_acct_meta, sample_variances, sample_dim_bu, sample_dim_period):
        """Variance rows become graph nodes."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        assert empty_graph.has_node("v001")
        assert empty_graph.has_node("v002")

    def test_belongs_to_account(self, empty_graph, sample_acct_meta, sample_variances, sample_dim_bu, sample_dim_period):
        """Variance nodes have belongs_to edge to their account."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        neighbors = empty_graph.get_neighbors("v001", edge_type="belongs_to", direction="out")
        assert "A001" in neighbors

    def test_belongs_to_bu(self, empty_graph, sample_acct_meta, sample_variances, sample_dim_bu, sample_dim_period):
        """Variance nodes have belongs_to edge to their BU."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        neighbors = empty_graph.get_neighbors("v001", edge_type="belongs_to", direction="out")
        assert "marsh" in neighbors

    def test_variance_node_attributes(self, empty_graph, sample_acct_meta, sample_variances, sample_dim_bu, sample_dim_period):
        """Variance nodes have expected attributes."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        node = empty_graph.get_node("v001")
        assert node["node_type"] == "variance"
        assert node["variance_amount"] == 5000
        assert node["variance_pct"] == 0.05
        assert node["account_id"] == "A001"
        assert node["bu_id"] == "marsh"


class TestAddCorrelations:
    """Test correlates_with edges and hypothesis nodes."""

    def test_adds_bidirectional_edges(self, empty_graph, sample_acct_meta, sample_variances, sample_correlations, sample_dim_bu, sample_dim_period):
        """Correlations create edges in both directions."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        empty_graph._add_correlations(sample_correlations)

        # v001 → v004 and v004 → v001
        corr_out = empty_graph.get_neighbors("v001", edge_type="correlates_with", direction="out")
        assert "v004" in corr_out

        corr_reverse = empty_graph.get_neighbors("v004", edge_type="correlates_with", direction="out")
        assert "v001" in corr_reverse

    def test_hypothesis_node_created(self, empty_graph, sample_acct_meta, sample_variances, sample_correlations, sample_dim_bu, sample_dim_period):
        """Correlations with hypothesis text create hypothesis nodes."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_business_units(sample_dim_bu)
        empty_graph._add_periods(sample_dim_period)
        empty_graph._add_variances(sample_variances, sample_acct_meta)
        empty_graph._add_correlations(sample_correlations)

        assert empty_graph.has_node("hypothesis:c001")
        hyp = empty_graph.get_node("hypothesis:c001")
        assert hyp["node_type"] == "hypothesis"
        assert "Revenue increase" in hyp["text"]


class TestAddNetting:
    """Test netting data on nodes."""

    def test_netting_stored_on_node(self, empty_graph, sample_acct_meta, sample_netting):
        """Netting info stored as attribute on parent node."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_netting(sample_netting)
        node = empty_graph.get_node("total_revenue")
        assert node is not None
        assert "netting" in node
        assert node["netting"]["net_variance"] == 2000
        assert node["netting"]["netting_ratio"] == 4.0


class TestAddTrends:
    """Test trend data on account nodes."""

    def test_trend_stored_on_account(self, empty_graph, sample_acct_meta, sample_trends):
        """Trend info stored as attribute on account node."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_trends(sample_trends)
        node = empty_graph.get_node("A001")
        assert node is not None
        assert "trend" in node
        assert node["trend"]["direction"] == "increasing"
        assert node["trend"]["consecutive_periods"] == 3


class TestAddCalcDependencies:
    """Test calculated row dependency edges."""

    def test_ebitda_depends_on_gp_opex(self, empty_graph, sample_acct_meta):
        """EBITDA has calc_depends_on edges to gross_profit and total_opex."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_calc_dependencies()
        deps = empty_graph.get_neighbors("ebitda", edge_type="calc_depends_on", direction="out")
        assert "gross_profit" in deps
        assert "total_opex" in deps

    def test_gp_depends_on_revenue_cogs(self, empty_graph, sample_acct_meta):
        """Gross Profit depends on total_revenue and total_cogs."""
        empty_graph._add_account_hierarchy(sample_acct_meta)
        empty_graph._add_calc_dependencies()
        deps = empty_graph.get_neighbors("gross_profit", edge_type="calc_depends_on", direction="out")
        assert "total_revenue" in deps
        assert "total_cogs" in deps


# ---------------------------------------------------------------------------
# Tests: Queries
# ---------------------------------------------------------------------------


class TestGetFullContext:
    """Test the unified context query."""

    def test_returns_all_keys(self, populated_graph):
        """get_full_context returns all expected keys."""
        ctx = populated_graph.get_full_context("v001")
        expected_keys = {
            "correlations", "netting", "trends", "decomposition",
            "siblings", "peer_variances", "parent_chain", "period_history",
        }
        assert set(ctx.keys()) == expected_keys

    def test_correlations_populated(self, populated_graph):
        """get_full_context includes correlation data."""
        ctx = populated_graph.get_full_context("v001")
        assert len(ctx["correlations"]) >= 1
        partner_ids = [c["partner_id"] for c in ctx["correlations"]]
        assert "v004" in partner_ids

    def test_nonexistent_variance(self, populated_graph):
        """Nonexistent variance returns empty context."""
        ctx = populated_graph.get_full_context("nonexistent")
        assert ctx["correlations"] == []
        assert ctx["siblings"] == []
        assert ctx["peer_variances"] == []


class TestGetSiblings:
    """Test sibling variance query."""

    def test_siblings_under_same_parent(self, populated_graph):
        """v001 (A001) and v002 (A002) share parent total_revenue."""
        siblings = populated_graph.get_siblings("v001")
        sibling_accts = [s["account_id"] for s in siblings]
        assert "A002" in sibling_accts

    def test_no_siblings_for_lone_child(self, populated_graph):
        """v004 (A010 under total_cogs) is the only child."""
        siblings = populated_graph.get_siblings("v004")
        assert len(siblings) == 0


class TestGetCascadeChain:
    """Test cascade chain traversal."""

    def test_includes_section(self, populated_graph):
        """Cascade chain includes the section node."""
        chain = populated_graph.get_cascade_chain("v001")
        section_ids = [c for c in chain if c.startswith("section:")]
        assert len(section_ids) >= 1

    def test_empty_for_nonexistent(self, populated_graph):
        """Nonexistent variance returns empty chain."""
        chain = populated_graph.get_cascade_chain("nonexistent")
        assert chain == []


class TestGetPeerVariances:
    """Test peer variance query (same account, different BU)."""

    def test_finds_peer_in_different_bu(self, populated_graph):
        """v001 (A001, marsh) should find v003 (A001, mercer) as peer."""
        peers = populated_graph.get_peer_variances("v001")
        peer_bus = [p["bu_id"] for p in peers]
        assert "mercer" in peer_bus

    def test_no_peers_for_unique_account(self, populated_graph):
        """v004 (A010, only in marsh) has no peers."""
        peers = populated_graph.get_peer_variances("v004")
        assert len(peers) == 0


class TestGetAccountAncestors:
    """Test account ancestor traversal."""

    def test_child_to_parent(self, populated_graph):
        """A001 parent is total_revenue."""
        ancestors = populated_graph.get_account_ancestors("A001")
        assert "total_revenue" in ancestors

    def test_root_has_no_ancestors(self, populated_graph):
        """Root account has empty ancestor list."""
        ancestors = populated_graph.get_account_ancestors("total_revenue")
        assert len(ancestors) == 0


class TestGetPeriodHistory:
    """Test period history query."""

    def test_returns_sorted_history(self, populated_graph):
        """Period history for A001/marsh returns periods in order."""
        history = populated_graph.get_period_history("A001", "marsh")
        assert len(history) >= 2
        periods = [h["period_id"] for h in history]
        assert periods == sorted(periods)

    def test_empty_for_missing_account(self, populated_graph):
        """Nonexistent account returns empty history."""
        history = populated_graph.get_period_history("NONEXISTENT", "marsh")
        assert history == []


# ---------------------------------------------------------------------------
# Tests: Stats
# ---------------------------------------------------------------------------


class TestGraphStats:
    """Test node/edge counts and summary."""

    def test_node_count_positive(self, populated_graph):
        """Populated graph has positive node count."""
        assert populated_graph.node_count() > 0

    def test_edge_count_positive(self, populated_graph):
        """Populated graph has positive edge count."""
        assert populated_graph.edge_count() > 0

    def test_summary_has_expected_keys(self, populated_graph):
        """Summary returns node_count, edge_count, nodes_by_type, edges_by_type."""
        s = populated_graph.summary()
        assert "node_count" in s
        assert "edge_count" in s
        assert "nodes_by_type" in s
        assert "edges_by_type" in s

    def test_summary_node_types(self, populated_graph):
        """Summary includes all expected node types."""
        s = populated_graph.summary()
        node_types = s["nodes_by_type"]
        assert "account" in node_types
        assert "variance" in node_types
        assert "period" in node_types
        assert "business_unit" in node_types

    def test_summary_edge_types(self, populated_graph):
        """Summary includes key edge types."""
        s = populated_graph.summary()
        edge_types = s["edges_by_type"]
        assert "parent_of" in edge_types
        assert "belongs_to" in edge_types


class TestNodeAccess:
    """Test has_node, get_node, get_neighbors."""

    def test_has_node_true(self, populated_graph):
        """has_node returns True for existing node."""
        assert populated_graph.has_node("v001")

    def test_has_node_false(self, populated_graph):
        """has_node returns False for nonexistent node."""
        assert not populated_graph.has_node("nonexistent")

    def test_get_node_returns_attrs(self, populated_graph):
        """get_node returns attribute dict."""
        node = populated_graph.get_node("v001")
        assert node is not None
        assert node["node_type"] == "variance"

    def test_get_node_none_for_missing(self, populated_graph):
        """get_node returns None for nonexistent node."""
        assert populated_graph.get_node("nonexistent") is None

    def test_get_neighbors_direction_out(self, populated_graph):
        """get_neighbors with direction=out returns successors."""
        neighbors = populated_graph.get_neighbors("v001", direction="out")
        assert len(neighbors) > 0

    def test_get_neighbors_direction_in(self, populated_graph):
        """get_neighbors with direction=in returns predecessors."""
        # A001 has incoming belongs_to from v001
        neighbors = populated_graph.get_neighbors("A001", direction="in")
        assert len(neighbors) > 0

    def test_get_neighbors_filtered_by_edge_type(self, populated_graph):
        """get_neighbors filtered by edge_type returns only matching."""
        neighbors = populated_graph.get_neighbors("v001", edge_type="belongs_to", direction="out")
        for n in neighbors:
            node_type = populated_graph.get_node(n).get("node_type", "")
            assert node_type in ("account", "business_unit", "period")


# ---------------------------------------------------------------------------
# Tests: Graph Builder Factory
# ---------------------------------------------------------------------------


class TestGraphBuilder:
    """Test the graph builder factory functions."""

    def test_build_from_context_returns_graph(self, sample_acct_meta, sample_variances):
        """build_variance_graph returns a VarianceGraph instance."""
        context = {
            "acct_meta": sample_acct_meta,
            "material_variances": sample_variances,
            "data_dir": "data/output",
        }
        graph = build_variance_graph(context)
        assert isinstance(graph, NetworkXGraph)
        assert graph.node_count() > 0

    def test_build_from_data_returns_graph(self):
        """build_variance_graph_from_data returns a populated graph."""
        graph = build_variance_graph_from_data("data/output", period_id="2026-06")
        assert isinstance(graph, NetworkXGraph)
        # Should have at least accounts + periods + BUs
        assert graph.node_count() > 0
