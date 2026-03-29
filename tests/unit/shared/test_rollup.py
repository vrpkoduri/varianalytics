"""Unit tests for shared.hierarchy.rollup — rollup paths, is_descendant, children map."""

import pytest

from shared.hierarchy.rollup import build_rollup_paths, is_descendant
from shared.hierarchy.tree import HierarchyNode, build_tree_from_dict


@pytest.mark.unit
class TestBuildRollupPaths:
    """Tests for materialized rollup path generation."""

    def test_all_nodes_get_paths(self, sample_geo_tree: HierarchyNode) -> None:
        paths = build_rollup_paths(sample_geo_tree)
        assert len(paths) == 8

    def test_root_path(self, sample_geo_tree: HierarchyNode) -> None:
        paths = build_rollup_paths(sample_geo_tree)
        assert paths["geo_global"] == "geo_global"

    def test_leaf_path(self, sample_geo_tree: HierarchyNode) -> None:
        paths = build_rollup_paths(sample_geo_tree)
        assert paths["geo_us_ne"] == "geo_global/geo_americas/geo_us/geo_us_ne"

    def test_intermediate_path(self, sample_geo_tree: HierarchyNode) -> None:
        paths = build_rollup_paths(sample_geo_tree)
        assert paths["geo_americas"] == "geo_global/geo_americas"


@pytest.mark.unit
class TestIsDescendant:
    """Tests for ancestry checking via materialized paths."""

    def test_leaf_is_descendant_of_root(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_global", "geo_us_ne", sample_geo_tree) is True

    def test_leaf_is_descendant_of_parent(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_us", "geo_us_ne", sample_geo_tree) is True

    def test_root_is_not_descendant_of_leaf(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_us_ne", "geo_global", sample_geo_tree) is False

    def test_node_is_not_its_own_descendant(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_us", "geo_us", sample_geo_tree) is False

    def test_sibling_is_not_descendant(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_americas", "geo_uk_ireland", sample_geo_tree) is False

    def test_cross_branch_not_descendant(self, sample_geo_tree: HierarchyNode) -> None:
        assert is_descendant("geo_emea", "geo_us_ne", sample_geo_tree) is False

    def test_missing_node(self, sample_geo_tree: HierarchyNode) -> None:
        """Missing node returns False (empty path won't match)."""
        assert is_descendant("geo_global", "nonexistent", sample_geo_tree) is False


@pytest.mark.unit
class TestRaggedHierarchy:
    """Tests for unbalanced/ragged hierarchy trees."""

    @pytest.fixture
    def ragged_tree_data(self) -> dict:
        """Tree with varying depths: 1 level on one branch, 4 on another."""
        return {
            "node_id": "root",
            "node_name": "Root",
            "children": [
                {"node_id": "shallow", "node_name": "Shallow Leaf", "children": []},
                {
                    "node_id": "deep1",
                    "node_name": "Deep 1",
                    "children": [
                        {
                            "node_id": "deep2",
                            "node_name": "Deep 2",
                            "children": [
                                {
                                    "node_id": "deep3",
                                    "node_name": "Deep 3",
                                    "children": [
                                        {"node_id": "deep4", "node_name": "Deep Leaf", "children": []},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            ],
        }

    def test_ragged_tree_leaf_nodes(self, ragged_tree_data: dict) -> None:
        from shared.hierarchy.tree import flatten_tree, get_leaf_nodes

        root = build_tree_from_dict(ragged_tree_data)
        leaves = get_leaf_nodes(root)
        leaf_ids = {n.node_id for n in leaves}
        assert leaf_ids == {"shallow", "deep4"}

    def test_ragged_tree_depths(self, ragged_tree_data: dict) -> None:
        from shared.hierarchy.tree import flatten_tree

        root = build_tree_from_dict(ragged_tree_data)
        flat = flatten_tree(root)
        depth_map = {n.node_id: n.depth for n in flat}
        assert depth_map["shallow"] == 1
        assert depth_map["deep4"] == 4

    def test_ragged_tree_rollup_paths(self, ragged_tree_data: dict) -> None:
        root = build_tree_from_dict(ragged_tree_data)
        paths = build_rollup_paths(root)
        assert paths["deep4"] == "root/deep1/deep2/deep3/deep4"
        assert paths["shallow"] == "root/shallow"

    def test_is_descendant_across_depths(self, ragged_tree_data: dict) -> None:
        root = build_tree_from_dict(ragged_tree_data)
        assert is_descendant("root", "deep4", root) is True
        assert is_descendant("root", "shallow", root) is True
        assert is_descendant("shallow", "deep4", root) is False


@pytest.mark.unit
class TestEmptyAndSingleNodeHierarchy:
    """Tests for edge case hierarchies."""

    def test_single_node_tree(self) -> None:
        root = build_tree_from_dict({"node_id": "only", "node_name": "Only Node", "children": []})
        paths = build_rollup_paths(root)
        assert paths == {"only": "only"}

    def test_single_node_is_not_own_descendant(self) -> None:
        root = build_tree_from_dict({"node_id": "only", "node_name": "Only Node", "children": []})
        assert is_descendant("only", "only", root) is False
