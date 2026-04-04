"""Tests for the abstract VarianceGraph interface.

Validates that the ABC cannot be instantiated directly, and that
the interface contract is correct.
"""

import pytest

from shared.knowledge.graph_interface import VarianceGraph


class TestVarianceGraphABC:
    """Tests for the abstract base class."""

    def test_cannot_instantiate_directly(self):
        """VarianceGraph is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            VarianceGraph()  # type: ignore[abstract]

    def test_has_build_methods(self):
        """Interface declares build_from_context and build_from_data."""
        assert hasattr(VarianceGraph, "build_from_context")
        assert hasattr(VarianceGraph, "build_from_data")

    def test_has_query_methods(self):
        """Interface declares all core query methods."""
        query_methods = [
            "get_full_context",
            "get_cascade_chain",
            "get_siblings",
            "get_correlations",
            "get_account_ancestors",
            "get_peer_variances",
            "get_period_history",
        ]
        for method_name in query_methods:
            assert hasattr(VarianceGraph, method_name), f"Missing: {method_name}"

    def test_has_stat_methods(self):
        """Interface declares node_count, edge_count, summary."""
        for method_name in ["node_count", "edge_count", "summary"]:
            assert hasattr(VarianceGraph, method_name), f"Missing: {method_name}"

    def test_has_node_access_methods(self):
        """Interface declares has_node, get_node, get_neighbors."""
        for method_name in ["has_node", "get_node", "get_neighbors"]:
            assert hasattr(VarianceGraph, method_name), f"Missing: {method_name}"
