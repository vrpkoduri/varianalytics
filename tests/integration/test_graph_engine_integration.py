"""Integration tests for Knowledge Graph + Engine Pipeline.

Validates that the graph integrates correctly with the engine runner,
that context maps from the graph match legacy output, and that
DataService graph caching works.
"""

import sys
import time

import pytest
import pandas as pd

from shared.knowledge.graph_builder import build_variance_graph, build_variance_graph_from_data
from shared.knowledge.networkx_graph import NetworkXGraph
from shared.knowledge.graph_interface import VarianceGraph
from shared.data.service import DataService

# pass5_narrative requires Python 3.11+ (datetime.UTC)
_PY311 = sys.version_info >= (3, 11)
_skip_py311 = pytest.mark.skipif(not _PY311, reason="Requires Python 3.11+ for pass5_narrative imports")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir():
    """Path to test data output directory."""
    return "data/output"


@pytest.fixture
def graph_from_data(data_dir):
    """Graph built from persisted parquet files for the latest period."""
    return build_variance_graph_from_data(data_dir, period_id="2026-06")


@pytest.fixture
def graph_all_periods(data_dir):
    """Graph built from persisted parquet files — all periods."""
    return build_variance_graph_from_data(data_dir)


@pytest.fixture
def engine_context(data_dir):
    """Simulated engine context with real data loaded from parquet.

    Mimics what context looks like after Pass 4 completes.
    """
    from shared.data.loader import DataLoader

    loader = DataLoader(data_dir)

    # Load tables
    dim_account = loader.load_table("dim_account")
    material = loader.load_table("fact_variance_material")
    correlations = loader.load_table("fact_correlations") if loader.table_exists("fact_correlations") else pd.DataFrame()
    netting = loader.load_table("fact_netting_flags") if loader.table_exists("fact_netting_flags") else pd.DataFrame()
    trends = loader.load_table("fact_trend_flags") if loader.table_exists("fact_trend_flags") else pd.DataFrame()
    decomposition = loader.load_table("fact_decomposition") if loader.table_exists("fact_decomposition") else pd.DataFrame()

    # Build acct_meta from dim_account (same as Pass 1)
    acct_meta = {}
    for _, row in dim_account.iterrows():
        acct_id = str(row["account_id"])
        acct_meta[acct_id] = {
            "account_id": acct_id,
            "account_name": str(row.get("account_name", acct_id)),
            "parent_id": row.get("parent_id"),
            "pl_category": str(row.get("pl_category", "")),
            "variance_sign": str(row.get("variance_sign", "natural")),
            "is_calculated": bool(row.get("is_calculated", False)),
        }

    # Filter to a single period for faster testing
    period_id = "2026-06"
    if "period_id" in material.columns:
        material_filtered = material[material["period_id"] == period_id]
    else:
        material_filtered = material

    return {
        "period_id": period_id,
        "data_dir": data_dir,
        "acct_meta": acct_meta,
        "all_variances": material,
        "material_variances": material_filtered,
        "correlations": correlations,
        "netting_flags": netting,
        "trend_flags": trends,
        "decomposition": decomposition,
    }


# ---------------------------------------------------------------------------
# Tests: Graph built from engine context
# ---------------------------------------------------------------------------


class TestGraphFromContext:
    """Test building graph from simulated engine context."""

    def test_graph_built_successfully(self, engine_context):
        """Graph builds from real engine context without errors."""
        graph = build_variance_graph(engine_context)
        assert isinstance(graph, NetworkXGraph)
        assert graph.node_count() > 0

    def test_graph_has_expected_node_types(self, engine_context):
        """Graph contains all expected node types from real data."""
        graph = build_variance_graph(engine_context)
        s = graph.summary()
        assert "account" in s["nodes_by_type"]
        assert "variance" in s["nodes_by_type"]
        # Periods and BUs come from dim tables loaded from disk
        assert "period" in s["nodes_by_type"]
        assert "business_unit" in s["nodes_by_type"]

    def test_graph_has_expected_edge_types(self, engine_context):
        """Graph contains key edge types."""
        graph = build_variance_graph(engine_context)
        s = graph.summary()
        assert "parent_of" in s["edges_by_type"]
        assert "belongs_to" in s["edges_by_type"]

    def test_graph_injected_into_context(self, engine_context):
        """After building, graph is accessible in context dict."""
        engine_context["knowledge_graph"] = build_variance_graph(engine_context)
        assert "knowledge_graph" in engine_context
        assert isinstance(engine_context["knowledge_graph"], VarianceGraph)


# ---------------------------------------------------------------------------
# Tests: Graph from persisted data
# ---------------------------------------------------------------------------


class TestGraphFromData:
    """Test building graph from parquet files."""

    def test_graph_from_data_has_nodes(self, graph_from_data):
        """Graph built from parquet has positive node count."""
        assert graph_from_data.node_count() > 0

    def test_graph_from_data_has_edges(self, graph_from_data):
        """Graph built from parquet has positive edge count."""
        assert graph_from_data.edge_count() > 0

    def test_all_periods_graph_larger(self, graph_from_data, graph_all_periods):
        """All-period graph has more variance nodes than single-period."""
        s_single = graph_from_data.summary()
        s_all = graph_all_periods.summary()
        # All-periods should have >= single period variance count
        assert s_all["nodes_by_type"].get("variance", 0) >= s_single["nodes_by_type"].get("variance", 0)


# ---------------------------------------------------------------------------
# Tests: Context maps compatibility
# ---------------------------------------------------------------------------


class TestContextMapsCompatibility:
    """Test that graph-backed context maps match legacy format."""

    @_skip_py311
    def test_graph_context_maps_have_expected_keys(self, engine_context):
        """Graph-backed context maps return same 5 keys as legacy."""
        graph = build_variance_graph(engine_context)
        engine_context["knowledge_graph"] = graph

        # Import the context map builder
        from services.computation.engine.pass5_narrative import (
            _context_maps_from_graph,
            _build_context_maps_legacy,
        )

        graph_maps = _context_maps_from_graph(graph, engine_context)
        expected_keys = {"correlations", "netting", "trends", "decomposition", "siblings"}
        assert set(graph_maps.keys()) == expected_keys

    @_skip_py311
    def test_legacy_context_maps_still_work(self, engine_context):
        """Legacy context maps build correctly without graph."""
        from services.computation.engine.pass5_narrative import _build_context_maps_legacy

        legacy_maps = _build_context_maps_legacy(engine_context)
        expected_keys = {"correlations", "netting", "trends", "decomposition", "siblings"}
        assert set(legacy_maps.keys()) == expected_keys

    @_skip_py311
    def test_fallback_when_no_graph(self, engine_context):
        """_build_context_maps falls back to legacy when no graph in context."""
        from services.computation.engine.pass5_narrative import _build_context_maps

        # No knowledge_graph in context → should use legacy
        assert "knowledge_graph" not in engine_context
        maps = _build_context_maps(engine_context)
        assert set(maps.keys()) == {"correlations", "netting", "trends", "decomposition", "siblings"}


# ---------------------------------------------------------------------------
# Tests: Performance
# ---------------------------------------------------------------------------


class TestGraphPerformance:
    """Test graph build timing."""

    def test_graph_build_under_10_seconds(self, engine_context):
        """Graph builds from engine context in < 10 seconds (includes disk I/O for dim tables)."""
        start = time.monotonic()
        graph = build_variance_graph(engine_context)
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"Graph build took {elapsed:.2f}s (budget: 10s)"

    def test_graph_from_data_under_60_seconds(self, data_dir):
        """Graph builds from all parquet files in < 60 seconds."""
        start = time.monotonic()
        graph = build_variance_graph_from_data(data_dir)
        elapsed = time.monotonic() - start
        assert elapsed < 60.0, f"Graph build from data took {elapsed:.2f}s (budget: 60s)"


# ---------------------------------------------------------------------------
# Tests: DataService graph cache
# ---------------------------------------------------------------------------


class TestDataServiceGraphCache:
    """Test graph caching in DataService."""

    def test_get_graph_returns_instance(self, data_dir):
        """DataService.get_graph returns a VarianceGraph."""
        ds = DataService(data_dir)
        graph = ds.get_graph("2026-06")
        assert isinstance(graph, VarianceGraph)
        assert graph.node_count() > 0

    def test_graph_cache_returns_same_instance(self, data_dir):
        """Second call returns cached graph (same object)."""
        ds = DataService(data_dir)
        g1 = ds.get_graph("2026-06")
        g2 = ds.get_graph("2026-06")
        assert g1 is g2

    def test_invalidate_graph_cache(self, data_dir):
        """invalidate_graph_cache clears the cache."""
        ds = DataService(data_dir)
        g1 = ds.get_graph("2026-06")
        ds.invalidate_graph_cache()
        g2 = ds.get_graph("2026-06")
        assert g1 is not g2  # New instance after invalidation


# ---------------------------------------------------------------------------
# Tests: Graph summary stats
# ---------------------------------------------------------------------------


class TestGraphSummaryStats:
    """Test graph summary output."""

    def test_summary_returns_expected_keys(self, graph_from_data):
        """summary() returns node_count, edge_count, nodes_by_type, edges_by_type."""
        s = graph_from_data.summary()
        assert "node_count" in s
        assert "edge_count" in s
        assert "nodes_by_type" in s
        assert "edges_by_type" in s
        assert isinstance(s["nodes_by_type"], dict)
        assert isinstance(s["edges_by_type"], dict)

    def test_summary_counts_match(self, graph_from_data):
        """Summary counts match node_count/edge_count methods."""
        s = graph_from_data.summary()
        assert s["node_count"] == graph_from_data.node_count()
        assert s["edge_count"] == graph_from_data.edge_count()
