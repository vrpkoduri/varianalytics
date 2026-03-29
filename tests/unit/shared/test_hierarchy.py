"""Unit tests for shared.hierarchy — tree traversal, rollup paths, leaf nodes."""

import pytest

from shared.hierarchy.tree import (
    HierarchyNode,
    build_tree_from_dict,
    flatten_tree,
    get_ancestors,
    get_leaf_nodes,
    get_node_by_id,
)
from shared.hierarchy.rollup import build_rollup_paths, depth_sorted_nodes, get_children_map


@pytest.mark.unit
class TestBuildTreeFromDict:
    """Tests for building HierarchyNode trees from nested dicts."""

    def test_builds_root_node(self, sample_geo_tree_data: dict) -> None:
        root = build_tree_from_dict(sample_geo_tree_data)
        assert root.node_id == "geo_global"
        assert root.node_name == "Global"
        assert root.parent_id is None
        assert root.depth == 0

    def test_builds_children(self, sample_geo_tree: HierarchyNode) -> None:
        assert len(sample_geo_tree.children) == 2
        assert sample_geo_tree.children[0].node_id == "geo_americas"
        assert sample_geo_tree.children[1].node_id == "geo_emea"

    def test_sets_parent_id(self, sample_geo_tree: HierarchyNode) -> None:
        americas = sample_geo_tree.children[0]
        assert americas.parent_id == "geo_global"
        us = americas.children[0]
        assert us.parent_id == "geo_americas"

    def test_sets_depth(self, sample_geo_tree: HierarchyNode) -> None:
        assert sample_geo_tree.depth == 0
        americas = sample_geo_tree.children[0]
        assert americas.depth == 1
        us = americas.children[0]
        assert us.depth == 2
        us_ne = us.children[0]
        assert us_ne.depth == 3

    def test_identifies_leaf_nodes(self, sample_geo_tree: HierarchyNode) -> None:
        assert not sample_geo_tree.is_leaf
        us_ne = sample_geo_tree.children[0].children[0].children[0]
        assert us_ne.is_leaf

    def test_preserves_metadata(self, sample_account_tree: HierarchyNode) -> None:
        revenue = sample_account_tree.children[0]
        assert revenue.metadata.get("pl_category") == "Revenue"
        assert revenue.metadata.get("variance_sign") == "natural"


@pytest.mark.unit
class TestFlattenTree:
    """Tests for flattening trees with materialized rollup paths."""

    def test_flattens_all_nodes(self, sample_geo_tree: HierarchyNode) -> None:
        flat = flatten_tree(sample_geo_tree)
        assert len(flat) == 8  # global, americas, us, us_ne, us_se, canada, emea, uk_ireland

    def test_rollup_paths(self, sample_geo_tree: HierarchyNode) -> None:
        flat = flatten_tree(sample_geo_tree)
        paths = {n.node_id: n.rollup_path for n in flat}
        assert paths["geo_global"] == "geo_global"
        assert paths["geo_americas"] == "geo_global/geo_americas"
        assert paths["geo_us_ne"] == "geo_global/geo_americas/geo_us/geo_us_ne"


@pytest.mark.unit
class TestGetLeafNodes:
    """Tests for extracting leaf nodes."""

    def test_returns_only_leaves(self, sample_geo_tree: HierarchyNode) -> None:
        leaves = get_leaf_nodes(sample_geo_tree)
        leaf_ids = {n.node_id for n in leaves}
        assert leaf_ids == {"geo_us_ne", "geo_us_se", "geo_canada", "geo_uk_ireland"}

    def test_single_node_is_leaf(self) -> None:
        node = HierarchyNode(node_id="single", node_name="Single", is_leaf=True)
        assert get_leaf_nodes(node) == [node]


@pytest.mark.unit
class TestGetNodeById:
    """Tests for finding nodes by ID."""

    def test_finds_root(self, sample_geo_tree: HierarchyNode) -> None:
        found = get_node_by_id(sample_geo_tree, "geo_global")
        assert found is not None
        assert found.node_id == "geo_global"

    def test_finds_deep_node(self, sample_geo_tree: HierarchyNode) -> None:
        found = get_node_by_id(sample_geo_tree, "geo_us_ne")
        assert found is not None
        assert found.node_name == "US Northeast"

    def test_returns_none_for_missing(self, sample_geo_tree: HierarchyNode) -> None:
        assert get_node_by_id(sample_geo_tree, "nonexistent") is None


@pytest.mark.unit
class TestDepthSortedNodes:
    """Tests for depth-sorted node ordering."""

    def test_bottom_up_order(self, sample_geo_tree: HierarchyNode) -> None:
        sorted_nodes = depth_sorted_nodes(sample_geo_tree, reverse=True)
        depths = [n.depth for n in sorted_nodes]
        assert depths == sorted(depths, reverse=True)

    def test_top_down_order(self, sample_geo_tree: HierarchyNode) -> None:
        sorted_nodes = depth_sorted_nodes(sample_geo_tree, reverse=False)
        depths = [n.depth for n in sorted_nodes]
        assert depths == sorted(depths)


@pytest.mark.unit
class TestGetChildrenMap:
    """Tests for parent -> children mapping."""

    def test_maps_parent_to_children(self, sample_geo_tree: HierarchyNode) -> None:
        children_map = get_children_map(sample_geo_tree)
        assert set(children_map["geo_global"]) == {"geo_americas", "geo_emea"}
        assert set(children_map["geo_us"]) == {"geo_us_ne", "geo_us_se"}

    def test_leaves_not_in_map(self, sample_geo_tree: HierarchyNode) -> None:
        children_map = get_children_map(sample_geo_tree)
        assert "geo_us_ne" not in children_map


@pytest.mark.unit
class TestGetAncestors:
    """Tests for ancestor chain lookup."""

    def test_leaf_ancestors(self, sample_geo_tree: HierarchyNode) -> None:
        flat = flatten_tree(sample_geo_tree)
        ancestors = get_ancestors("geo_us_ne", flat)
        assert ancestors == ["geo_us", "geo_americas", "geo_global"]

    def test_root_has_no_ancestors(self, sample_geo_tree: HierarchyNode) -> None:
        flat = flatten_tree(sample_geo_tree)
        assert get_ancestors("geo_global", flat) == []
