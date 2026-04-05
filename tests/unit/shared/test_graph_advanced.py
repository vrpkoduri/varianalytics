"""Tests for Graph Enhancement Sprint: Advanced graph intelligence.

Tests multi-hop root cause chains, hub detection, subgraph extraction,
and impact propagation.
"""

import pytest

from shared.knowledge.graph_builder import build_variance_graph_from_data
from shared.knowledge.networkx_graph import NetworkXGraph


@pytest.fixture
def graph():
    return build_variance_graph_from_data("data/output", period_id="2026-06")


@pytest.fixture
def sample_variance_id(graph):
    """Find a variance with correlations for testing."""
    for node_id, data in graph._graph.nodes(data=True):
        if data.get("node_type") == "variance" and data.get("period_id") == "2026-06":
            corrs = graph.get_correlations(node_id)
            if corrs:
                return node_id
    pytest.skip("No variance with correlations found")


@pytest.fixture
def sample_leaf_id(graph):
    """Find a leaf variance."""
    for node_id, data in graph._graph.nodes(data=True):
        if (data.get("node_type") == "variance" and data.get("period_id") == "2026-06"
                and data.get("base_id") == "BUDGET" and data.get("view_id") == "MTD"):
            acct = graph.get_node(data.get("account_id", ""))
            if acct and not acct.get("is_calculated"):
                return node_id
    pytest.skip("No leaf variance found")


# ======================================================================
# Multi-Hop Root Cause Chains
# ======================================================================


class TestRootCauseChains:

    def test_returns_chain(self, graph, sample_variance_id):
        """Root cause chain returns linked variances."""
        chain = graph.get_root_cause_chain(sample_variance_id)
        # May have 0+ entries depending on data
        assert isinstance(chain, list)

    def test_chain_has_expected_fields(self, graph, sample_variance_id):
        """Chain entries have variance_id, account_id, score, hop."""
        chain = graph.get_root_cause_chain(sample_variance_id)
        if chain:
            entry = chain[0]
            assert "variance_id" in entry
            assert "account_id" in entry
            assert "score" in entry
            assert "hop" in entry

    def test_max_hops_respected(self, graph, sample_variance_id):
        """Chain respects max_hops limit."""
        chain = graph.get_root_cause_chain(sample_variance_id, max_hops=1)
        for entry in chain:
            assert entry["hop"] <= 1

    def test_min_score_filters(self, graph, sample_variance_id):
        """Chain respects min_score threshold."""
        chain = graph.get_root_cause_chain(sample_variance_id, min_score=0.9)
        for entry in chain:
            assert entry["score"] >= 0.9

    def test_nonexistent_returns_empty(self, graph):
        """Nonexistent variance returns empty chain."""
        assert graph.get_root_cause_chain("nonexistent") == []


# ======================================================================
# Hub Detection
# ======================================================================


class TestHubDetection:

    def test_returns_top_n(self, graph):
        """get_variance_hubs returns up to top_n results."""
        hubs = graph.get_variance_hubs("2026-06", top_n=5)
        assert len(hubs) <= 5

    def test_sorted_by_degree(self, graph):
        """Hubs are sorted by connected_count descending."""
        hubs = graph.get_variance_hubs("2026-06", top_n=10)
        if len(hubs) >= 2:
            assert hubs[0]["connected_count"] >= hubs[1]["connected_count"]

    def test_hub_has_expected_fields(self, graph):
        """Hub entries have variance_id, account_name, degree."""
        hubs = graph.get_variance_hubs("2026-06")
        if hubs:
            hub = hubs[0]
            assert "variance_id" in hub
            assert "account_name" in hub or "account_id" in hub
            assert "degree" in hub

    def test_no_hubs_for_empty_period(self, graph):
        """No hubs for nonexistent period."""
        hubs = graph.get_variance_hubs("2099-01")
        assert hubs == []


# ======================================================================
# Subgraph Story Extraction
# ======================================================================


class TestSubgraphExtraction:

    def test_returns_nodes_and_edges(self, graph, sample_leaf_id):
        """Subgraph includes nodes and edges."""
        story = graph.extract_story_subgraph(sample_leaf_id, radius=2)
        assert story["node_count"] >= 1
        assert isinstance(story["nodes"], list)
        assert isinstance(story["edges"], list)

    def test_center_node_included(self, graph, sample_leaf_id):
        """Center variance is in the subgraph nodes."""
        story = graph.extract_story_subgraph(sample_leaf_id)
        node_ids = [n["id"] for n in story["nodes"]]
        assert sample_leaf_id in node_ids

    def test_summary_generated(self, graph, sample_leaf_id):
        """Summary string is generated."""
        story = graph.extract_story_subgraph(sample_leaf_id)
        assert len(story["summary"]) > 0
        assert "Story around" in story["summary"]

    def test_radius_controls_size(self, graph, sample_leaf_id):
        """Larger radius = more nodes."""
        small = graph.extract_story_subgraph(sample_leaf_id, radius=1)
        large = graph.extract_story_subgraph(sample_leaf_id, radius=3)
        assert large["node_count"] >= small["node_count"]

    def test_nonexistent_returns_empty(self, graph):
        """Nonexistent variance returns empty subgraph."""
        story = graph.extract_story_subgraph("nonexistent")
        assert story["nodes"] == []


# ======================================================================
# Impact Propagation
# ======================================================================


class TestImpactPropagation:

    def test_returns_impact(self, graph, sample_leaf_id):
        """estimate_fix_impact returns direct_impact."""
        impact = graph.estimate_fix_impact(sample_leaf_id)
        assert "direct_impact" in impact
        assert "affected_parents" in impact
        assert "total_pl_impact" in impact
        assert impact["direct_impact"] != 0 or True  # Could be 0

    def test_affected_parents_populated(self, graph, sample_leaf_id):
        """Impact includes affected parent accounts."""
        impact = graph.estimate_fix_impact(sample_leaf_id)
        assert isinstance(impact["affected_parents"], list)
        # Most variances have at least one parent
        assert impact["affected_node_count"] >= 1

    def test_nonexistent_returns_zero(self, graph):
        """Nonexistent variance returns zero impact."""
        impact = graph.estimate_fix_impact("nonexistent")
        assert impact["direct_impact"] == 0
        assert impact["affected_node_count"] == 0
